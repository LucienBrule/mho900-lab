# Recovered factory point sender and fresh-start trial

2026-09-30. `TASK.rf.factory-point-sender` implements the bounded continuation
selected after the [published stock-image review](rf-source-repository-review.md).
This preparation performs no physical serial operation.

The [`mho-source` package](../../packages/mho-source/README.md) now has an explicit
`FactoryPointCommand` alongside the unchanged HawkRAO `PointCommand`. Click's
`source factory-frame` is offline; `source factory-point-once` calls the existing
durable evidence delegate and one-write transport. Factory metadata records the
protocol and public reference image digest, and leaves device-image equivalence
unproven. It has no reference-clock setting because the recovered command carries
none. Raw power codes 0–3 describe a bit field, not measured output levels.

The factory frame uses whole MHz and hundredths of MHz, with no checksum:

```text
100.00 MHz, raw power 0: 55 55 00 64 00 00 00 0D 0A
100.25 MHz, raw power 0: 55 55 00 64 00 19 00 0D 0A
```

Inputs require exact 10 kHz resolution. The encoder rejects payloads containing
CR, including 100.13 MHz, 269 MHz and 3328 MHz; it never rounds or substitutes a
different frequency. LF without a preceding CR remains a permissible data byte.
The advertised frequency range is only a validation bound. General synthesizer
accuracy and physical output behavior have not been qualified by these controls.

## Host verification

`tools/check-python.sh` passed Ruff, formatting, strict mypy, the authored typing
policy and **673 tests**. New controls exercise independent integer/fractional
vectors, all four raw power codes, malformed units and ranges, coercion rejection,
delimiter collisions and revalidation of unchecked models. Host PTY exchanges
retain the actual nine bytes with a reply or silence. Both protocol alternatives
retain uncertainty if result evidence fails after writing. The factory CLI control
verifies protocol metadata, exact request bytes and the resulting evidence seal.

The shared transport still observes before writing, preserves unexpected input,
records durable intent, attempts one write, observes for two seconds, and closes
without retry. Existing failure controls continue to pass. PTY checks omit modem
line checks because the terminals have no electrical lines; physical use still
requires cleared DTR/RTS and readback. Host driver acceptance is not a device ACK.

`tools/check-python-packages.sh` also passed: eight source distributions were
rebuilt into wheels and installed outside the checkout. The isolated library and
CLI independently emitted the expected 100.25 MHz factory frame while retaining
the previous HawkRAO vector.

Private host-control manifest SHA-256:
`cc7bbae218d6c20b817d9bdf14738ee2682dd82c2f7d7e0136f55394feaca9aa`.
Installed-package evidence manifest SHA-256:
`f2785512380cc36d50ec9e77f516def970237ca238454d17ba45b850fbd4e384`.
These are local verification results; they make no remote CI or RF claim.

## Deliberate receiver-state change

After the earlier decision, the operator offered a source power cycle. The
selected trial uses **one coordinated power cycle immediately before the one
point command**, replacing the decision's proposed CR/LF cleanup of the earlier
unterminated frame. No cleanup bytes will be sent. A startup cycle establishes a
fresh receiver assumption without interpreting residual input. The operator's
startup observation remains necessary; a USB re-enumeration alone does not prove
MCU state or successful source startup.

The admitted physical sequence is:

1. Retain the current USB-UART topology and check for another serial-port user.
2. Ask the operator to remove source USB-C power, confirm its screen is dark,
   wait five seconds, reconnect through the same dock port, and report the stable
   display without pressing controls. Keep both SMA ports empty, the ribbon
   connected and programmers detached.
3. Revalidate the returning device and its serial endpoint; record the observed
   frequency and Point/Quite state. Reconcile an unexpected startup or identity
   before proceeding.
4. Send exactly `55 55 00 64 00 00 00 0D 0A` once at 115200/8N1. This may save
   the ordinary frequency setting. Preserve raw evidence and obtain the resulting
   screen witness. No automatic retry or persistence power cycle belongs here.
5. Seal and evaluate the trial. A stable transition to 100.00 MHz and Point
   supports this command path on this unit; unchanged or unexpected behavior
   returns to analysis. Neither outcome measures the emitted RF.

This branch does not attach the source to the oscilloscope, probe the MCU, remove
the display ribbon or replace firmware. The broader RF-response milestone and
its measurement preparation remain open.
