# Whole-loader observation controls

The static recovery predicts the first three calibration loads as a complete region.
The observer checks their returns and captures complete destination records before the
unexecuted `SetADCParameter(0)` call. It adds no mapped-register response and leaves
stock code unchanged. This controls batch does not execute Sparrow.

The private program exercises the same inherited observer prefix, then four execution
stops after uninterrupted atomic sequences. Its buffers are independently generated:
LSB bytes change from `a5` to `(3*i+1)&255`, ADC bytes remain `5a`, and vertical bytes
are `(5*i+7)&255`. Three successful arms check ordinary returns, negative 32-bit
returns, and revisiting an old checkpoint after its breakpoint has been cleared.

Negative arms cover wrong PC, opcode, thread, binding, pointer, and length; a short
remote read; corruption at the final vertical byte; an unexpected mapped access;
a newly created thread; and a missing checkpoint. Each outcome requires exact group
cleanup. Existing runtime and malformed-input controls run first against the same
new executable.

The wrong-thread control explicitly arms a worker's own breakpoint before private
execution resumes. It records that thread's debug state and unchanged registers,
then requires rejection of its actual checkpoint event. Stock checkpoints remain
main-thread-only. The signed-width control supplies zero-extended negative 32-bit
values in `x0`; interpreting all 64 bits as the return status would fail this case.

Complete remote capture uses `process_vm_readv` in chunks no larger than 64 KiB,
with explicit address-overflow, single-record and cumulative limits. Positive partial
reads are preserved and reported before rejection. Capture file hashes are computed
independently on the host. Entry captures hold only the main thread; terminal captures
require convergence of the entire traced group. Derived fixed-layout addresses are
distinguished from observed loader returns and captured bytes.

The guest filesystem fixture installs only the two byte-identical available stock
defaults, verifies their round trips, and proves the four primary/ADC paths absent.
Guest enforcement and `system_server` identity must remain unchanged. Installation
in a private control does not establish that the stock application can open the files.

The [frozen inputs](../../experiments/calibration-loaders/inputs.toml),
[control definitions](../../experiments/calibration-loaders/controls.toml), and
[event protocol](../../experiments/calibration-loaders/native-protocol.md) define this
experiment. A separate decision task must evaluate its evidence before admitting a
stock loader continuation.

## First run: host admission stopped the suite

`group-calibration-loaders-01` passed the 59 runtime controls numbered 0 through 58
and all 30 malformed-input controls. Tail arm 59 then completed its native sequence,
but its frozen host verifier rejected the new executable against the previous
binary's hardcoded digest. Arms 60 through 89 and calibration-file installation
were never reached. This run establishes no complete loader capture.

A separately preserved review copy changed only the two expected native digest
literals. It accepted the original arm 59 capture: two existing DNA reads, 466
stores, ten tail reads, two tail stores, three checkpoints, three completed tail
atomic sequences, and exact cleanup of three traced threads. Calibration did not
execute. The frozen failure and raw evidence remain unchanged.

Review also found an unreached loader-verifier contradiction: a required count of
466 writes was compared with indices 0 through 463. Neither defect calls for a
native or hardware-model change. The follow-up must explicitly admit this exact
binary for private legacy controls, preserve strict baseline and stock profiles,
correct the index list, and run the remaining validation through a fresh bounded
suite. It must not claim that controls omitted from this run passed.

The preservation audit verified 561 indexed artifacts and 67 unchanged
`system_server` samples. Enforcement stayed enabled, the stock package remained
absent, stock APK and library hashes matched, and dedicated listeners were absent
after teardown. See the [recorded conclusion](../../experiments/calibration-loaders/run01-results.toml).
