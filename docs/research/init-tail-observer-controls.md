# Private controls for the version and DDR consumer region

The [candidate](../../experiments/init-tail/candidate.toml) follows the statically recovered
initialization region. The native observer retains the validated ADC, SPU and transport
prefix, then permits ten fixed reads and two predicted writes. Three rotating execution
stops check version composition, DDR outputs and the unexecuted calibration boundary.

The [control manifest](../../experiments/init-tail/controls.toml) defines arms 59 through
74. Arms 59 and 72 complete the region; 72 also revisits a cleared breakpoint site. Each
positive arm performs an atomic increment before every checkpoint. The final checkpoint
must precede the private calibration sentinel. Arm 73 waits after the first checkpoint
and requires deadline cleanup. The other arms deliberately disagree with a single
access, binding, live selector or output expectation.

The output contract preserves the stock widths: version words, first and sixth tap
outputs are 32-bit; intermediate tap outputs are 64-bit; the completion flag is a byte.
The upper-half corruption in arm 69 detects a verifier that compares only the low word.
Arm 74 changes the selected configuration after initial capture to test the consumption
boundary guard independently from its initial-value guard.

The new counters remain separate from the earlier two identity responses, 464-store
prefix and ten transport checkpoints. The initial candidate predicted that a redundant
clear of an already disabled slot would differ from a clear after an armed checkpoint.
The [first private negative](init-tail-clear-negative.md) falsified that prediction.
Complete register snapshots must show only the
read destination and PC changed for reads, only PC for writes, and no changes from
checkpoint rotation.

A fresh disposable guest runs all earlier controls with the same executable before
these sixteen arms. Stock Sparrow remains absent. The independent verifier checks raw
fields, operation ordering, checkpoint state, thread accounting and cleanup. Native exit
78 denotes a bounded stop for both complete and deliberately rejected arms; acceptance
depends on the evidence, not the exit code alone.

This private suite validates the observation mechanism and rejection behavior. It does
not establish stock execution through the region or physical FPGA behavior. Its complete
pass is the prerequisite for the separately admitted stock experiment.
