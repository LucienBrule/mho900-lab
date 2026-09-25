# Bounded calibration filesystem construction

The private loader observer is validated. The independent filesystem task remains open because run02 failed before
creating `/rigol`: `mount -o remount,rw /` returned `No such device`. No alternate command was tried in that run.

The pinned API25 ramdisk remounts rootfs read-only during `post-fs`. Its Toybox mount dispatcher and embedded version
match the Android 7.1.1 implementation's one-operand remount behavior: lookup in `/proc/mounts` already supplies the
rootfs device, directory, and type. Explicitly spelling those operands would repeat the same transition.
The reference source is
[AOSP Toybox mount.c][mount-source].

[mount-source]: https://android.googlesource.com/platform/external/toybox/+/android-7.1.1_r1/toys/lsb/mount.c

The exact guest binary remains authoritative; matching reference behavior is not proof of every build input.

Select a deterministic derivative of the pinned emulator ramdisk adding exactly one empty root-owned `rigol` directory
with mode 0755. Preserve every original archive entry, content, metadata, and the original compressed image. Do not
change init scripts or guest policy. Verify the complete archive delta and reproducible output before booting it.

Before fixture mutation, record and validate live mountinfo, mounts, root and mountpoint metadata, labels, enforcement,
system_server PID, processes, and package inventory. Require a read-only rootfs mounted at `/`, an empty `/rigol`, no
existing mount at that path, and no stock application. Any unexpected state ends this candidate.

Execute exactly one predeclared guest command:

```sh
mount -t tmpfs -o rw,nosuid,nodev,noexec,size=4m tmpfs /rigol
```

Only if it succeeds, create `data/default`, install the two byte-identical stock default assets, and check
full roundtrip hashes, ownership, permissions, mount flags, labels, and the four absent primary/ADC paths. Capture final health even
when setup fails. Do not try alternate mount forms or relabel policy within this run. The selected 4 MiB limit
bounds the fixture above its approximately 1.8 MiB contents. No stock application executes in this test, so
stock-UID readability and actual loader behavior remain questions for a subsequent admitted experiment.

This replaces the earlier writable-root/remount branch with a single explicit construction. The existing decision gate
still requires both independently verified results before admitting stock execution. Local source, guest binary, and
init evidence is pinned in `out/calibration-filesystem/static-01/analysis.toml`; the experiment manifest will bind those
inputs and the final implementation before execution.
