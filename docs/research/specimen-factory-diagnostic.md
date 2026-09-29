# Native factory diagnostic

The single diagnostic run narrows the failure to the first `CApiBase` constructor, reached through
`Api_Create` → `CApiUtility` → `CApiCore`. It does not retain the faulting PC. The process terminates after
constructor entry without a terminal fault event. Missing event delivery is an observer limitation, not proof
of a specific instruction failure or JNI prerequisite.

Static inspection places the base constructor at `0x260f78`, its service-item constructor at `0x260ba4`,
and its vector append at `0x260eac`. This path allocates and copies native service metadata. No direct JNI
call is present in the inspected base-constructor path. The normal Java business entry establishes JNI before
calling the factory, but that ordering alone does not attribute this failure to Java.

The unchanged specimen libraries loaded successfully. The run made no installer call, established no option
state and did not reach the DNA stop. The copied instrument files have equal before/after manifests. No
physical instrument connection occurred. The bounded diagnostic question closes with a narrower unresolved
native-construction boundary; it does not justify substituting constructor results or adding speculative JNI.

## Next decision

Validate durable native fault recording in a private control, then use it for one stock constructor diagnostic.
Use stolen native exception context and a flushed guest journal so a process exit cannot erase the only fault
record. Recover constructor helpers and initialization requirements statically in parallel. This is directly
necessary to the short entitlement path; it does not expand into ADC or general startup recovery.

## Evidence

Private run: `out/specimen-entitlement/factory-diagnostic-01`.

| Artifact | SHA-256 |
| --- | --- |
| `controller.stdout` | `76b03ffd0416f112d83d18dca2681c417f739600afa96118c187ee6dce5d9152` |
| `evidence-sha256.txt` | `594638bda20febf7ecab34d5f11d0078752945d230e9405c388140d5c2613202` |
| `result.toml` | `70c9ebd99274487739aaca7406b966fe627d385391a7884150a2c7b66b061448` |

Run interval: 2026-09-29 05:51:20–05:51:42 UTC. Controller and runner returned 3. No successful
installer or persistence result is claimed.

## Durable recorder control

`fault-control-01` passed on 2026-09-29 at 06:01:27 UTC. Private ARM64 code performed one null read.
The stolen native exception identified the exact allocated instruction PC and a read at address zero.
All three journal events were delivered identically; the terminal record was acknowledged after syncing the
host evidence file. The runner exited zero and the copied instrument files were unchanged. No stock native
library was loaded by the control script. This validates the caught-exception path, not every possible
process-level signal-handler path.

The guest journal SHA-256 is `ea40d64955706b91c758ef2a011108b73529b08a3836ff110d8aad9e3f7031ed`.
The run evidence index SHA-256 is `03c639a99d62466970b639828dfe6ccdea2d60808ce54fa828b53df48ef3e066`.
The admitted single stock diagnostic can now use this recorder.
