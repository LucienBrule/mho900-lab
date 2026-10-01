# Source USB control decision

2026-09-30. `TASK.rf.usb-control-decision` follows the positive
[first-contact observation](rf-source-usb-observation.md). The Apple driver is already bound and a single new
serial interface has been matched through USB ancestry. Select a bounded point-command compatibility test.
No driver installation, alternative serial protocol, MCU identification or firmware work is presently justified.

This decision prepares a test; no serial endpoint was opened or bytes transmitted during this checkpoint.
The photograph is an initial UI witness. A subsequent trial must check that the board remains at a stable main
screen before applying a command, and must stop on reboot, unexpected UI state or loss of the identified target.

## Concrete candidate

Use the HawkRAO touchscreen format, 115200 baud, 8 data bits, no parity and one stop bit. The requested point is
100 MHz, distinguishable from the observed 470 MHz. Use power code 4, the lowest setting in that published mapping.
Do not assign a delivered dBm value: the chip-marking discrepancy and output network remain unqualified.

Use 25 MHz as the explicit nominal-reference hypothesis from the delivered leaflet and the original-clock board
report. The source was not modified to an external reference. This is not a measured oscillator frequency and
does not justify copying HawkRAO's example 10 MHz field. Keep this assumption visible in trial evidence.

The candidate frame is:

```text
AD 01 01 04 03 D0 90 01 86 A0 3D
```

The reference field encodes 250,000 units of 100 Hz; the RF field encodes 100,000 units of 1 kHz. The final `3D`
is the sum of the preceding ten bytes modulo 256. Offline arithmetic rechecked both published example checksums
and independently decoded the proposed fields. This proves framing arithmetic only, not device compatibility.

## Bounded trial requirements

- Keep RF OUT and MCLK unconnected, retain the ribbon and existing source firmware, and leave the scope unchanged.
- Revalidate the current device registry identity, USB ancestry and serial path immediately before opening.
  Retain a pre-command UI observation. A changed path or identity requires reconciliation, not a wildcard scan.
- Use exclusive serial access and explicit raw 115200/8N1 configuration with software/hardware flow control off.
  Define and record DTR/RTS handling and hangup behavior. Port opening can pulse control lines even if later set
  explicitly; do not claim guaranteed absence of resets. Retain any pre-command bytes and stop on a detected reset.
- Preserve the exact proposed frame before transmitting it once. Use bounded reads/timeouts, preserve raw received
  bytes, record write completion and errors, and close the port cleanly. Do not repeat after a partial or ambiguous
  write. Unknown acknowledgement semantics mean an empty response is not proof of failure or success.
- Obtain a post-command screen witness. A changed 100.00 MHz field with expected point-mode indication supports
  UI command interpretation. An unchanged screen, reboot, malformed response or lost device is a result to evaluate,
  not permission to try different selectors or protocols immediately.
- The board may persist point/power settings. Record the final observed state and this persistence uncertainty;
  do not claim exact rollback because the original output-power setting was never observed. No EEPROM commands,
  power cycle or automatic restoration belongs to this compatibility trial.

An implementation must be admitted and committed before device execution. Check framing with known vectors and
exercise the actual transport's timeout/error behavior on a host-only serial control before using the source.
Any reusable Python component follows the existing typed uv/Click/delegate/library conventions. Keep this test
small; a general source driver or sweep engine is unnecessary.

## Evidence and scope

Offline candidate bytes and a TOML interpretation are privately sealed by manifest SHA-256
`0ba905263338d3f761358cf0ec37f3888c4ba487d149b4a9bd79c5e4b51014f6`.
The protocol reference is the [HawkRAO firsthand report][protocol]; its supplied snapshot hash and limitations
remain in [source references](rf-source-references.toml).

This supplies the proposed control and execution limits required by the decision task. It does not assert serial
compatibility, measured RF, calibrated power or persistence, and does not close RF preparation or integration.

[protocol]: https://sites.google.com/view/hawkrao/miscellaneous-sub-projects/software-control-of-max2870-lcd-signal-generator
