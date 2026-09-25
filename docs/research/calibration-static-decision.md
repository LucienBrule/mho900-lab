# Decision: recover calibration initialization before another guest hypothesis

The [stock initialization-tail result](stock-initialization-tail.md) matched the
frozen static prediction through the unexecuted calibration-entry boundary.
Versions, tap outputs, ready/status state and shadow updates propagated through
stock instructions under the synthetic fixture. This supports using static
subsystem recovery as the primary method and runtime checkpoints to falsify it.
It does not validate the modeled values against a physical instrument.

The next bounded batch is static. Recover the complete calibration initialization
dispatcher, its loader ordering, runtime selectors, error paths and thread-start
sequence. Expand relevant callees through their first environment or hardware
boundary. Inventory paths, formats, sizes and defaults alongside mapped access,
ioctl, DMA and asynchronous operations where the code reaches them. Preserve
unresolved indirect targets and deeper algorithms as explicit graph boundaries.

Use a typed TOML graph with instruction-address witnesses and classifications
`STATIC-DETERMINED`, `RUNTIME-SELECTED`, `HARDWARE-RETURNED`, `ASYNCHRONOUS` and
`UNKNOWN`. Separate stock-binary evidence from driver/reference plumbing and
modeled FPGA semantics. Reproducible extraction and independent checking must
establish coverage rather than implying every transitive callee was recovered.

The batch contains recovery, independent review and a decision. No guest run or
new response is part of the first two tasks. The decision will identify the next
externally unsatisfied dependency and select the smallest coherent environment
fixture or observation needed. File reconstruction may be preferable to adding
register behavior; the evidence must decide. Any future run will validate a
complete predicted region and stop on divergence.

Tasking is in [calibration-static.yaml](../../.agents/plans/calibration-static.yaml).
The inspected plan creates only those three task records and their immutable
history. Commit and push the admitted batch before executing recovery.
