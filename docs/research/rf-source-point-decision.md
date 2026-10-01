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

Reconcile the delivered board's own serial-control instructions against the
HawkRAO frame before another command. The photographed leaflet explicitly says
serial control and a command protocol are provided, but the retained photographed
pages do not supply the wire protocol. The valuable missing information is the
actual supplied protocol section, including baud, framing, field units, required
control mode, and whether externally commanded frequency changes appear on the
LCD. The photographed component marking and UI family are insufficient evidence
that this firmware accepts the older example unchanged.

If that supplied section is unavailable, first review the retained reference
material specifically for display behavior and control prerequisites. A further
trial needs a concrete difference or a discriminating observation. Blind power-code,
reference-clock or command-selector variations would leave an equally ambiguous
result. A source-frequency observation could eventually distinguish a stale
display from a rejected command, but requires the separately planned RF connection
and input qualification; this trial did not admit that step.

Keep the current powered state and both SMA ports empty while reconciling. No
repeat command, power cycle, ribbon removal, firmware work, calibration operation,
scope connection or successor device experiment was performed by this decision.
The final observed display remains 470.00 MHz; actual RF and persistence remain
unknown. The broader RF-response milestone is still open.
