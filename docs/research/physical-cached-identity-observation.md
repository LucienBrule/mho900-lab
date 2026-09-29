# Physical cached-identity observation: APK-backed mapping boundary

On 2026-09-29, the authorized observation stopped before helper staging or process-memory access.
The tested reader requires a standalone stock Auklet backing file. The physical Sparrow process instead
shows executable and data mappings backed by its installed APK; no standalone `libscope-auklet.so` path
appears. This is a mapping-contract mismatch, not a denied memory read or a recovered identity value.

## Captured sequence

Fresh full Ethernet capture began at 12:07:12 UTC, before adding the temporary isolated host address.
A single-client DHCP exchange supplied the existing private address without gateway or DNS options;
the ACK was captured at approximately 12:10:08 UTC. Existing ADB credentials connected to the previously
established endpoint. `id` reported the existing root identity; no daemon restart or root request occurred.
Read-only commands collected policy mode, process listing, command line, start time, boot ID and maps.
The standalone-library precondition rejected at 12:10:09 UTC.

The run made zero reader attempts, staged no helper and read no process-memory bytes. It did not invoke
instrument initialization, registers, SCPI, Web Control, option installation or capability changes.
The current loaded library's bytes were not freshly acquired or hashed, because the mapping precondition
failed first. The run therefore does not establish current file identity or physical reader permissions.

The operator subsequently reported unplugging and reconnecting Ethernet to force a lease, with a visible
"LAN disconnected" indication. The cable transition's exact time relative to the recorded DHCP exchange
is unknown. Do not characterize the DHCP request as an undisturbed spontaneous retry: cable reconnection
may have triggered it. The operator then confirmed a stable normal UI with Ethernet connected.
No reconnect or second observation was initiated by the harness.

## Capture and restoration

The recorder terminated gracefully with 516 stored frames, 516 packets reported received by the filter,
and zero reported kernel drops. Every stored frame was complete. Offline replay of the recorded network
classifier accepted all frames: the single-client DHCP exchange, local ARP and IPv6 neighbor traffic,
the bounded ADB connection, and previously characterized host discovery/multicast traffic. Reusing that
classifier checks retained evidence against the run's rules; it is not an independent proof of those rules.

The dock interface was identified through its hardware topology and MAC identity. The default route stayed
on the separate host interface; IPv4 and IPv6 forwarding were disabled, with no active NAT, Internet Sharing
or bridge membership on the scope-facing interface. Host DHCP-client configuration remained inactive.

The temporary host address was removed, the lease responder stopped and ADB disconnected. Post-run checks
confirmed isolation; network preferences and interface-mapping property lists matched their baseline bytes.
The private lease was granted for one hour and was not revoked. Host restoration does not erase that lease
from the scope. A later host-only link check following the operator's report showed active carrier and no
host IPv4 or IPv6 address. The privileged host shell was closed.

## Offline mapping comparison

The previously acquired active APK has SHA-256
`6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b`.
Its uncompressed `lib/arm64-v8a/libscope-auklet.so` entry starts at APK file offset `0xf05000`, is
12,453,760 bytes long, and hashes to the pinned stock Auklet value
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.

Preserved physical maps contain an executable APK mapping beginning at file offset `0xf05000` and data
mappings consistent with adding that ZIP-entry offset to the stock ELF segment offsets. In particular,
the page containing ELF data offset `0xb68c00` begins at APK offset `0x1a6d000`.
This supports direct loading from the uncompressed APK entry. It does not substitute for a fresh hash of
the currently mapped APK, nor does it establish the cached values.

## Decision

Close this observation as a reproducible precondition stop. Do not retry the standalone reader, weaken
its backing-file checks, attach instrumentation or change physical permissions.

The next useful work is offline: specify and test an APK-entry-aware address resolver using the acquired
APK and preserved maps. Pin the APK, ZIP entry and embedded ELF independently; account for APK-relative
file offsets; distinguish the other libraries and resource mappings sharing the same APK inode; retain
unique load-bias and writable-range requirements. A disposable-guest control must establish that contract
before proposing another physical read. This is a new bounded hypothesis, not an amendment to this run.

No physical DNA/file-key derivation or acquired-Key.data coherence claim is available yet. Physical option
installation, capability changes, reboot and further state acquisition remain separate decisions.

## Evidence

Private run: `out/physical/mho984-cached-identity-20260929T120256Z`.
Raw maps, process identifiers, packet payloads and host details remain local. No cached key bytes were acquired.

| Artifact | SHA-256 |
| --- | --- |
| `live/capture.pcap` | `2ea3f1f856ac95ddce16bac8d1d760d74d8bd70ccc82525d2cc60d7fbd24124a` |
| `capture-validation.toml` | `5de8395a8394e12d3b59f6704f9cd5964bb279fefdcf9e0031a15f453f04f837` |
| `observation-validation.toml` | `23b9003248c67c4f3e4a4e376a2f7373c72d6eae080fa5df88eb1f935b94117c` |
| `apk-map-comparison.toml` | `a1e3f9850d85a55fbff02cc22a4cfa65b612718fd47150ca37a021f156f56d0c` |
| `control-inputs.toml` | `28c76028af8114b3459fc161f05a20d1023a5d42c563967a6546f1af0c71bdda` |
| `metadata/target-maps.stdout` | `f8f5b0f30f9a930dd7c8d51ed6e154ac639afb4428a4efc2cfe3c8f92e3ff831` |
| `evidence-sha256.txt` | `575b52d4ac20ed47dac8c4aa9fa358ca80405be5710cfe834dde8e675ae3a21d` |
