# ADC input capture profile

This research profile observes the software inputs to the recovered mode-zero
ADC programming routine. It extends the existing loader observation at its
terminal checkpoint, before stock `SetADCParameter(0)` executes. It does not
supply another device value or claim physical calibration behavior.

The [decision contract](../../experiments/adc-input-capture/decision.toml)
defines nine raw captures, totaling 11,565 bytes. The existing terminal
1,936-byte ADC record is reused. The captures cover matrix and bucket state,
channel/probe/trigger/Bode settings, sample rate, series selection, selected
configuration and sample-mode entry, and fifteen mutable register shadows.
The diagnostic-only field at `adc+0x87f4` remains explicitly outside this set.

`stock-adc-inputs` uses the same modeled initialization prefix and four loader
checkpoints as the accepted loader experiment. At the last checkpoint it clears
the execution stop, converges the complete tracked thread group, retains the
five existing loader captures, then performs the additional capture phase.
There is no target resume after the terminal stop. Normal cleanup kills and
reaps the disposable application threads before the guest is torn down.

The capture phase validates fixed object addresses, sixteen relocation bindings,
series selection and pointer allowlists, finite capture sizes, and readable-map
containment. It follows only the selected config and sample-table entry. The
mapped device pointer is captured as a scalar and never dereferenced by this
reader. A bounded maps snapshot is retained separately. Missing or incomplete
reads and inconsistent pointers are negative observations, not reasons to invent
software state.

The independent capture checker recomputes selection and addresses from raw
bytes. A separate stock checker carries the complete inherited transcript,
loader, fixture, thread, health, and evidence-index checks with explicit new
source and runtime pins. The earlier stock-loader checker remains unchanged.
The private control suite uses independently constructed software state and
checks both accepted captures and bounded failures before stock observation.

New modes are `adcinputcontrol` and `adcinputmodel`. Each consumes its frozen
manifest under `experiments/adc-input-capture/`; run identity and source hashes
are checked before guest startup. Results belong in a fresh ignored run
directory. Private and stock conclusions must be committed and pushed before
another guest experiment.

## Disposable userdata staging

The new modes stage userdata through `stage-userdata.sh`. On macOS this requests
an independent copy-on-write clone using the platform copy utility, then checks
source/copy hashes, distinct inode identities, and a single link on the copy.
It records available space before and after staging and requires at least
2 GiB before startup. The fallback on other platforms is a regular independent
copy subject to the same byte and space checks. Existing evidence is preserved.

Host controls mutate a staged private fixture and verify that the source remains
unchanged. They also reject an occupied output, linked source, linked output,
and insufficient space. Initial host controls exposed a PATH tool mismatch and
an early-exit guard error; both were fixed before any guest use. Reproduction:

```sh
sh tools/guest/test-userdata-staging.sh out/userdata-staging-controls-reproduction
```

A successful capture binds one stopped-process snapshot. It does not establish
that earlier state was never mutated, that another boot selects the same state,
or that programming these values will produce valid acquisition.

## Implementation checks

The capture-only ARM64 binary compiles with warnings treated as errors. Exact
one-, four-, and eight-byte reads are checked for complete transfer, so adjacent
fields are not implicitly read. Each raw capture also records FNV-1a-64 over the
bytes written. This detects accidental file changes independently of a regenerated
SHA-256 file index; it is a consistency witness, not an authenticity mechanism.

The host capture suite accepts normal selection, fallback, the stock 4000-to-2000
substitution, mask normalization, and Bode selection. Twelve negative cases cover
changed bytes, pointer or address mismatch, unreadable maps, invalid bounds,
missing bindings, a post-terminal resume, inconsistent state or summary, missing
captures, truncation, and an unsigned maximum bound. The full stock-profile
checker is additionally exercised with independent copies of the accepted prior
loader evidence and explicitly synthetic input captures. Its eight negative
controls test capture corruption, pull failure, actual runtime pins, inode aliasing,
terminal resume, final health, and duplicate or incomplete evidence indexes.

These host fixtures do not constitute a stock ADC observation. Their preparation
verifies the original evidence index before and after copying and requires distinct
inodes; each mutated case has its own copy. Reproduction with local evidence:

```sh
kotlinc -script tools/guest/test-adc-input-capture.main.kts -- out/adc-capture-host
kotlinc -script tools/guest/PrepareStockAdcInputControls.main.kts -- \
  out/guest-admission/stock-calibration-loaders-02 out/adc-capture-host out/adc-stock-host
kotlinc -script tools/guest/VerifyStockAdcInputs.main.kts -- out/adc-stock-host/base
kotlinc -script tools/guest/test-stock-adc-inputs.main.kts -- \
  out/adc-stock-host/base out/adc-stock-host/negative
```

Private arms 90–100 test complete capture, fallback, three pointer/binding failures,
an excessive table bound, an unreadable address, a deliberately shortened capture,
a single changed matrix bit, a changed configuration/mode pair, and a late clone.
The shortened-capture arm exercises partial-output rejection; it is not a claim
that the guest kernel produced a short read. The changed-bit arm must report the
exact divergence from its canonical pattern. Any unexpected result stops the suite
and blocks stock observation.

Build the new profile to a fresh output directory, preserving older frozen binaries:

```sh
GROUP_OBSERVER_OUT="$PWD/out/adc-input-capture/reproduction-build" \
  NATIVE_CC="$(command -v clang)" NATIVE_LD="$(command -v ld.lld)" \
  sh tools/guest/build-group-observer.sh
```
