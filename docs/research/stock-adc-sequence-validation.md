# Stock whole-ADC-sequence validation

The private suite now supports a single stock prediction test. The question is
whether stock Sparrow executes the complete ADC initialization candidate: 97
software-determined writes and two reads whose explicit synthetic values are
`0x11234` and zero. The intended stop is the unexecuted caller instruction at
relative PC `0x333bac`, after the ADC helper returns. No subsequent subsystem is
modeled by this experiment.

The stock APK, its native library, native observer and sequence profile retain
their existing hashes. The runner reuses the validated calibration filesystem
and guest configuration. A separate `adcsequencemodel` mode stages the manifest's
source, APK, control APKs, calibration records, static candidate and observer
before starting the guest. The native command is `stock-adc-sequence`.

## Local instrumentation prerequisite

The earlier local instrumentation environment has an unavailable interpreter.
It remains preserved. A separate project-local environment was staged with
Python 3.12.13, Frida 16.7.19 and frida-tools 13.7.1. All seven package versions
remain those in `experiments/guest-admission/inputs.toml`, and the server digest
remains unchanged. This changes the host tool interpreter used by this attempt;
it does not change the guest image or stock application.

The environment was created with `uv venv --python 3.12 --relocatable` in a new
local directory, followed by `uv pip install --link-mode copy` using the manifest's
package list. The selected interpreter's exact version, dependency check and CLI
version were recorded. `FreezeFridaEnvironment.main.kts` inventories 721 files,
including the interpreter executable reached through the environment link.
Derived bytecode caches are excluded. The inventory contains relative paths and
is itself pinned in the stock experiment manifest. The runtime verifies all tool
file hashes, exact inventory membership, Python and CLI versions, and the complete
package list before any guest starts.

`ADMISSION_FRIDA_HOME` selects this environment; no global interpreter or host
security configuration is changed. The private-control mode still needs no Frida.

## Evidence and execution boundary

`VerifyStockAdcSequence.main.kts` checks the inherited stock execution and file
fixture, entry captures, 175 guards, complete operation sequence and register
transitions, 33 final shadows, thread coverage, cleanup and the precise stop.
Its host fixtures are synthetic checker tests; they cannot establish stock ADC
execution. The final verifier takes an external manifest digest and checks indexed
provenance and health along with native behavior.

After the preparation task is verified, closed and pushed, the separately
admitted run uses configured tool locations:

```sh
ADMISSION_ADC_SEQUENCE_STOCK_INPUTS="$PWD/experiments/adc-sequence/stock-inputs.toml" \
ADMISSION_FRIDA_HOME="$FRIDA_TOOL_ROOT" \
  tools/guest/run-admission.sh stock-adc-sequence-01 adcsequencemodel
```

The runner also requires `ANDROID_SDK_ROOT`. Keep stdout, stderr and final audit
outputs outside the finalized evidence directory. Stop and preserve the first
unexpected result. A fresh hypothesis and freeze are required for any subsequent
attempt.

## Preparation result

The frozen manifest is `experiments/adc-sequence/stock-inputs.toml`, SHA-256
`c174fc9bd0b4a9842af20783df3ea92afe02ed217527a84b44325f4c7db33cd3`,
with 168 staged artifacts. Host verification accepted one complete synthetic
trace and rejected fourteen targeted corruptions, including incorrect writes,
readbacks, registers, guards, captures, final shadows, thread cleanup, terminal
PC, identity, health, packages, and omitted direct/transitive evidence-index rows.

The production runtime passed seven mocked cases; production indexing passed one
positive and four negative cases. Tool prerequisite controls passed two positive
and three negative cases, and environment inventory controls passed one positive
and three negative cases. The actual separate local environment also passed its
721-file hash inventory, version, package and dependency checks. Earlier fixtures
and private experiment evidence were preserved. These are preparation results;
they do not establish stock ADC execution.
