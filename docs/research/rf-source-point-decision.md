# RF source point compatibility decision

2026-09-30. `TASK.rf.point-decision` evaluates the
[single-command trial](rf-source-point-trial.md).

The selected candidate did **not** produce the predicted UI transition. The host
accepted one complete 11-byte write, received no reply during the observation
window and closed cleanly. The operator reported the original 470.00 MHz display
unchanged. This is sufficient to reject the experiment's predicted screen result;
it is insufficient to decide what the generator did internally or electrically.

The usable facts are now stronger than enumeration alone: the positively matched
native serial driver accepted raw configuration, DTR/RTS clear/readback and a
complete bounded write. The host-side sender is reusable with those limits. The
candidate board command interface remains **unresolved** and cannot yet be used
as an unattended frequency-setting service.

## Smallest useful continuation

**Corrected after operator clarification, 2026-09-30:** the complete supplied
leaflet is already available. It describes the onboard UI; there is no additional
serial-protocol section to obtain. Its claim that a protocol is provided does not
establish that such instructions were delivered. The earlier recommendation to
request more leaflet pages was unsupported and is withdrawn.

Review of the existing references identifies a separate limitation in the trial:
the expected LCD refresh was an experimental assumption, not a documented response.

| Existing reference | What it establishes | What it does not establish |
| --- | --- | --- |
| Complete delivered leaflet | Local touchscreen controls and claimed serial support | Wire protocol, acknowledgement or USB-driven LCD refresh |
| [HawkRAO control report][hawk] | Candidate 11-byte point frame, 115200/8N1, field units and checksum | This firmware's compatibility, LCD refresh, acknowledgement or an explicit remote-mode prerequisite |
| [element14 board report][element14] | The author's measured RF and local UI experience | Working USB control; the author says they could not determine how to use it |
| Supplied small-OLED module manual | A different nine-byte protocol described in the earlier [comparison](rf-source-research.md) | Applicability to this touchscreen firmware |
| IC datasheet, porting note and evaluation-kit guide | IC-level electrical/register behavior and reference designs | This commercial board's MCU USB command interface |

The transmitted frame remains consistent with HawkRAO's published field rules.
Neither that report nor the supplied leaflet establishes that successful serial
control must change the displayed point frequency. Therefore this trial is
**inconclusive for command acceptance**, despite its observed negative LCD result.
The retained host and screen observations remain unchanged.

The next trial needs an observation that distinguishes accepted control from an
ignored command. Direct RF frequency observation is the strongest currently
identified candidate, after the separately planned source/input qualification.
It could check for the requested 100 MHz versus the displayed 470 MHz without
first sending another frame. Further documentary recovery is useful only if it
provides a board-specific prerequisite, reply convention or different framing.
Blind power-code, reference-clock or selector changes would remain ambiguous.
No operator document-gathering dependency remains.

Keep the current powered state and both SMA ports empty while reconciling. No
repeat command, power cycle, ribbon removal, firmware work, calibration operation,
scope connection or successor device experiment was performed by this decision.
The final observed display remains 470.00 MHz; actual RF and persistence remain
unknown. The broader RF-response milestone is still open.

## Later repository evidence

The subsequent [pinned repository review](rf-source-repository-review.md) recovers
a different point protocol from a published original touchscreen firmware image.
Its [successor decision](rf-source-repository-decision.md) prefers a bounded
compatibility check before programmer work. This narrows the documentary gap
without establishing that the delivered unit runs that image or changing the
original trial's outcome.

[hawk]: https://sites.google.com/view/hawkrao/miscellaneous-sub-projects/software-control-of-max2870-lcd-signal-generator
[element14]: https://community.element14.com/technologies/test-and-measurement/b/blog/posts/using-a-max2870-frequency-synthesizer-signal-generator
