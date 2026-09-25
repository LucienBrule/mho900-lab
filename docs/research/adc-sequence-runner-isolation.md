# Private ADC sequence runner isolation

The first private attempt stopped before guest startup because a shared runner
prerequisite invoked an unused Frida launcher. Its original manifest, staged
inputs and failure logs remain preserved. It supplies no native observer result.

The corrected prerequisite function records that `adcsequencecontrol` does not
use Frida. Other modes retain the server digest, CLI version and package checks.
This is a runner dependency correction; it changes neither host interpreter
configuration nor the native observation experiment.

Host controls exercise the actual sourced function with no Frida installation,
a valid retained-mode fixture, a changed server, a missing launcher and a wrong
version. The production runtime health and index controls are repeated. The suite
audit also checks the prerequisite record and binds the reported run identity to
the externally digest-pinned manifest. Synthetic host fixtures test those checks;
they do not establish native guest behavior.

The new manifest is `experiments/adc-sequence/control-inputs-02.toml`. It retains
arms 101–112 and the exact native executable, profile and per-arm verifier from
the original freeze. `runner-isolation-results.toml` binds the host evidence and
both manifest digests. The original `control-inputs.toml` remains historical.

After committing and pushing this freeze and closing the prerequisite task, run
the separately admitted attempt with a configured Android SDK:

```sh
ADMISSION_ADC_SEQUENCE_INPUTS="$PWD/experiments/adc-sequence/control-inputs-02.toml" \
  tools/guest/run-admission.sh private-adc-sequence-02 adcsequencecontrol
```

Keep stdout, stderr and the final suite audit outside the finalized run directory.
Use the new manifest digest from `runner-isolation-results.toml` when invoking
`VerifyAdcSequenceRun.main.kts`. Stop on the first unexpected result and preserve
it; changing a frozen suite requires a separate decision and new tasking.

Stock validation remains gated on the actual private guest controls. This change
introduces no hardware response and launches no stock application.
