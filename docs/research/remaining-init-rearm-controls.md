# Remaining initialization rearm controls

The complete private suite passed with the phase-specific breakpoint profile. The
observer can now test the recovered SCU/transport/LA region as one bounded stock
hypothesis, using the exact executable validated here. This result establishes observer
behavior in the disposable guest; it does not establish Sparrow's actual transport branch.

Run `group-remaining-rearm-01` used executable SHA-256
`8314d10b48c3cc69a4f51e28f61836dacd2f2b0c7a7831f2614a39fa3bf71e0d`.
All nineteen new controls, forty prior controls and thirty malformed inputs passed.
The frozen aggregate verifier checked all runtime arms and all 532 indexed artifact
digests. Current native source, header and verifier match the frozen run copies.

Both complete controls accepted ADC452, SPU8, SCU2 and LA2, reached all ten native
checkpoints, completed ten atomic increments, and stopped before the mapped read at
offset 4. Arm 53 also revisited the cleared old checkpoint without another trap and
recorded its completion. Every accepted store changed only PC; breakpoint programming
preserved all captured general registers, SP and PSTATE.

The guest matched the fixed profile: initial clear returned control `0x1e4`, clearing a
previously armed slot returned `0x1e5`, and arming/rearming returned `0x1e4` at the new
target. Metadata stayed `0x0606`, with all unused slots zero. Actual delivery and atomic
progress support the combined rotation behavior; the cached enable bit alone remains
insufficient evidence about physical debug state.

The board/GPIO successful-open controls stopped at checkpoints 1 and 5 before their
I/O sentinels, with atomic totals 1 and 5. Cached descriptor, original bool, binding,
shadow, operand, order, width, thread and propagated-error mismatches were rejected.
Skipping checkpoint 4 left the observer at index 4 while nine private atomic increments
completed; the first LA store was rejected for the wrong phase. The deadline control
quiesced the group without a previously stopped main thread and reaped all three threads.

Across the nineteen new arms, 8,770 stores were accepted, including thirty SCU/LA stores.
Each arm retained the two existing identity responses, started with two threads, observed
one clone, and exactly quiesced/reaped three terminal threads. All 65 `system_server`
samples remained PID 1080; enforcement stayed enabled, the stock package was absent,
and dedicated guest listeners were absent after teardown. Stock APK/library hashes
remain unchanged.

Ten altered evidence copies were rejected: missing final clear readback, missing SET
result, missing checkpoint or initial register-invariance records, a wholly omitted
first rotation, changed open argument, changed non-PC store register, changed atomic
total, nonzero unused debug slot, and missing reaped thread. The unaltered copy passed.
These checks used the frozen verifier and did not alter the original capture.

Pre-run review additionally made the timeout arm require an actual deadline event and
bound aggregate verification to the exact profile artifact. The earlier negative run
remains independently verifiable under its explicit negative mode; it was not rerun or
reinterpreted as a success.

## Stock gate and limits

Proceed to the waiting stock task with this exact executable and the unchanged four-store,
ten-checkpoint hypothesis. Add no synthetic return value or device node to make the
transport branch match. A successful open, unexpected selector, changed state, new clone
in the region, timeout or unknown access remains a terminal result.

Software captures are not atomic across other running threads. Main-thread checkpoints
do not establish process-wide absence of UART operations. Private successful-open
sentinels validate the fixture's stopping order, not physical device behavior. No FPGA
side effect, acquisition, useful UI, or stock completion is established here.

See the [profile](breakpoint-rearm-profile.md),
[result manifest](../../experiments/remaining-init/rearm-results.toml), and
[stock region contract](remaining-init-decision.md).
