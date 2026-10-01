# RF source control decision after stock-firmware review

2026-09-30. `TASK.rf.repository-decision` evaluates the
[pinned repository and instruction review](rf-source-repository-review.md).
The conclusion is to qualify the recovered **factory UART point protocol** before
considering a debugger or replacement firmware.

The published original image supplies a concrete alternative hypothesis:
the generator may use the same 115200-baud, CR/LF-terminated, `0x55` point path.
That path is supported by static instruction evidence and nine bounded offline
controls. It explains why the earlier `AD ... 3D` frame would remain unprocessed
on this build. It does not prove what our unit did: no own-unit dump or RF
observation exists, and appearance is not firmware identity.

The completed single-write trial retains its observed outcome: eleven host-accepted
bytes, no captured reply, and an unchanged 470.00 MHz display. It remains inconclusive
for the delivered unit. The new evidence changes the next experiment, not that record.

## Alternatives considered

| Continuation | Information gained | Decision |
| --- | --- | --- |
| More offline recovery of the published parser | Additional framing, storage and sweep details | Enough of the point path is recovered for a bounded compatibility test. Complete recovery of every menu and sweep branch is not a prerequisite. |
| Bounded factory point-command test | Whether the delivered unit accepts the recovered path; predicted frequency text and Point state provide a witness | Preferred next branch. Reuses intact hardware and stock UI. It can settle ordinary workstation control before RF integration. |
| Observe existing RF first | Distinguish actual 100 MHz from 470 MHz without another source command | Still useful after source/input qualification, especially if the digital witness disagrees. It currently requires the separately open RF connection and level preparation. |
| Acquire this unit's firmware with a programmer | Exact MCU/build evidence and an own-unit restoration baseline | Valuable fallback if the stock protocol remains unresolved, or prerequisite to replacing control. Requires identified MCU, verified wiring and an acquisition plan that separates flash, EEPROM and option state. |
| RAM-resident replacement controller | Direct register-level control with a known command set | Keep as a fallback. It interrupts the stock UI, assumes compatible MCU/pins and needs correction of the host register-4 state issue. It is broader than the current question. |

## Concrete next experiment to prepare

Implement a distinct typed protocol variant; do not silently change the meaning
of the existing HawkRAO encoder or invalidate its retained frame evidence. The
host controls should use independently specified 100.00 and 100.25 MHz vectors,
explicit raw power bits, and framing restrictions derived from the receiver.

The delivered unit then needs one bounded **source-only** compatibility test:

1. Revalidate the same USB-UART device and current displayed state, with both SMA
   ports empty and the LCD ribbon intact.
2. Establish the receiver-state assumption explicitly. If the previous frame is
   still pending as in the public build, terminate that known input with CR LF,
   allow a bounded dispatch interval, and retain any reply or UI status change.
   Do not append the new point frame immediately or claim silence confirms a reset.
   A host input-buffer flush cannot clear the MCU's receive buffer.
3. Send one recovered 100.00 MHz point frame at 115200/8N1, with raw power setting
   0: `55 55 00 64 00 00 00 0D 0A`. Retain exact bytes, timing, host outcomes and
   a screen witness. No automatic retry or alternate baud/protocol search.
4. Stop and classify. A transition to 100.00 MHz with the expected Point UI is
   evidence of this command path on this unit. No change or an unexpected result
   leaves compatibility unresolved and returns to analysis. Neither result alone
   establishes emitted RF, lock, amplitude, spectral purity or bandwidth.

The command must be described as a settings change: the public build also calls
its frequency-save path. It is not a read-only or guaranteed volatile probe.
The offline control records attempted EEPROM writes, not successful storage or
power-cycle behavior. Do not add a reboot, another point setting, or a return to
470 MHz without including those interventions in the physical task's contract.

This decision is preparation, not execution of that test. The concrete sender
and sequence controls should be admitted and committed before the physical
continuation, using applicable operator authorization. A changed or unknown
receiver state must be reconciled before selecting a reset or cleanup operation.

## Probe and measurement handoff

There is no reason to remove the LCD ribbon or attach ST-Link/J-Link for the
preferred branch. If own-unit acquisition becomes necessary, first identify the
controller and power/reference arrangement, then preserve its own bytes before
replacement. Do not use an unlock/erase restoration sequence as a read attempt,
or use the public stock image as a substitute for an own-unit backup.

The exact remaining physical question is:

> With the known receiver state reconciled, does one 115200-baud
> `55 55 00 64 00 00 00 0D 0A` frame change this unit's point display to
> 100.00 MHz, without a reset or unrelated UI transition?

After that, source qualification must independently ask whether the RF output
has the requested fundamental frequency and a suitable level. The RF-response
roadmap remains the main objective; custom source firmware is an optional tool,
not a new prerequisite for the 1 GHz comparison.

No physical access, firmware change, serial write, probe connection or RF
connection occurred during this decision. Review evidence is sealed by private
manifest SHA-256
`c3368d9a4be760dd31d0623f9b919160a6911768f4d925c564b90a7f6134a8dd`.
