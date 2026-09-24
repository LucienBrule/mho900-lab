# Scoped guest admission experiment

This continues the [stock guest baseline](guest-baseline.md) under `TASK.guest.admission-design` and
`TASK.guest.admission-probe`. The original APK and guest image remain pinned by the baseline input manifest.
The experiment uses disposable writable guest state and stops at the next observed startup failure.

The exact stock APK can be admitted as UID 1000 under the scoped exception, with all three negative controls
rejected. The next observed startup failure is a missing SELinux process-context mapping. The experiment stops
before application initialization; it does not establish a running Sparrow UI or instrument behavior.

## Framework evidence and design

The guest identifies itself as `Android/sdk_phone_arm64/generic_arm64:7.1.1/NYC/8695018:userdebug/test-keys`.
Its `/system/framework/services.jar` is a stripped 318-byte container. Executable framework code resides in
`/system/framework/oat/arm64/services.odex`, SHA-256
`8f6019912e6a22f220a222fdde2d553f688e81b5a09587caab1623c9e25d0bc9`.
Guest `oatdump` exposes the DEX instructions for `PackageManagerService.verifySignaturesLP`.
They check existing-package signatures first, then shared-user signatures, and throw errors -7 and -8 respectively.
The latter is the baseline failure. Runtime reflection independently confirms the method and parameter types.

