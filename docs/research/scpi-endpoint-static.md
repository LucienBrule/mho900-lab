# Stock MHO900 SCPI socket endpoint: static evidence

The existing stock `.26` firmware implements an IPv4 TCP SCPI listener on port
5555. This is implementation-derived evidence from a pinned local package,
not a numeric port published in the vendor manual or a listener observed on the
physical specimen. No specimen connection, host address assignment, or network
configuration change was performed for this investigation.

## Provenance and preservation

The fresh read-only container check establishes this byte-identity chain:

| Artifact | SHA-256 |
| --- | --- |
| `MHO900_Firmware_Update_v1.00.zip` | `ca45c3a7a40bfb265eca685253abedd9087715af992d5cbdb032a8af7408158f` |
| Embedded `MHO900_Update.GEL` | `d17b14ccf9bbc25b7d776708a486fcde84ad22e93e10aa5dd8dfadf018a3eb12` |
| GEL member `app/Sparrow.apk` | `6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b` |
| APK member `lib/arm64-v8a/libscope-auklet.so` | `4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e` |
| GEL member `app/Webcontrol.apk` | `7b37be5ee0b63857949f7ed7ea940b7593ab50058a3a4c608b8bda00f88d2736` |
| Web Control APK member `classes.dex` | `614e516bd442ec67df75117e69b0c23aecdafc6ba33a150d6542b55e798f74a8` |

These match the extracted files used for analysis. Package origin follows the
existing [input corpus](observed-inputs.toml); this investigation did not download
a new firmware package or authenticate the specimen's installed build. All five
input files were rehashed after analysis and remain unchanged.

Private run: `out/physical/scpi-endpoint-static-20260929T023501Z`.
Its `evidence-manifest.toml` SHA-256 is
`a19c673252243df34f5d1e32e68aa90acd4766ae28dd3d3689026d3bebd983c3`.
The manifest binds input inventories, container checks, native disassembly,
fresh Java decompilation, tool versions, and pinned third-party source.

## Native bind path

Addresses below are link-time virtual addresses in the pinned ELF, not runtime
addresses. LLVM disassembly establishes a data/control-flow chain beyond a
string match:

| Function / address | Evidence |
| --- | --- |
| `CApiScpi::start`, entry `0x65e2c8` | Embedded TCP-server object selected at `this + 0x58`. |
| `0x65e6cc` | `mov w2, #0x15b3`: unsigned-short port argument is decimal 5555. |
| `0x65e6d0` | Calls `CTcpServer::startServer(int, unsigned short)` with that argument. |
| `CTcpServer::startServer`, `0x68c110` | Stores the port as a halfword at server member `+0x1c`; then starts its thread. |
| `CTcpServer::run`, `0x68c1a8` | Calls `socket(2, 1, 0)`: Android/Linux IPv4 stream socket. |
| `0x68c270`–`0x68c290` | Constructs a 16-byte IPv4 sockaddr: family 2, address zero (`INADDR_ANY`), stored port converted to network byte order with `rev` / `lsr #16`. |
| `0x68c2a8` | Calls `bind` with that sockaddr and length 16. |
| Success path `0x68c3a4`, `0x68c3bc` | Calls `listen` with backlog 5, then `accept`. |

The ELF also contains `TCPIP0::%s::5555::SOCKET`. The decisive evidence is the
named SCPI startup and socket bind flow, rather than the literal alone. Port 5555
can also be used by ADB in other contexts; this flow specifically identifies
SCPI. It establishes neither ADB availability nor its absence.

The listener conclusion is conditional on this code executing successfully.
Static analysis does not establish the installed specimen version, enabled
services, successful binding, reachability, or an observed response.

## Stock Web Control transport and framing

Fresh single-class JADX decompilation from the hashed stock Web Control APK gives:

- `com.rigol.webcontrol.BuildConfig.SCPI_SERVER_PORT = 5555` (line 8).
- `com.rigol.webcontrol.server.SCPIWSS`, line 63, connects an asynchronous socket
  to `NetworkUtil.getIpAddress(context)` and that port constant.
- The same class, line 84, writes `(str + "\n").getBytes()` to its connected
  socket. This supplies implementation evidence for an LF-terminated command.

These are decompiler-derived statements, preserved with their original DEX
hash. They describe the stock client convention; they do not prove every server
parser rule or every permitted terminator. For the ASCII command `*IDN?`, they
support the six candidate request bytes `2a 49 44 4e 3f 0a`.

## Separate evidence categories

| Category | What it establishes | What it does not establish |
| --- | --- | --- |
| Vendor documentation | Parameterless `*IDN?` identity-query semantics and `SOCKet` transport, as pinned in the [original B1 proposal](physical-stage-two-b1-proposal.md). | A printed numeric socket port; the official screenshot's field is blank. |
| Stock implementation | SCPI startup passes 5555 through to an IPv4 TCP bind/listen path; stock Web Control uses 5555 and LF. | Specimen build identity, current listener availability, or an actual physical response. |
| Third-party corroboration | Pinned scopehal explicitly lists MHO900 LAN transport as `<ip_address>:5555`; its socket transport appends LF. | Vendor documentation or proof that this specimen is configured identically. |

The scopehal revision is `e812615f5d1ce9498952fd1f6847f8bda151d5a3`:
[transport declaration, lines 172–174](https://github.com/ngscopeclient/scopehal/blob/e812615f5d1ce9498952fd1f6847f8bda151d5a3/scopehal/RigolOscilloscope.h#L172)
and [socket command framing, lines 140–145](https://github.com/ngscopeclient/scopehal/blob/e812615f5d1ce9498952fd1f6847f8bda151d5a3/scopehal/SCPISocketTransport.cpp#L140).
The commit response, tree response and source bytes are retained privately.
Only source inspection occurred; a scopehal client was not run. Independence
here means a separate implementation, not a demonstrated independent origin for
the authors' port knowledge.

The operator also reported DHO-family EEVblog usage of 5555. That reference was
not pinned in this run and is not needed for the endpoint conclusion; it is not
promoted to MHO900-specific implementation evidence.

## Reproduction

Use configurable LLVM/JADX locations and the stock corpus under
`local/reversing/firmware-extracted/stock-0.26/`. Read the source containers in
place; put generated analysis in a new ignored output directory. Preserve exact
tool versions and hashes. Native extraction commands are:

```sh
"$LLVM_BIN/llvm-objdump" -d --demangle --start-address=0x65e2c8 --stop-address=0x65e7a8 "$STOCK_ELF"
"$LLVM_BIN/llvm-objdump" -d --demangle --start-address=0x68c05c --stop-address=0x68c4ec "$STOCK_ELF"
"$JADX" -r --single-class com.rigol.webcontrol.BuildConfig --single-class-output "$OUT/BuildConfig.java" -d "$OUT/jadx-config" "$STOCK_WEB_APK"
"$JADX" -r --single-class com.rigol.webcontrol.server.SCPIWSS --single-class-output "$OUT/SCPIWSS.java" -d "$OUT/jadx-scpi" "$STOCK_WEB_APK"
```

Extracting bytes from ZIP/GEL members into memory and comparing their SHA-256
values verifies the container chain without modifying or executing firmware.
This bounded search recovered a positive endpoint result; it was not an inventory
of every server, parser branch, or networking feature in the firmware.
