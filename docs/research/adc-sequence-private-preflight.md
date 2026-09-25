# ADC sequence private-suite preflight finding

The frozen `private-adc-sequence-01` attempt exited 1 before starting an Android
guest. The shared admission runner tried to execute its local Frida CLI version
check, and that launcher failed with a bad-interpreter error. The private native
suite did not execute any arm. This result says nothing about the observer's
worker, atomic, register-sequence or final-stop behavior.

All 140 staged inputs match the frozen manifest. The runner stopped before ADB
startup, userdata staging and emulator launch; those artifacts are absent. Its
runtime finalizer and indexer were consequently not reached. The original stdout,
stderr and staged directory remain unchanged, with a separate staged-input audit
and idle-listener checks for all four experiment ports. Guest health is not
applicable to this attempt because no guest started.

The coupling is in the shared runner. The `adcsequencecontrol` helper uses ADB to
run the pinned private native executable, collect its evidence and invoke the
Kotlin verifier. It does not invoke Frida or install Sparrow. Requiring Frida's
CLI and package environment for this mode adds a host-tool dependency without
contributing to the control question.

The bounded continuation is a runner-only correction: make the prerequisite
check conditional on the selected mode, test private operation without a Frida
installation and retain the existing checks for modes that use it. Freeze a new
run identity and manifest while preserving this attempt and the original native
binary, profile and per-arm verifier. Admit another private suite only after that
correction is reviewed, committed and pushed. Stock continuation remains gated on
actual private guest evidence.

See `experiments/adc-sequence/private-run-results.toml` for evidence hashes. No
physical instrument or host policy was accessed or changed.
