# Stock startup reaches the PCIe boundary

Observed 2026-09-25 UTC in a disposable ARM64 Android 7.1.1/API-25 guest.
**Decision: stop for operator review.** Stock Sparrow now initializes its Android
activity, loads its native library and renders a loading screen. Its main thread
is waiting in the native PCIe device-open retry. Resolving that interface as an
instrument device would require hardware behavior beyond the standing pre-hardware
authorization. No such behavior was supplied.

## What executed

The APK remains byte-identical, with SHA-256
`6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b`.
The packaged `libscope-auklet.so` matches the independently inspected stock ELF,
SHA-256 `4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.

The exact-stock [admission exception](guest-admission.md) and
[guest label assignment](guest-labeling.md) permit UID 1000 and the existing
`system_app` domain while preserving both the stock package certificate and the
different platform shared-UID certificate. No app method or native return value
was replaced. Frida was detached and stopped before app launch; its previously
documented guest-policy changes remain a fidelity limitation.

The stock DEX inspection shows `SplashActivity.onResume` scheduling a 500 ms delay,
then calling `API.UI_StartBusiness`, then reading view models and entering
`MainActivity`. `API` loads `scope-auklet`. The live main-thread dump captures:

```text
SplashActivity coroutine
  -> API.UI_StartBusiness (native)
  -> JNI_StartBusiness                 call site 0x232558
  -> CApiFactory::Api_Init             call site 0x239110
  -> Dev_PCIeInit                      call site 0x27022c
  -> usleep -> nanosleep
```

These three native offsets in the ART dump match the independently disassembled
stock ELF exactly. ART labels the frames as `base.apk` because this library is
mapped directly from the APK; it does not provide their native symbol names.
The symbol attribution above comes from that separate ELF comparison.

The native startup log also records `JNI_StartBusiness`, channel scale setup and
failed GPIO reads. Those GPIO diagnostics precede the observed PCIe wait; they are
not themselves proof that the GPIO failure stopped initialization. The AndroidX
missing-class diagnostic is likewise followed by activity resume and rendering.

## Why this is a hardware boundary

| Witness | Observation |
| --- | --- |
| Stock `Dev_PCIeInit`, `0x27017c` | Opens `/dev/xdma0_bypass`; the referenced string is at ELF address `0x993543`. |
| Open call, `0x2701fc` | On a negative descriptor, retries up to 30,000 times with a 1,000 microsecond sleep. |
| Live main-thread dump | Stopped at that retry's `usleep` call, reached through the real JNI startup path. |
| Two `/proc` samples, 15 seconds apart | Main thread in `hrtimer_nanosleep`; process survives. |
| Guest device inventory | No `/dev/xdma*` node exists. |
| Success branch, `0x270280` | Requests a shared, read/write 16 MiB mapping of the opened device. |

The containing read-only ELF load segment has equal file offset and virtual
address, checked in the captured program headers; the device string extraction
is therefore grounded in the actual referenced bytes.

The live dump and device inventory support the device-open failure inference.
An exact syscall errno was not captured. The loop is finite; 30,000 nominal
one-millisecond sleeps do not establish a 30-second wall-clock deadline in this
guest. The approximately 40-second post-launch observation ends while it is
still in the retry. Its eventual timeout behavior was not tested.

This interface is the stock application's mapped FPGA control plane, not an
ordinary missing resource file. Creating an empty node or file would not provide
the register semantics expected by subsequent stock code. A behavioral model or
real instrument backend would be needed to resolve that interface faithfully.
No fake mapping, successful-open substitution, register values, DMA data, or
waveform was introduced. This finding does not establish that PCIe is the only
remaining dependency, nor that all later startup paths must access hardware.

## Evidence, controls and limits

`startup-01` ran from 01:28:04Z to 01:30:00Z. It independently repeats the exact
admission, three rejection controls, installed-byte and certificate checks,
process label, activity resume and splash rendering. The app PID is 2527;
`system_server` remains PID 1039 before hook removal, after removal and after
observation. The crash buffer is empty. Screenshots show the loading spinner,
not a useful instrument UI. No physical device or host security policy was used.

The optional `debuggerd` collector failed twice with exit 127: this guest exposes
`debuggerd64`, not that command name. Those failed observations are retained.
The successful stack witness comes from ART's SIGQUIT dump, collected separately
after the two `/proc` samples. No debugger failure is presented as an app failure.
SIGQUIT is observational but may briefly perturb scheduling. The stock instruction
sequence and earlier logs provide independent corroboration of its stack result.

Static exploration output is retained separately. `static-01` included its own
checksum index by mistake; `static-02` reruns the unchanged static inspection with
that indexing bug fixed. Only `static-02` is used as the verified static evidence.
Tools are JADX 1.5.6 and LLVM 23.1.1; their captured versions and LLVM executable
hashes accompany the output. Decompiler output is treated as interpretation and
is corroborated by the native instructions and live stack.

`experiments/guest-startup/results.toml` indexes source and raw evidence.
`VerifyLabeling.main.kts` validates the admission/lifecycle evidence and
`VerifyStartup.main.kts` checks both checksum indexes, the packaged ELF hash,
observed stack, wait samples, missing device inventory and static call sites.

## Reproduction

With the previously pinned SDK and Frida inputs configured, and `LLVM_BIN` set
to the local LLVM tool directory:

```sh
tools/guest/inspect-startup.sh static-fresh
tools/guest/run-admission.sh startup-fresh startup
kotlin tools/guest/VerifyLabeling.main.kts out/guest-admission/startup-fresh
kotlin tools/guest/VerifyStartup.main.kts out/guest-admission/startup-fresh out/guest-startup/static-fresh
```

The startup helper preserves the failed optional `debuggerd` capture and uses the
SIGQUIT witness. The verifier deliberately checks that recorded limitation.
Fresh run IDs prevent overwriting evidence. Guest state is disposable; original
APK, firmware and image files are checked and remain unchanged.

No successor execution task is admitted. The architecture's previously static
PCIe boundary now has a live startup witness; this confirms the proposed boundary
without requiring a material architecture revision. Further hardware-model design
or implementation awaits operator review.
