# Supplied-RAW AC statistics and sampled-frequency receive guard

`mho-rf` consumes an existing `mho-waveform.RawQualified` record, rebinds its full
byte/metadata/observation qualification, and returns immutable typed
`ReceiveQualified` or `ReceiveRejected` results. It never opens a file or device,
prints, contacts a service, fits a carrier or changes acquisition state.
The offline `mho-lab rf receive-inspect` endpoint reads bounded regular files
through an application delegate and renders TOML without paths or sample dumps.

```python
from mho_rf import ReceiveProfile, ReceiveRequest, qualify_receive

result = qualify_receive(ReceiveRequest(
    record=raw_record,
    command_frequency_hz=600_000_000.0,
    profile=ReceiveProfile(),
))
```

The default engineering profile requires the full 100,000-point RAW/ASCII extent,
acquisition count one, observed and interval-derived 4 GSa/s within 1e-8 relative
tolerance, voltages strictly within +/-180 mV, and Vpp strictly between 5 and
360 mV. Supplied rate and extent remain assertions rather than independent proof
of acquisition origin or freshness. Public models are revalidated, the waveform
is reparsed from retained bytes and the entire rebuilt `RawQualified` result must
equal the supplied qualification; forged samples, preambles, hashes, durations
and observations cannot substitute for the evidence.

The fixed default numerical procedure removes the arithmetic mean, applies
periodic Hann `0.5 - 0.5*cos(2*pi*n/N)`, and computes the real FFT using the actual
preamble interval. Squared FFT magnitudes have weight two on interior bins and
one on DC and the even-N Nyquist bin. DC is excluded from both selection and
total energy. Odd-N last bins remain interior bins. Select the strongest weighted
bin in inclusive `[0.5, 1.5] * command` and the strongest global non-DC bin;
both must lie within 1% of command. The selected peak's +/-2 bins, clipped to the
non-DC FFT extent, must contain at least 20% of all non-DC weighted energy.
Relative peak ties within 1e-12 choose the lowest bin and preserve tied-bin lists.
Zero/nonfinite energy, empty/out-of-Nyquist bands and invalid profiles reject.

The complete explicit profile is returned with SHA-256 of its validated
field-ordered `model_dump_json()` UTF-8 bytes, including defaults. JSON is only
the canonical hash encoding; authored receipts are TOML. The default profile
digest is `25401a53b0b9b9a14581f740b5d8cf665ccfb2b37c962d925c77b46389409358`.
Bin spacing is approximately 40 kHz at the default geometry; these bins inherit
scope-clock uncertainty. Nearby tones, modulation, harmonics and aliases can
contribute to the neighborhood. The threshold is not calibrated sensitivity,
spectral purity, source-frequency origin or amplitude accuracy.

```sh
uv run --locked mho-lab rf receive-inspect \
  --preamble-before out/record/preamble-before.txt \
  --data out/record/waveform-ascii.txt \
  --preamble-after out/record/preamble-after.txt \
  --actual-rate-hz 4000000000 --memory-points 100000 --start 1 --stop 100000 \
  --command-frequency-hz 600000000
```

Exit zero and `result = "receive-qualified"` mean only that the declared sampled
receive criteria passed. Rejection emits `result = "receive-rejected"` and exits
one; FFT diagnostics remain available when computed. An out-of-Nyquist physical
3.4 GHz tone can alias into an accepted 600 MHz sampled component. A 600.5 MHz
tone can pass this 1% receive criterion while lying outside a later command-centered
+/-1e-4 fit interval. The CLI consequently emits `physical_origin_proven = false`,
`calibrated_amplitude_proven = false` and `final_fit_validity_proven = false`.

The TOML schema is `mho-rf.receive-inspection/1`. It includes command, profile hash,
preamble/data hashes, selected/global peak bins and frequencies, energy fraction,
FFT spacing and numerical ties. `[profile]` contains every criterion and `[input]`
contains actual interval/rate/extent, duration, extrema and removed DC mean. Prior
input/RAW failures omit unavailable FFT fields. Qualification can support an
explicitly admitted online acquisition stop rule; final sealed analysis must
recompute and compare retained receipts and assess final fit validity separately.


## Original RAW AC statistics

`measure_raw_ac(RawAcStatisticsRequest(record=raw_record))` returns named frozen
`RawAcStatistics` or `RawStatisticsRejected` outcomes. It rebinds the full RAW
qualification to its original bytes and acquisition observations before computing
arithmetic DC, original extrema/Vpp and unwindowed demeaned population AC RMS.
Evidence includes all three byte hashes; geometry retains the selected extent,
acquisition count, reported/interval-derived rates, interval tolerance and durations.
This operation has no frequency, receive, voltage or experiment engineering gate.
The waveform decoder's existing bounded input contract still applies.

RMS uses an origin shift and scaling before centering and squaring; this preserves
small AC differences on large DC offsets and tiny varying signals. Arithmetic DC
uses a compensated sum. Exactly constant decoded samples preserve their exact DC
and zero RMS. `constant_samples` means exact equality of decoded binary64 volts,
not equality of the original decimal tokens: ordinary decimal rounding remains.
A nonzero original decimal token that underflows to binary64 zero rejects as
`unrepresentable-samples`; a varying positive RMS or nonzero compensated DC mean
that underflows to zero rejects as `unrepresentable-metrics`. Rejections retain
available hashes. No rounded numerical zero is promoted to a varying-signal result.

`mho-lab rf raw-ac-inspect` accepts the existing supplied waveform flags, without a
command frequency. TOML schema `mho-rf.raw-ac-inspection/1` contains root evidence
hashes and named `[geometry]` and `[metrics]` tables on success. Exit zero means
`raw-ac-statistics`; exit one means `statistics-rejected`. It emits false origin,
calibrated amplitude and receive-qualification claims. Supplied metadata does not
independently prove freshness. The metric includes harmonics, aliases and noise;
it does not isolate a physical carrier or establish an experiment's group decision.
See the [synthetic walkthrough](../../docs/runbooks/raw-ac-statistics-walkthrough.md).
