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
