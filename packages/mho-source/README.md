# Bounded RF source control

`PointCommand` validates candidate touchscreen-generator fields; `encode_point`
produces the 11-byte HawkRAO point frame. These describe a candidate serial
interface, not verified MAX2870/MAX2871 RF behavior. See the project's
[control decision](../../docs/research/rf-source-usb-control-decision.md).

`FactoryPointCommand` and `encode_factory_point` are a separate recovered
touchscreen protocol: `55 55 W_hi W_lo F_hi F_lo P 0D 0A`. `W` is whole MHz,
`F` is hundredths of MHz, and `P` is raw power bits 0–3. `frequency_hz` must be
an exact multiple of 10000 within the advertised 23.5–6000 MHz range. This range
is an input bound, not RF qualification. The receiver treats CR as framing even
inside the binary payload, so requests containing that byte are rejected.
There is no escaping or silent frequency adjustment. For example, 100.13 MHz,
269 MHz and 3328 MHz cannot be encoded safely with this recovered framing.
LF alone is not a delimiter. See the [pinned instruction review](../../docs/research/rf-source-repository-review.md)
for the supporting public image and the unresolved delivered-unit equivalence.
One [delivered-unit trial](../../docs/research/rf-source-factory-trial.md) confirmed
the expected 100.00 MHz Point display after this command. That is a command-path
witness, not RF qualification or validation of the entire command range.

`Command` is the explicit union of these two models. `encode_command` and
`execute` select the matching encoder; existing `PointCommand` semantics remain
unchanged. Both encoders revalidate models, including unchecked copies, before
any port operation.

`execute` operates on a typed `Port`. It observes input for 0.5 seconds, stops
before writing on any input or setup error, attempts one write, and observes for
2 seconds. Each input window retains at most 4097 bytes: 4096 plus one overflow
witness. Partial writes, read errors and overflow stop the experiment without a
retry. Bytes read before an error are retained.

`PosixPort` uses a nonblocking POSIX descriptor, advisory exclusive flock and
terminal `TIOCEXCL`, raw 115200/8N1, no flow control, no input flush, and cleared
`HUPCL`. It clears DTR/RTS and requires modem-line readback. Opening the port can
still pulse lines through OS/driver behavior. Tests use host PTYs with modem
checks explicitly disabled because PTYs do not implement electrical lines;
the CLI never disables them. Existing noncooperating openers are not evicted by
these locks: identify the target and check other users before a physical run.

Closing does not flush, block on drain, restore unknown prior modem states, or
retry a failed close. A complete write means driver acceptance only; the receive
window is not an independent proof of UART transmission. Device interpretation
requires an external witness. Source settings may persist.

The `mho-lab source frame` command is offline. `source point-once` is explicitly
active and requires the device path, frequency, reference, power code and a new
evidence directory. No port discovery or automatic target selection occurs.
The CLI delegates to the library and records a request before opening, durable
write intent before attempting output, raw input, driver-accepted prefix when
known, timestamps and outcome, then seals the run with `mho-evidence`.

The separate `source factory-frame` and `source factory-point-once` commands
take `--frequency-hz` and `--power-code`, with no reference-clock field. Factory
run metadata identifies the protocol and reference firmware digest; it does not
claim that the attached unit contains those bytes. `factory-point-once` uses the
same one-write transport and seal path, with no receiver cleanup or power cycle.
The caller must establish the receiver state before executing it. The recovered
point branch also saves the frequency, so this command may persist ordinary
source settings. No explicit UART ACK is established for this branch; a silent
receive window does not establish device acceptance.

Offline example:

```sh
uv run --locked mho-lab source factory-frame --frequency-hz 100000000 --power-code 0
# 55 55 00 64 00 00 00 0D 0A
```

An intent without a final result is uncertain. A failed final seal does not erase
an earlier write or authorize retry. The evidence captures bytes observed by this
process, not a lossless electrical trace. Port opening and terminal configuration
are themselves possible side effects even when no command is written.

Only point encoding is implemented. Sweep, mute, firmware, calibration, direct
memory operations and oscilloscope access are outside this component.
