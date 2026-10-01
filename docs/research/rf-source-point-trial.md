# First RF source point-command trial

2026-09-30. `TASK.rf.point-trial` follows the admitted
[control decision](rf-source-usb-control-decision.md) and
[host-only sender controls](rf-source-point-sender.md). Sender implementation and
controls were committed and pushed as `f549dad` before opening the source.

## Observed transport result

The operator confirmed the unchanged 470.00 MHz main screen with Point highlighted
and both SMA ports empty. Immediately before execution, the USB vendor/product,
location, USB and serial registry identities, serial paths and full observed hub /
driver ancestry matched the preserved first-contact evidence. The host reported
no process holding either serial endpoint. No alternate target was selected.

The session ran from **18:46:07.768618 to 18:46:10.301259 PDT**, corresponding to
**2026-10-01 01:46:07.768618–01:46:10.301259 UTC**. These are host session timestamps,
not timestamps of individual UART bits or UI changes.

The configured raw 115200/8N1 sender passed its setup and DTR/RTS clear/readback
checks, observed no pre-command bytes for 0.5 seconds, and attempted this frame once:

```text
AD 01 01 04 03 D0 90 01 86 A0 3D
```

It requests a 100 MHz point under the nominal 25 MHz reference hypothesis and
candidate power code 4. The OS write returned **11 bytes**, exactly the complete
frame. The process received **zero bytes** during its following two-second window.
Close returned without an error. There was no retry, second command, sweep,
power cycle, RF connection or oscilloscope interaction.

The transport result is **complete, device interpretation unconfirmed**. A full
write establishes driver acceptance, not independently observed UART delivery.
No reply convention has been established; silence alone supports neither command
acceptance nor rejection. Subsequent host inspection retained the serial entry
and reported no open holder.

## Operator witness and conclusion

After the command the operator reported **“Still 470.00 MHz, unchanged.”** This is
a textual screen witness; no new photograph or exact display-change timestamp
was supplied. It contradicts the predicted 470.00-to-100.00 MHz UI transition.

The compatibility trial therefore has a negative UI result. It does not establish
whether the board ignored the frame, rejected some field, or acted without
updating the display. In particular, the unchanged display is not a measurement
that the RF output stayed at 470 MHz. There is no basis for choosing among those
explanations from this trial alone.

The subsequent [reference reconciliation](rf-source-point-decision.md) confirms
that the existing documentation does not establish LCD refresh as a necessary
response to serial control. The experiment's expected screen transition was an
assumption; command acceptance remains inconclusive. The complete supplied leaflet
is already held and contains only onboard UI instructions.

## Preserved evidence

Private evidence retains the original registry records and target identity, operator
pre-state, exact request and driver-accepted bytes, empty raw input files, durable
write intent, local/UTC timestamps, final result and host postflight.

| Evidence phase | Manifest SHA-256 |
| --- | --- |
| Target and operator preflight | `a8071307604532e0c75d7c8c8a349f2152f90798cf315777ae8030c1d5e5e573` |
| Single-command attempt | `6df5cd949ad45ad1e14e7eaa0f061c50854800e66a9baeb4a435cabe930440c6` |
| Host postflight | `c42ccb2421b97713c2fd1bdd890d3507f1ad01fa1933543bfa928820c2788605` |

The operator witness and conclusion are retained separately from the sealed phase
records. The complete private run manifest SHA-256 is
`4709ee110d792d535688b8cdb553fb50e567c6db678fc785931f256e67a4106b`. This closes the single-command question and feeds the bounded decision.
No extra command is justified by the empty response or unchanged display. RF
frequency accuracy, output level, mute behavior, actual reference frequency and
persistence remain unmeasured.
