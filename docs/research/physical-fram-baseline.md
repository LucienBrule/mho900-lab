# Physical FRAM baseline acquisition

The first stored-image attempt stopped at adapter metadata validation, before
staging or executing the FRAM reader. Its fresh stock private-cache observation
passed, but the specimen's older `stat` implementation rejects `-L` and does not
implement the requested device-number format specifiers. The controller preserved
that failure rather than guessing the device identity or weakening its gate.

This was a metadata-tool compatibility failure, not a FRAM transfer failure.
No direct FRAM transaction, option installation or capability change occurred.
The scope-facing capture contains 43,031 complete frames and zero kernel drops;
recorder exit was graceful. Temporary host networking was removed and the saved
network preference files match their baseline bytes.

The private run `mho984-fram-baseline-20260929T171200Z` is sealed with manifest
SHA-256 `4c3a71570a2662187cf5d7f3a4bd90b8caf5062ebe42607cc0e89fd8206fc43d`.
Its capture SHA-256 is
`929e18014b267b722008b85436a417cd8c423e4bd80dd3b074465e036fab1874`.

The next bounded correction is a native metadata-only probe using ARM64 stat
semantics, tested in the disposable guest. It should follow the exact stock
process descriptor and compare it with the device node and sysfs adapter,
without opening the device or issuing an ioctl. A new acquisition run may proceed
only after that correction is validated; the original failure remains immutable.

The normal-APK loader control independently establishes a candidate signed-APK-
preserving deployment method in the guest. That does not waive the stored-state
preservation requirement before physical option installation.
