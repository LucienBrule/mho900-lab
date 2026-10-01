# Compute supplied RAW AC statistics offline

`mho-lab rf raw-ac-inspect` computes statistics of the supplied original ASCII
voltage samples after parsing and qualifying their RAW preambles and explicit
acquisition metadata. It requires no carrier frequency or receive threshold.
`mho-lab rf receive-inspect` asks a separate question: whether those samples meet
the unchanged default sampled-frequency receive profile at a supplied command
frequency. A receive rejection does not make otherwise valid RAW statistics
undefined.

The [synthetic example](../../examples/raw-ac-statistics/README.md) demonstrates
the distinction with two manufactured records. From the repository root:

```sh
uv sync --locked --all-packages
uv run --locked python examples/raw-ac-statistics/walkthrough.py out/rf/raw-ac-example-01
```

Choose a fresh output directory for each run. The example refuses an existing
path. It generates all bytes locally, invokes the public CLI module with the
current Python executable in isolated mode, and retains
the original input files, complete TOML receipts, stderr and a verification TOML
with source and input digests. It uses no device, network interface, socket,
controller, private acquisition or sealed physical run.
Each command and its actual and expected exit status are printed separately from
the retained TOML stdout. The same script can run with `python -I` in an installed
consumer environment outside the checkout.

Each record has 100,000 points at a supplied 4 GSa/s rate, a matching 250 ps
preamble increment, one acquisition, and the entire asserted memory extent from
1 through 100,000. Its duration is `N * dt = 25 µs`; its first-to-last sample span
is `(N - 1) * dt = 24.99975 µs`. The weak sine uses the exact rational phase step
`975 MHz / 4 GHz = 39/160`, repeated 625 times over the record, plus 10 mV DC.
ASCII values are already volts and are never rescaled through the preamble's
vertical conversion fields.

| Manufactured record | Arithmetic DC | Original Vpp | Population AC RMS | RAW statistics | Default receive |
| --- | ---: | ---: | ---: | --- | --- |
| 1 mV peak sine plus 10 mV DC | 10 mV | 2 mV | approximately 0.707106781 mV | accepted | rejected at `range:vpp-range` |
| Constant 10 mV | 10 mV | 0 V | exactly 0 V | accepted; constant and zero flags true | rejected at `range:vpp-range` |

The reference values and metric comparison tolerances are preserved in
[expected.toml](../../examples/raw-ac-statistics/expected.toml). The example checks
the expected status 0 for statistics and status 1 for receive rejection, the named
metric fields, the geometry, and the original waveform and preamble hashes.
Unexpected outcomes stop the example and leave its output for inspection.

For one generated record, the two commands can be run independently:

```sh
mho-lab rf raw-ac-inspect \
  --preamble-before out/rf/raw-ac-example-01/weak-sine/preamble-before.txt \
  --data out/rf/raw-ac-example-01/weak-sine/waveform-ascii.txt \
  --preamble-after out/rf/raw-ac-example-01/weak-sine/preamble-after.txt \
  --actual-rate-hz 4000000000 --memory-points 100000 --start 1 --stop 100000 \
  > out/rf/raw-ac-example-01/weak-sine/statistics-manual.toml

# Expected status 1: the default receive profile requires at least 5 mV Vpp.
mho-lab rf receive-inspect \
  --preamble-before out/rf/raw-ac-example-01/weak-sine/preamble-before.txt \
  --data out/rf/raw-ac-example-01/weak-sine/waveform-ascii.txt \
  --preamble-after out/rf/raw-ac-example-01/weak-sine/preamble-after.txt \
  --actual-rate-hz 4000000000 --memory-points 100000 --start 1 --stop 100000 \
  --command-frequency-hz 975000000 \
  > out/rf/raw-ac-example-01/weak-sine/receive-manual.toml
```

The statistics receipt has schema `mho-rf.raw-ac-inspection/1`, result
`raw-ac-statistics`, method `unwindowed-demeaned-population`, original-byte hashes,
and named `[geometry]` and `[metrics]` tables. Rejections report
`statistics-rejected` with a typed stage and code. The library rebinds original
bytes and the supplied acquisition assertions before measuring; passing an
already constructed qualified object does not bypass that check.

For sample voltages `v[0]` through `v[N-1]`, the arithmetic DC is their sum divided
by `N`, and AC RMS is `sqrt(sum((v[i] - DC)^2) / N)`. It is an unwindowed population
statistic of these samples. It subtracts DC, uses divisor `N`, and applies no
Hann window, frequency fit or engineering pass threshold. Extrema and Vpp use the
original decoded samples. If all decoded binary64 samples are exactly equal,
their common value is DC and AC RMS is exactly zero. Nonzero original decimal samples or nonzero derived values
that underflow to zero are rejected explicitly. Ordinary rounding of representable
values remains part of the binary64 numerical contract.

These statistics establish quantities of supplied sampled voltages and metadata.
They do not establish physical origin, calibrated amplitude, a noise floor,
carrier frequency, isolated analog gain, analog bandwidth or a software-policy
effect. A zero result identifies equal decoded binary64 samples; distinct decimal
tokens can round to the same binary64 value. It does not establish that a physical
signal was absent. A weak record can have useful
sampled AC statistics while failing receive qualification; reporting its statistic
does not promote it to a qualified carrier. The synthetic amplitude and frequency
are manufactured inputs, not physical observations.
