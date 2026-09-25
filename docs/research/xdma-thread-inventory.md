# ARM64 thread-inventory control

Run `post-store-inventory-01` resolves the private inventory failure. Opening the stopped child's task directory
with `0x10000` returned `-22` (`EINVAL`) in both controls. Opening the same directory with ARM64 `O_DIRECTORY`
(`0x4000`) succeeded, and `getdents64` returned 72 bytes. All four before/terminal inventories identified exactly
one thread, with matching thread group, supervisor PID and tracing-stop state. No enumeration error or overflow
was reported.

The paired positive control consumed the two unchanged synthetic words and reached its precise hardware stop with
`0x0123456789abcdef` in the output object. The negative control rejected offset `0x4040` after one response.
The four width/direction controls also passed. The independent Kotlin verifier accepted these captures before
stock preparation continued. This supports the corrected observer ABI in this pinned guest; it does not establish
stock process-wide coverage.

## Separate pre-attach failure

The helper next collected stock PID 2534 and a 102,177-byte process snapshot containing the command line,
`system_app` label and memory maps. That ADB shell command returned 255, causing the helper to stop before its
next command. There is no libc pull, stock supervisor launch, modeled mapping or synthetic stock response.
The capture does not record individual command statuses or a separate error stream, so the precise failure
inside the composite snapshot command is unresolved. A populated output file is not proof of a successful
snapshot operation.

This is a second, distinct negative stock gate. The [earlier inventory failure](xdma-post-store.md) remains
preserved. The new post-run `pre-attach-failure` verification mode checks the private controls, exact missing
stock artifacts, raw evidence index, stock hashes, normal instrumentation detachment and final guest samples.
It does not turn the stock gate failure into a post-store success.

The final helper trap sampled `Enforcing` and system_server PID 1073, agreeing with all three outer samples.
The guest shut down normally and the experiment ports were free. The stock APK and embedded native library
retain their pinned hashes. No physical instrument was accessed.

## Decision

Keep the corrected ARM64 inventory implementation. Admit a bounded snapshot diagnostic: capture the command line,
process label and maps separately, record each command's status and error output, and reproduce the original
composite command as a comparison. Proceed to the unchanged stock post-store experiment only when its required
inputs are complete and validated. Keep exactly two synthetic read responses and the same post-store stop;
thread coverage remains a required decision before expanding the model.

The implementation records the directory flag, error operation and return value, bounds enumeration to 128 TIDs,
and rejects malformed directory records. Inventories remain non-atomic snapshots; sibling threads are runnable
and untraced. The [result manifest](../../experiments/xdma-post-store/inventory-results.toml) pins the capture and
source. Reproduction uses the post-store command documented in the prior report and a fresh run ID.
