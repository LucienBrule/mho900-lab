# Calibration filesystem fixture result

`calibration-filesystem-01` succeeded with the frozen single-mount candidate. The derived API25 ramdisk booted with an
empty root-owned `/rigol` directory on read-only rootfs. One bounded tmpfs mount succeeded; the two exact stock default
files were installed and pulled back without a byte difference. The four primary/ADC paths remained absent. No stock
application was installed or started.

The mount reports `rw,nosuid,nodev,noexec,size=4096k`. Directories are mode 0755, files are mode 0644,
and all are root-owned.
The read-only root mount remained unchanged. The directory below the mount initially had `rootfs` type; the mounted
directories have `tmpfs` type and the pushed files have `su_tmpfs` type. These labels are observations;
they do not establish whether
stock `system_app` can read the files. That access path needs static policy review before a stock-loader run.

All 24 setup-command statuses and all five final-health statuses were zero. The three system_server samples retained
PID 1083, enforcement remained enabled, and the final inventory contained no stock application or observer. Teardown
removed the disposable guest; this run did not separately unmount the fixture or test persistence across a reboot.

The frozen independent aggregate verifier accepts the original run. All 143 indexed artifacts match their hashes.
The original ramdisk, stock APK, and stock native library remain unchanged, and the dedicated listeners are absent.
The source manifest pins the candidate before execution. The ramdisk builder's two final builds match byte-for-byte;
an independent archive parser and native gzip/cpio readers confirm the sole added directory and unchanged original
archive records. Its initial rejected inode-inventory check is preserved separately from the successful final builds.

This closes filesystem placement, not stock calibration behavior. The private loader controls and this fixture result
now support a decision at the file-access boundary. The next task must preserve the measured labels and either justify
stock access from the exact policy or isolate the specific missing access rule before whole-loader validation.
The predicted stock statuses remain 192, 1794240, -1; none has yet been observed in the actual stock loader sequence.

Reproduce with the pinned local artifacts:

```sh
kotlinc -script tools/guest/BuildCalibrationRamdisk.main.kts -- \
  local/guest-images/api25-default-r02/arm64-v8a/ramdisk.img NEW_OUTPUT_DIRECTORY
ANDROID_SDK_ROOT=SDK_DIRECTORY tools/guest/run-admission.sh NEW_RUN_ID filesystem
kotlinc -script tools/guest/VerifyCalibrationFilesystem.main.kts -- \
  out/guest-admission/NEW_RUN_ID complete
```

The input manifest selects the already verified derivative and pins its source files. A deliberate source or derivative
change requires a newly frozen candidate; do not rewrite an existing run directory. See
[the result manifest](../../experiments/calibration-filesystem/run01-results.toml) for evidence hashes.
