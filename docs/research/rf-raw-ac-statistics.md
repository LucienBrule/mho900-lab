# Reusable supplied-RAW AC statistics

2026-10-01. The [mho-rf library](../../packages/mho-rf/README.md) now separates
original sampled AC statistics from frequency receive qualification. Its pure
`measure_raw_ac(RawAcStatisticsRequest(...))` API rebinds a supplied RAW record to
its original bytes and acquisition observations before computing DC, extrema,
Vpp and unwindowed demeaned population AC RMS. Named immutable validated outcomes
carry evidence hashes and geometry or an explicit rejection. The file-based
`mho-lab rf raw-ac-inspect` command composes bounded input handling, the reusable
operation and TOML presentation. It performs no device operation.

The [synthetic walkthrough](../runbooks/raw-ac-statistics-walkthrough.md) shows why
statistics and receive acceptance are separate. A manufactured weak sine has
approximately 0.707107 mV AC RMS, while its 2 mV Vpp fails the unchanged receive
profile. A constant 10 mV record has exactly zero sampled AC and likewise fails
that receive profile. Neither rejection prevents reporting valid supplied-record
statistics. The example logs each command and expected status, preserves complete
receipts and byte hashes, and refuses an existing output directory.

## Numerical and evidence controls

Origin-shifted, scaled centering preserves small varying AC on a large DC offset
and avoids squaring tiny voltages directly. Arithmetic DC uses a compensated sum.
Exact constant decoded samples preserve their original decoded DC and zero RMS.
Ordinary decimal-to-binary64 rounding remains; constant classification means
exact equality of decoded binary64 values, not identical decimal tokens.
Nonzero original decimal samples that underflow to zero, and positive AC RMS or
nonzero compensated DC means that underflow to zero, reject explicitly. They
cannot silently become constant or zero-signal successes.

Controls cover known sine plus DC, off-bin finite records, nonsinusoidal data,
constants including nonbinary DC, minimum subnormal variation, unrepresentable
metrics, neighboring floats at large DC, malformed/nonfinite input, forged
samples/preambles/hashes/rates/durations, strict model consistency, bounded files,
CLI equivalence and supplied-byte preservation. No frequency, amplitude floor,
upper engineering limit or group decision enters the primitive. Decoder limits
and explicit RAW acquisition qualification still apply.

The final full workspace gate passed **822 tests**, Ruff and formatting over
124 files, strict mypy and the authored typing policy. Installed wheels rebuilt
from source distributions passed outside the checkout under an isolated Python
3.12.13 interpreter. That consumer exercised library/CLI metrics and hashes,
exact constant zero, tiny positive AC, incomplete-record rejection, and a copied
walkthrough whose refused second run left all earlier output hashes unchanged.

Two failed development gates remain retained: a reused test-loop variable failed
strict mypy, and the new command's import of another command's formatting helper
failed the import-layer control. The fixes use distinct named variables, a shared
presentation helper and an explicit module-entrypoint aggregator. New positive
and negative import controls passed. Existing receive computation, profile and
receipt semantics are unchanged; the frozen physical helper was not replaced.

## Archived physical consumer

A separate offline consumer reproduced all fifteen original limiter records'
DC/RMS quantities through the public supplied-file delegate, within relative
`1e-12` and absolute `1e-15 V` tolerances. It retained the original hashes and did
not reclassify the experiment. Its source-bound evidence is sealed separately:
`out/rf/raw-ac-consumer-final-20261001T235100Z/`, four artifacts, 11,672 bytes;
manifest SHA-256
`bbb81818d7dc77c6093e1c748de76ae4cf1e381ded77dda55fb62cea78850296`.
The original acquisition and reduction manifests were independently verified
unchanged after composition. An earlier development consumer remains separate.

Private final quality evidence is retained in
`out/rf/raw-ac-statistics-workspace-quality-03.log` and
`out/tooling/raw-ac-statistics-installed-02-20261001T235200Z/`.
Earlier failures and installed runs are preserved rather than overwritten.

These statistics include every retained sampled AC contribution: harmonics,
aliases, modulation and noise. They do not establish a physical carrier, isolated
fundamental amplitude, calibrated analog gain, freshness or an experiment's
eligibility/contrast rule. The fixed-frequency
[limiter result](rf-limiter-control.md) remains its own frozen decision. The
[matched-policy readiness hold](rf-policy-comparison-readiness.md) remains open;
no further physical contact or native-policy transition accompanied this tooling
batch.
