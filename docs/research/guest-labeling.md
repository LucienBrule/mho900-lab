# Scoped guest process labeling

This experiment tests whether the byte-identical stock Sparrow APK can pass
Android process creation after the admission experiment's SELinux lookup failure.
It uses the same pinned API-25 ARM64 guest, fresh userdata, original signature
checks, exact-stock admission guards, negative controls, and normal instrumentation
teardown described in [guest admission](guest-admission.md).

## Hypothesis and scope

The guest has an existing `user=system seinfo=platform` mapping to `system_app`.
The admitted package instead received `seinfo=default`. Assigning `platform` to
that exact package's in-memory `ApplicationInfo.seinfo` should resolve the missing
process-domain mapping. This is a research guest assumption, not a reconstruction
of the instrument's original SELinux policy.

`tools/guest/labeling-exception.js` first executes the original signature check.
Only its shared-UID error, with all existing package, signer, UID, new-package,
unsplit-package, platform-certificate and exact-file-digest guards satisfied,
permits the assignment. It also requires the previous label to be `default`
and the application UID to be 1000. It changes no certificate or permission grant.
The three negative fixtures must remain rejected and produce no labeling event.

The guest framework's field is inspected at runtime. An `oatdump` of the actual
pinned `scanPackageDirtyLI` implementation captures assignment ordering. The
cached AOSP reference places `SELinuxMMAC.assignSeinfoValue` before
`verifySignaturesLP`; the actual guest evidence must establish the relevant order.
No app method is intercepted. The PMS hook exits normally, the Frida server stops,
and Zygote maps are checked before launch. A read-only `ps -Z` sampler captures
the process context. Frida's previously documented guest-policy changes remain
a fidelity limitation; enforcing mode alone does not imply pristine policy.

## Reproduction and rollback

Configure `ANDROID_SDK_ROOT` to the locally installed pinned SDK, then run:

```sh
tools/guest/run-admission.sh label-01 label
tools/guest/run-admission.sh label-02 label
```

Choose unused run IDs. Each run snapshots its executable helpers under
`out/guest-admission/<run>/source/`, captures logs, screenshots, package state,
native crash evidence and a checksum index, and tears down its isolated emulator.
Rollback is disposal of that run's guest state. No original image, APK or firmware
file is rewritten. No host security policy or physical instrument is involved.

## Findings and decision

The exact field is present in the guest. In the actual `scanPackageDirtyLI` DEX,
`assignSeinfoValue` occurs at code offset `0x05b0`, before `verifySignaturesLP` at
`0x06ef`. Both offsets refer to that method's DEX instruction stream, not ELF
addresses. The scoped assignment changes `default` to `platform`, and installation
also relabels the app data directories as `system_app_data_file`.

The first clean run (`label-01`) creates a surviving `u:r:system_app:s0` process,
calls `SplashActivity.onResume`, and displays the app's RIGOL logo and loading
spinner. It reports a successful activity launch in 370 ms, with no crash-buffer
entries. The process remains in the splash activity through the approximately
30-second observation. The `ps -Z` sampler requests 40 samples but is bounded by
the helper's 30-second ADB timeout; its expected timeout is not an app failure.

The three negative fixtures remain rejected. The installed APK, package signer,
and shared-UID certificate remain unchanged. A reinstall after hook removal again
fails the original signature check. `system_server` retains PID 1064 before and
after detach and observation. `VerifyLabeling.main.kts` checks the raw checksum
index, controls, certificates, framework order, label, lifecycle, and server PID.

An AndroidX missing-class diagnostic appears during view inflation, but it is
followed by activity resume and rendering; it is not evidence of a fatal startup
exception. A screenshot alone would not establish this distinction.

The second clean run (`label-02`) independently passes the same verifier and
controls. Its screenshot shows the spinner against black without the logo seen
in the first run. Both remain in `SplashActivity`, with empty crash buffers and
the same process domain. The screenshot variance is retained; neither image is
treated as proof of a complete or useful UI. Raw evidence and source hashes are
indexed in `experiments/guest-labeling/results.toml`.

The process-labeling hypothesis is supported. The remaining splash screen is an
unresolved startup dependency, not a useful instrument UI and not yet proof of a
hardware dependency. The successor batch in `.agents/plans/guest-startup.yaml`
will inspect the exact stock startup code and capture a bounded live wait trace
without substituting native or hardware behavior. No material architecture change
has been established by this result.
