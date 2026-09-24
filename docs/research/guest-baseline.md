# ARM64 API-25 guest baseline

This experiment implements `ROADMAP.guest-baseline`. The first candidate is the official plain Android ARM64
API-25 revision-2 image. Its extracted metadata identifies Android **7.1.1**, build `NYC`, incremental `8695018`,
security patch `2018-01-01`, and `userdebug`. It is not the instrument's reported Android 7.1.2 environment.

## Inputs and reproduction

The [input manifest](../../experiments/guest-baseline/inputs.toml) pins the archive, extracted files, runtime
executables and stock APK. The original APK remains byte-identical and its source corpus is read-only.

Download the URL recorded in the manifest into `local/guest-images/api25-default-r02/image.zip`. Verify its
published SHA-1 and recorded SHA-256 before extracting there. The archive contains the `arm64-v8a/` subdirectory.
Copy the stock APK from `local/reversing/firmware-extracted/stock-0.26/firmware/app/Sparrow.apk` to
`local/guest-inputs/Sparrow.apk`; verify the copy against the manifest. SDK location is configured locally through
`ANDROID_SDK_ROOT`. Use the pinned emulator and platform-tools versions; the runner rejects changed executables.

Requirements: a compatible macOS ARM64 host, Android SDK with build-tools 35.0.0, GNU `gtimeout`, `yq`, `lsof`,
`shasum`, and free ports 5041, 5580 and 5581. Acquisition uses `curl` and `unzip`. No host kernel or security
configuration changes are part of this experiment.

```sh
tools/guest/run-baseline.sh run-01
tools/guest/run-baseline.sh run-02
```

Each invocation requires a new run ID and creates a fresh writable guest under `out/guest-baseline/`.
The script pins two virtual CPUs, 2 GiB RAM, 1280x800 display at 160 dpi, and SwiftShader graphics.
It uses a private ADB server and isolated Android configuration directories; snapshots are disabled.
It does not modify the APK, guest signing policy, model identity, or hardware interfaces.

Boot polling lasts at most 180 seconds plus the final bounded ADB probe; the emulator process has a 330-second
outer timeout. Individual ADB commands have 15-second bounds; installation has 30 seconds. The application is
observed for 15 seconds after a launch attempt. Cleanup targets only the experiment's emulator and ADB server.

Shell is used here for native SDK process orchestration, filesystem isolation, and raw output capture. This is
not a manifest-processing framework or an emulated hardware model; future semantic project tooling remains
Kotlin-first. Generated local configuration necessarily resolves paths, but those files remain ignored.

## Evidence interpretation

Raw logs, screenshots, command arguments, any pulled platform APK and tombstones remain local. Review and sanitize
evidence before adding a result summary to source. Record hashes of the original local evidence for traceability.

`result.toml` records phase reachability. `completed` means Android reported boot completion; a screenshot still
requires inspection. `admitted` means ordinary package installation succeeded. `attempted` means a launch command
was issued, not that the application reached useful state. Negative outcomes are valid investigation results
only when the repeated evidence identifies the failure; a timeout alone does not identify its cause.

The expected signing barrier is a hypothesis until the guest platform certificate and install result are observed.
If boot fails, installation and launch must remain `not_reached`. The decision task evaluates that failure before
proposing any runtime change, guest modification, or additional task admission.

## Observed result

The official guest boots on the pinned Apple Silicon runtime with Hypervisor.Framework acceleration and
SwiftShader rendering. ADB reports Android 7.1.1, API 25, ARM64, and `sys.boot_completed=1`; screenshots show the
Android launcher. The guest kernel reports `3.18.91+`, AArch64. This establishes guest viability for the baseline.

Ordinary installation of the byte-identical stock APK fails with `INSTALL_FAILED_SHARED_USER_INCOMPATIBLE`.
The package-manager diagnostic identifies `com.rigol.scope` and the existing `android.uid.system` shared UID.
The guest platform certificate extracted from `/system/framework/framework-res.apk` has SHA-256:

```text
c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8
```

Sparrow's certificate is different:

```text
f48e7189aac174df7fd19acf58b6d15832760fcf25ac0a6d4bcd5fc1974d4c03
```

The first two fresh-state runs produced this same operational result. Verification then found that the runner's
checksum index mistakenly included itself; all other indexed evidence matched. The runner now excludes that
index and waits for the log collector to exit before hashing. The original runner is retained locally under
`out/guest-baseline/inputs/runner-original.sh`, matching the historical input-task receipt. The final repeated
runs and their evidence are indexed in [results.toml](../../experiments/guest-baseline/results.toml).

The result is **a reproducible APK-admission failure**. Application launch, JNI loading, model selection, and
hardware-facing behavior were not reached. No APK modification, guest signing exception, physical device access,
or synthetic hardware was introduced. Screenshots establish Android rendering, not Sparrow rendering.

## Decision gate

Guest acquisition and boot are no longer the immediate blockers. The next experiment should investigate a narrowly
scoped admission exception in a disposable research guest while preserving the stock APK's bytes and signature.
This is a proposed guest modification, not a claim that the original Android signing policy accepts Sparrow.

| Candidate response | Assessment |
| --- | --- |
| Different emulator or Google APIs image | No evidence this resolves a certificate mismatch; defer. |
| Reconstruct a compatible vendor Android environment | Useful later; no complete compatible image is pinned. |
| Re-sign or edit Sparrow | Breaks the byte-identical baseline requirement; reject for this experiment. |
| Disable signature checks globally | Confounds the environment beyond the observed need; reject. |
| Exact APK/package/certificate admission exception in an isolated guest | Selected next investigation. |

Unknowns include the guest framework's exact implementation/build correspondence, available debug mechanisms,
and whether a bounded exception can retain normal rejection for unrelated packages, signers, and updates.
The baseline provides sufficient evidence to begin designing that exception; it does not establish its feasibility
or authorize an unbounded patch. If a narrow mechanism is unavailable, return an evidenced blocker to review.

The [proposed successor plan](../../.agents/plans/guest-admission-proposed.yaml) separates admission design from
the controlled probe. It is not admitted to taskctl and has not been executed. The probe must independently
validate exception scope, preserve the APK digest, and capture the next actual startup failure.
Android 7.1.1 versus the reported 7.1.2 remains a documented fidelity limit rather than an explanation for the mismatch.
