# mho-waveform

An offline supplied-byte boundary for MHO900 ASCII-voltage waveforms. It parses
one exact LF or CRLF waveform line and matching ten-field preamble lines, keeps
the original immutable bytes and SHA-256 hashes, and returns named accepted or
rejected outcomes. It never opens files, sockets or instruments, imports Click,
prints output or estimates RF amplitude.

`parse_ascii(WaveformInputs(...))` validates byte/point/token bounds, explicit
format/mode enums, positive point/acquisition counts and time increment, decimal
numeric grammar, finite values and invalid-measurement sentinel magnitudes.
Numbers with absolute magnitude at least `1e30` are rejected, including the
`9.9e37` family. ASCII samples already represent volts: the retained Y increment,
origin and reference fields are never used to rescale them. BYTE/WORD payloads
and binary-block envelopes require separate future profiles and are rejected.
Whitespace, trailing empty fields and unterminated or multiple lines are rejected.

`qualify_raw(parsed, RawAcquisition(...))` rebinds the public parsed model to its
evidence and requires RAW mode, selected extent count and `dt * actual_rate`
consistency. Start/stop are inclusive one-based indices inside explicitly
observed memory. This profile requires the preamble point count to equal the
exported selected extent; it does not infer omitted memory or assemble chunks.
The relative interval tolerance defaults to `1e-8` and is bounded to `1e-3`.
The result distinguishes `N * dt` record duration from `(N - 1) * dt` span.
Sample times use the documented mapping `(index - x_reference) * dt + x_origin`,
where index starts at zero in the returned selected record.

NORMAL/MAXIMUM ASCII records can parse, but cannot qualify as raw acquisitions.
A matching raw interval and supplied rate check observed metadata consistency;
they do not independently prove instrument origin, unprocessed ADC samples,
fresh independent acquisition, voltage accuracy or analog bandwidth. A display
grid can be interpolated at an interval different from the acquired sample rate.
No numerical estimator, calibrated gain or isolated fundamental claim is provided.

The CLI reads explicit bounded regular files, rejects observed file changes and
renders structural TOML without private paths or a raw sample dump:

```sh
uv run --locked mho-lab waveform inspect \
  --preamble-before evidence/preamble-before.txt \
  --data evidence/waveform-ascii.txt \
  --preamble-after evidence/preamble-after.txt \
  --actual-rate-hz 4000000000 --memory-points 100000 --start 1 --stop 100000
```

The acquisition arguments are supplied observations, not independent proof.
The command exits zero for raw qualification and one for typed input/protocol
rejection. Reads check each file separately; they do not claim an atomic snapshot
of the collection or validate a run seal. Preserve and verify the original run
manifest separately before reduction. Tests use only synthetic supplied bytes.
