# Offline ADC capture evidence review

The separate review covers all 333 required artifacts: 325 original index entries
and eight static contracts checked against frozen pins. Every original indexed
hash matches, all nine raw capture lengths and native byte checksums match, and
the complete consumed-file set is accounted for. The original index and every
reviewed input remain byte-for-byte unchanged.

The original capture-phase checker accepts the snapshot again. The original full
checker still exits 3 at its final index-coverage requirement. This review does
not change that experiment outcome. It records a narrower, explicit conclusion:
the captured software state can be used for static candidate construction with
the original index limitation documented and the missing coverage checked in a
separate manifest. No guest or physical instrument was accessed during review.

`ReviewAdcInputEvidence.main.kts` pins the completed run's original index and frozen
checker, checks every artifact, independently checks raw capture lengths and
FNV-1a values, runs the unchanged frozen checks, and verifies the original files
again afterward. It writes only to a fresh review directory:

```sh
kotlinc -script tools/research/ReviewAdcInputEvidence.main.kts -- \
  out/guest-admission/stock-adc-input-capture-01 out/adc-review-reproduction
```

## Prospective indexing correction

The production `runner_index` now includes `adc-parameter-static/*.toml`. Closed
runs and their source copies are not rewritten. The new host integration test
calls that actual function, then independently checks required-file coverage and
fixed input hashes. It accepts the complete fixture and rejects a missing static
file, a file changed after indexing, a changed file with a regenerated index,
and a duplicate entry. The index generator itself remains a recorder; the
consumer checker is responsible for rejecting missing or unexpected inputs.

The seven existing runtime cases also pass with this index change. Reproduction:

```sh
kotlinc -script tools/guest/test-admission-index.main.kts -- out/index-host-controls
sh tools/guest/test-admission-runtime.sh out/index-runtime-controls adcinputmodel
```

The native capture binary and the stock APK/library are unchanged. This batch
supplies no hardware response and makes no acquisition claim. Future guest
profiles must pin the corrected runtime before use.
