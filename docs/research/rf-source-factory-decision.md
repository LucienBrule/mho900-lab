# Return from source-control recovery to RF qualification

2026-09-30. `TASK.rf.factory-point-decision` evaluates the
[successful factory point trial](rf-source-factory-trial.md). The delivered source
responded to one recovered UART frame with the predicted 100.00 MHz display and
Point state. **Use the existing factory controller for the next bounded source
qualification step.** Programmer attachment and replacement firmware no longer
address the immediate blocker.

The evidence supports one specific path: 115200/8N1, nine-byte CR/LF point frame,
integer 100 MHz and raw power 0 after a fresh startup. The fractional encoding and
delimiter restrictions are supported by published-image recovery and host
controls; they have not been exercised on this unit. An exact MCU/build identity
or exhaustive parser recovery is unnecessary for a fixed-frequency RF pilot.

| Established | Still separate |
| --- | --- |
| USB device/serial ancestry and a retained one-command transcript | Electrical UART trace or a device-generated acknowledgement |
| Operator-reported 470.00 to 100.00 MHz Point transition | PLL lock and emitted fundamental frequency |
| A reusable typed sender with explicit protocol evidence | Calibrated output level, spectral purity and arbitrary frequency coverage |
| Factory UI remains usable; no replacement firmware introduced | Equality with the public firmware dump and successful EEPROM persistence |

The observation makes further guessing between the old HawkRAO and recovered
factory point paths unnecessary for this immediate use. It does not turn the
previous negative trial into a success or establish every menu command. A custom
STM32/GD32 controller, complete stock dump, or persistence exercise would broaden
the work without answering the next RF question.

## Next useful work

Resume `TASK.rf.inventory` and the existing preparation/integration sequence in
the [RF-response roadmap](rf-response-roadmap.md). Reconcile the delivered cables,
available attenuation/termination and actual scope input conditions into one
short, fixed signal path and a defensible level budget. Then prepare a **100 MHz
pilot** that records a waveform and its scaling/sample-rate metadata. Its question
is whether this source setting produces a usable measured signal at the selected
scope connector; it is not a bandwidth determination.

The raw power code alone is not a calibrated level. Do not silently substitute
an advertised MAX2870/MAX2871 output-power value for a measurement of this board.
Use the equipment actually available to justify the first connection and record
the limitation if no independent level reference exists. Resolve output state
during connection explicitly; no additional UART mute command was tested here.

Once the pilot is interpretable, a fixed-frequency stock/derived/stock comparison
around the intended bandwidth region has more information value than source MCU
archaeology. The existing policy verification, matched acquisition settings and
baseline-return checks still apply. Relative improvement and an absolute 1 GHz
bandwidth claim require different evidence, as already recorded in the roadmap.

Exact next bench question:

> Under the documented 50-ohm connection and level conditions, does the delivered
> source's 100.00 MHz Point setting yield a stable, unclipped waveform whose
> measured fundamental and saved sample metadata support the planned comparison?

This decision introduces no RF connection, new serial command, programmer
operation or scope contact. The source is left at its reported 100.00 MHz Point
setting with both SMA ports empty. The single-command trial is sealed by manifest
`369835189b35f93eb927d6a38740bfb321d6cbf41d479e8490ddab096511e3ae` and was
committed/pushed as `2a6a7d5` before this evaluation.
