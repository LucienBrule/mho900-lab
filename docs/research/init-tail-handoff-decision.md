# Decision: arm directly from the inherited disabled slot

The [initial tail control](init-tail-clear-negative.md) falsified the predicted result
of a redundant clear. Preserve that run, its executable and its failed positive verifier.
The hardware candidate remains unchanged: ten new reads, two writes and three checkpoints
before calibration, following the validated prefix.

Change only the initial breakpoint handoff. Require a full 264-byte GET with info
`0x0606`, slot zero address `0` and control `0x1e5`, and empty unused slots. Skip the
redundant clear. SET the first checkpoint address with requested control `0x1e5` using
24 bytes, then require a 264-byte GET of that address/control `0x1e4`, unchanged info
and empty unused slots. Verify complete register preservation before completing the
first read. Keep the established clear/rearm sequence after delivered checkpoints.

This selects a specific inherited state and a specific transition; it does not permit
alternative disabled encodings or broaden the hardware model. Upstream reference code
explains why the discarded operation preserved the cached control, but direct arm and
subsequent delivery still need their own private evidence.

Run a fresh private suite with all original controls 59 through 74 and all earlier
regressions and malformed inputs. Add arm 75: before the normal initial guard, a private
control deliberately populates slot zero with the valid first-checkpoint address and
control request `0x1e5`. Preserve that preparation's SET/GET evidence. The normal guard
must reject its nonempty inherited state before any tail response; this preparation is
unavailable in stock mode. Require exact thread cleanup on this and every other outcome.

The positive controls must complete all three atomic sequences, demonstrate breakpoint
delivery and final clearing, and preserve the old-site revisit behavior. The verifier
must independently check raw access/state/output ledgers, the changed initial transition
and every negative control. Any unexpected outcome terminates this experiment without
adapting its hardware fixture or debug profile.

Admit one implementation/private-control task and a decision task. The waiting stock
contract gains the decision as an explicit prerequisite. Only a complete private pass
with the identical executable releases stock execution; otherwise the decision records
another bounded continuation. Commit and push tasking before implementation and the
control conclusion before any subsequent experiment.
