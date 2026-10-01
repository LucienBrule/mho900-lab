# One-command RF source sender controls

2026-09-30. `TASK.rf.point-sender` implements the bounded experiment selected by
the [source control decision](rf-source-usb-control-decision.md). No physical
serial endpoint was opened while implementing or checking this component.

The new [`mho-source` package](../../packages/mho-source/README.md) separates
immutable Pydantic point fields, encoding, a typed port interface, and a POSIX
transport. Click delegates retain request bytes before opening and durable write
intent before one output attempt. They seal raw input, known driver-accepted
bytes, timestamps, and the result. A failed final evidence write remains an
incomplete record of an operation that may already have happened.

The sender never retries a partial write. Silence means only that this process
received no bytes during its bounded observation. Device acceptance requires a
screen witness; measured RF and persistence remain separate questions.

## Controls observed on the host

`tools/check-python.sh` passed: Ruff, formatting, strict mypy, authored typing
policy, and **645 tests**. The added controls cover:

- Independently specified published point vector and the 100 MHz candidate frame.
- Invalid units, ranges, coercions, unknown fields and unchecked model copies.
- Actual POSIX PTY exchanges with a reply and with silence.
- Input queued before terminal configuration, retained without flushing and
  causing a pre-write stop.
- Setup, write, read, close, short-write and receive-limit outcomes, with no retry.
- Actual receive-cap enforcement and a termios configuration failure.
- Durable write-intent failure, post-write evidence failure and refusal to reuse
  an existing run directory.

PTY controls explicitly omit modem-line IOCTLs because a PTY has no electrical
modem signals. Physical execution requires successful DTR/RTS clear/readback.
OS/driver pulses during open cannot be excluded. Host tests do not establish the
generator's command semantics, electrical behavior, or freedom from resets.

`tools/check-python-packages.sh` also passed. All eight workspace distributions
were rebuilt from source distributions, installed as wheels outside the checkout,
and exercised with an isolated interpreter. The new library and offline CLI
independently emitted `AD 01 01 04 03 D0 90 01 86 A0 3D`. No physical endpoint
was used by that check.

Private control logs are sealed by manifest SHA-256
`471535e17c94136c8cdbcc3df360e57c3ee812f509c4718127ec1810e77265a4`.
Installed-package evidence is sealed separately by
`b8bc83cf5caeee4fdf5b1a51dddcc4d2053c29ef5aa65b43062656becab4796d`.
These are local results, not an assertion about a remote CI run.

The admitted trial remains one 100 MHz point command, nominal 25 MHz reference,
and power code 4, after exact USB target revalidation and an unchanged-screen
report with both SMA ports empty. Implementation and these controls must be
committed and pushed before that physical trial.
