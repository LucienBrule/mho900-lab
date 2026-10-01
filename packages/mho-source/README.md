# Bounded RF source control

`PointCommand` validates candidate touchscreen-generator fields; `encode_point`
produces the 11-byte HawkRAO point frame. These describe a candidate serial
interface, not verified MAX2870/MAX2871 RF behavior. See the project's
[control decision](../../docs/research/rf-source-usb-control-decision.md).

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

An intent without a final result is uncertain. A failed final seal does not erase
an earlier write or authorize retry. The evidence captures bytes observed by this
process, not a lossless electrical trace. Port opening and terminal configuration
are themselves possible side effects even when no command is written.

Only point encoding is implemented. Sweep, mute, firmware, calibration, persistent
memory operations and oscilloscope access are outside this component.