The relevant control flow agrees with the
[Android 7.1.1 source](https://android.googlesource.com/platform/frameworks/base/+/android-7.1.1_r13/), at
`services/core/java/com/android/server/pm/PackageManagerService.java`.
This is a comparison of the relevant method, not an assertion that the entire SDK image was built from that tag.
The binary and runtime observations are the authority for this experiment.

The chosen mechanism is an in-memory Frida 16.7.19 hook on that one method in `system_server`.
It calls the original method first. Only an actual `PackageManagerException` with error -8 may be suppressed,
and only after all these conditions pass:

- Package is `com.rigol.scope`; requested and assigned shared-user name are `android.uid.system`, UID 1000.
- There is no already-installed package object, split APK, or child package.
- The parsed signer matches the pinned stock certificate; the shared UID retains the pinned guest certificate.
- Hashing the parser's actual `baseCodePath` yields the pinned stock APK SHA-256.
- File length and modification time remain unchanged while hashing.

All other exceptions are rethrown. Failure to read or interpret a guard also rethrows the original exception.
The hook changes neither signatures nor package-manager settings directly. General signature comparison and
update verification remain original. This is a controlled single-host experiment, not a hardened concurrent
installer: the runner owns the staging inputs and does not introduce a competing writer during installation.

The implementation is [admission-exception.js](../../tools/guest/admission-exception.js).
JavaScript is necessary for Frida's injected Java bridge; shell handles native emulator and ADB processes.
The binary negative-control generator is Kotlin. Python is used only by the upstream Frida CLI distribution.

## Debug configuration and rollback

`adb root` works in the selected userdebug guest. Frida attaches and resolves the framework while SELinux reports
`Enforcing`. **That does not mean the policy is unchanged.** Frida's own
[SELinux helper](https://github.com/frida/frida-core/blob/16.7.19/lib/selinux/patch.c) loads additional instrumentation
permissions into the guest kernel. Policy bytes captured before and after differ. This is a material experimental
change and can mask some later SELinux denials; runtime behavior must be interpreted under that limitation.
Neither host security policy nor the read-only guest image is modified.

The Frida server listens on guest loopback; the dedicated ADB connection forwards it to host loopback port 27043.
The baseline's private ADB server, isolated configuration, and fixed emulator serial prevent accidental device
selection. All raw logs and images stay under ignored `out/guest-admission/`.

Final runs disable Frida preload and crash interception, attach directly to the ADB-observed `system_server` PID,
detach the hook and stop the server before launch, and require no Frida mapping in Zygote's captured process maps.
Guest instrumentation policy remains changed until the guest is discarded. Rollback is to terminate this emulator
and use a new run ID with fresh userdata from the original pinned image; do not reuse a modified guest for a
baseline comparison.
No snapshots or persistent system-image patches are used.

Inspection run `inspect-01` used an incorrect ODEX path and timed out awaiting daemon startup. `inspect-02`
confirmed runtime reflection after explicit background startup. `inspect-03` corrected the ODEX path and captured
the actual bytecode and both policy files. Those diagnostic iterations installed no APK and changed no admission
decision. Their raw evidence is retained; the final inspection is indexed in the admission input manifest.

## Controls and bounded probe

Before loading the hook, repeat the original stock install rejection in each new guest. After loading it, require:

| Input | Required outcome | Guard exercised |
| --- | --- | --- |
| Manifest-only unrelated package requesting system UID | Rejected | Package name |
| Manifest-only `com.rigol.scope`, independently signed | Rejected | Signer |
| Stock copy with an extra ignored APK Signing Block entry | Rejected | Exact APK digest |
| Byte-identical stock APK | Admission may proceed | All guards |

The changed-byte copy must still pass v2 signature verification with the original stock signer. The added entry
is outside the v2 content digest and does not replace signed content. This tests the digest condition independently
of package, signer, and shared UID. It is a clearly named negative fixture, never substituted for the stock input.
The fixture generator refuses unexpected input hashes or existing output files. The other controls use an
experiment-only generated key; private keys and APKs remain local and are not project deliverables.

Any unexpectedly admitted control or missing hook event stops the probe before stock installation. For admitted
stock, record the installed APK hash, package UID, shared-user certificate state, and bounded launch evidence.
Repeat from a fresh guest, retain screenshots and crash evidence, and stop at the first newly observed failure.
Do not supply missing libraries, change model data, synthesize devices, or extend the experiment at that boundary.

## Reproduction

Use the baseline's SDK/image/APK setup and its host requirements, plus `uv`, `xz`, Kotlin, a JDK with `keytool`,
and SDK platform 35. The [admission inputs](../../experiments/guest-admission/inputs.toml) pin Frida, SDK tools,
framework artifacts, and the observed controls. Configure `ANDROID_SDK_ROOT` locally, then run:

```sh
tools/guest/prepare-admission.sh
tools/guest/build-admission-controls.sh
tools/guest/run-admission.sh probe-NEW probe
kotlinc -script tools/guest/VerifyAdmission.main.kts out/guest-admission/probe-NEW
```

Acquisition installs Frida in an ignored virtual environment. The fixture builder requires a new control directory;
retain an existing directory and its provenance instead of overwriting it. Newly generated fixture keys produce
different certificate and APK hashes for the two synthetic APKs; each run records them. The deterministic
changed-byte control retains the stock signer and has the fixed digest recorded in the manifest.

Each run snapshots its source and executes the helper scripts from that snapshot. The runner verifies baseline
inputs, SDK tools, the Frida server and guest framework hash. It preserves phase reachability even if later evidence
collection fails. The independent Kotlin verifier checks the full raw checksum index, exact hook decisions,
ordinary install rejection before instrumentation and after detachment, installed bytes, stored package and
shared-UID certificates, lack of a Frida mapping in Zygote, and the actual failure/tombstone evidence.

The emulator has a 600-second outer bound; individual ADB calls have 15-, 20-, or 30-second bounds.
The hook client has a 45-second normal lifetime and a 180-second outer bound. Normal completion unloads its script
and detaches through the upstream CLI's cleanup path. Launch waits at most 30 seconds, followed by 15 seconds of
observation. The runner records the `system_server` PID before hook loading, after detach, and after observation.
The `am start -W` exit code is retained separately: a timed-out wait is not a successful application launch.

## Observed checkpoint

The final paired runs are indexed in [results.toml](../../experiments/guest-admission/results.toml).
Both reproduce the ordinary install rejection, reject all three controls for the intended guard, and admit only
the exact stock APK. The pulled installed APK has the original SHA-256. Package state assigns UID 1000 while
retaining the stock package certificate and the different original certificate on `android.uid.system`.
Reinstallation after hook detachment again fails the original shared-user signature check.

The next boundary is **SELinux process-context assignment in the Zygote child**, before application initialization:

```text
seapp_context_lookup: No match for app with uid 1000, seinfo default, name com.rigol.scope
selinux_android_setcontext(1000, 0, "default", "com.rigol.scope") failed
```

The child aborts with SIGABRT. Native tombstones point to ART/Zygote, not `libscope-auklet.so`.
The launch wait times out; no surviving Sparrow process is found. The `probe-06` screenshot shows Android's
`RIGOL.SCOPE has stopped` dialog; `probe-07` shows a black screen. Neither shows a running oscilloscope UI.
Sparrow initialization, native instrument-library
execution, model selection, and hardware interaction are not established by these runs.

The captured guest `seapp_contexts` has `user=system seinfo=platform domain=system_app`, but no mapping for
`user=system seinfo=default`. This directly explains the observed lookup failure. Merely admitting an APK to a
shared UID does not make its signer a platform signer or provide its required SELinux labeling.
Package-manager logs also retain signature-permission denials; admission is not full vendor-environment fidelity.

### Diagnostic iterations

The final paired proof excludes earlier harness-development runs. `probe-01` rejected the changed-byte control
because Java `long` wrappers were compared by object identity; string-value comparison fixed that guard, and stock
installation had not been reached. `probe-02` first established admission and the SELinux failure, but Frida's
default preload and crash interception contaminated the crash frames. Final instrumentation disables both.

`probe-03` reproduced the ordinary Zygote abort without a Frida mapping, but editing a running shell helper caused
an extra launch attempt. That run was interrupted and its end-only phase summary incorrectly said `not_reached`;
the raw log demonstrates otherwise. It is retained as diagnostic evidence only. Helpers now execute immutable
per-run snapshots and write phase reachability before later collection steps. The final pair uses those fixes.

`probe-04` completed the controlled startup attempt. Its attempted repeat, `probe-05`, admitted stock but crashed
`system_server` during instrumentation teardown, before launch. The original-policy restoration check stopped it.
That failure is retained and is not counted as a successful startup probe. The Frida CLI's SIGTERM handler cancels
cleanup I/O; the normal path now waits for its quiet-mode deadline to unload and detach instead of signaling it.
This explains why a different teardown path was tested; it does not establish every cause of the native crash.
Final runs require unchanged `system_server` PIDs, successful ordinary rejection after detach, and no
`system_server` crash or Frida frame in the crash evidence. Claims of stability apply to those bounded observations.

Fixture development also rejected a non-page-aligned signing-block addition before any guest use. The final
4096-byte entry preserves both the APK's verity alignment and its original v2 signature, as independently checked
by `apksigner` and by the guest reaching the digest guard.

## Next decision

Stop here. Evaluate a narrowly scoped signer/package-to-`seinfo` assignment for this same exact APK, with negative
controls and an explicit choice of guest domain. The guest's `platform` to `system_app` mapping is a candidate
research configuration, not established vendor policy. Preserve both prior baselines and the APK bytes.
Do not infer that removing this labeling barrier would resolve permissions, native dependencies, or hardware.
No context mapping or additional startup substitution was applied, and no successor task was admitted.
