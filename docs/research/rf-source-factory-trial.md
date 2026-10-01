# Delivered source accepts the recovered factory point command

2026-09-30. `TASK.rf.factory-point-trial` completed the single-command test
prepared by the [factory sender task](rf-source-factory-sender.md). After one
operator power cycle, one USB-UART command changed the reported source display
from **470.00 MHz to 100.00 MHz**, with Point highlighted and the UI otherwise
stable. This is evidence for this factory command path on the delivered unit.
No RF measurement was performed.

## Physical sequence and observed result

Preparation and task closure were committed and pushed as `21d1c77` before the
trial. Host-only registry captures associated the USB device with its serial
client through the same dock topology; an ownership check reported no other open
port user. Raw registry identities remain in private evidence.

The operator was asked to unplug source USB-C, confirm the screen went dark,
wait five seconds and reconnect the same cable. The reply confirmed one cycle,
470.00 MHz with Point highlighted, and both SMA ports empty. Returning USB and
serial registry entry IDs differed from the baseline, while device identity,
topology and endpoint matched. The exact cable transition times were not measured.

| Observation | Recorded result |
| --- | --- |
| Restored source screen, operator report | 470.00 MHz; Point highlighted; both SMA ports empty |
| Sender configuration | 115200 baud, 8N1, no flow control; DTR/RTS clear and read back; HUPCL off |
| Pre-read | 0.5 seconds; no input returned |
| Request | `55 55 00 64 00 00 00 0D 0A` — 100.00 MHz, raw power 0 |
| Durable write-intent timestamp | 2026-09-30 19:35:04.583913 PDT / 2026-10-01 02:35:04.583913 UTC |
| Output attempt | One write; nine bytes accepted by the host driver |
| Post-read | Two seconds; no input returned |
| Transport completion | No reported issue; close succeeded at 02:35:06.587605 UTC |
| Resulting screen, operator report | 100.00 MHz; Point highlighted; otherwise stable |

The screen witness is the operator's transcription, not a captured photograph.
Its receipt was recorded at 02:35:52 UTC; that time is not a display-latency
measurement. Silence is recorded as absence of input during the bounded windows,
not an ACK. The transport record remains `transport-complete-device-unconfirmed`;
the subsequent independent screen witness supplies the command-path conclusion.

Only the RF source was power-cycled. No cleanup bytes, alternate baud, retry,
second setting or post-command persistence cycle was introduced. Both SMA ports
remained empty. No oscilloscope contact, programmer attachment, ribbon removal
or firmware replacement occurred.

## Supported conclusion and limits

The prediction from the public stock image survived a physical compatibility
test: the integer point frame produces the expected visible application state.
This gives a workable stock-controller route from the workstation without
requiring replacement firmware or MCU access.

It does **not** establish that the delivered MCU contains the public image, that
every command or fractional frequency is compatible, or that the output has the
requested fundamental, amplitude, lock or spectral quality. The new frame may
save the ordinary frequency setting; actual EEPROM persistence remains untested.
The earlier 470 MHz restoration precedes this command and cannot prove persistence
of the new setting. Software enablement and the oscilloscope RF-response milestone
remain distinct from source control.

The original eleven-byte trial and its unchanged-screen result are preserved.
The new finding supports using the recovered factory protocol for this unit's
point path; it does not retroactively turn the old host write into an accepted
source command.

## Evidence

The private run contains registry baselines, explicit operator reports, the
registry-review helper, exact request and driver-accepted bytes, raw input files,
durable intent, timestamps, transport result, CLI output and seals.

| Manifest | SHA-256 |
| --- | --- |
| Pre-cycle host baseline | `e7ed6db16c362e9165bb1dc743cd5471eeee96c1f1c563ac2e1d350c401339e3` |
| Post-cycle identity and startup witness | `b7e2d517ee7160f22773c0e17280def7eb723eca94519bf3fc44133a71840fc0` |
| One-command transcript | `2e171ac90fb38e705e4b98e6cfef4fa76b6c208ef5229c77a2259af08b5fe1e1` |
| Complete run, 34 artifacts | `369835189b35f93eb927d6a38740bfb321d6cbf41d479e8490ddab096511e3ae` |

All three phase manifests and the complete-run manifest were verified after
creation. The bounded decision follows separately; this trial does not itself
authorize a cable connection or another command.
