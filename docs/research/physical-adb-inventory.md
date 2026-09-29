# Physical ADB inventory and accession decision

ADB responds on TCP 55555 without an authentication prompt. The observed session
runs as `uid=2000(shell)`, not root. `getprop` reports Android 7.1.2/API 25,
RIGOL system version 1.5.3, `service.adb.tcp.port=55555`, `ro.adb.secure=0`,
`ro.secure=1` and `ro.debuggable=1`. These are specimen observations, separate
from the community boot-image reference that supplied the candidate endpoint.

The storage name is now observed rather than assumed: `/dev/block/mmcblk0`,
61,132,800 sectors of 512 bytes, or **31,299,993,600 bytes**. It has 16 exposed
partitions. The by-name directory is under
`/dev/block/platform/fe320000.dwmmc/by-name`; `/dev/block/by-name` is absent.
The full mapping and sysfs sizes are retained privately. `/system` is mounted
read-only; `/rigol`, `/data`, cache and metadata are mounted read-write. The raw
whole-device node is mode 0600, owned by root, so the current shell cannot read it.
No separate eMMC boot-area or RPMB node appeared in the inventory; a future
`mmcblk0` image must be described as the exposed user-area image, not proof that
all controller-managed storage has been acquired.

The installed package paths are `/data/app/com.rigol.scope-1/base.apk` and
`/data/app/com.rigol.webcontrol-1/base.apk`. System package records also exist
under `/system/app/Sparrow` and `/system/app/Webcontrol`. Preserve those separately
from `/rigol/app` copies: an update package is not necessarily the active APK.
Sparrow's package version is `00.01.00.00.00`, versionCode 1008000; Web Control's
is `00.01.02`, versionCode 1. These strings still do not settle firmware byte identity.

`/rigol` and its visible data are readable by the shell. The inventory includes
calibration files, `Key.data` and `vendor.bin`; their contents are not yet acquired.
The visible `/rigol/app/Sparrow.apk` size is 38,068,375 bytes, differing from the
38,166,679-byte local stock `.26` APK. That establishes a size difference for this
copy, not the hash or identity of the installed `/data/app` copy.

## Evidence quality and preparation failures

Three separate runs are retained under `out/physical/`:

- `mho984-adb-inventory-20260929T030302Z`: host logging error before the first
  ADB invocation; no ADB attempt. Capture stopped gracefully, 22/22/0 counters.
- `mho984-adb-inventory-20260929T030405Z`: connection, `id` and `getprop` succeeded;
  compound `exec-out` invocations were overquoted and failed. Their output is
  preserved as failure evidence, not a storage inventory. Capture: 162/162/0.
- `mho984-adb-inventory-20260929T030514Z`: corrected non-PTY `adb shell -T`
  inventory, including partitions, mounts, block mapping, processes/listeners,
  filesystem metadata, package paths/versions and acquisition-tool availability.
  Capture: 760/760/0, graceful exit zero, complete stored packet records.

Missing partition-specific sysfs attributes and the absent `/rigol/lib` directory
are recorded in stderr. Composite shell status is not proof that every component
succeeded; the individual output and errors were inspected. `tar`, `dd`,
`blockdev` and `stat` were located; `sha256sum` was not found on the command path.
Host-side hashing remains available. No dump, root transition, remount, reboot,
authentication approval, entitlement change or USB connection occurred in this batch.
Temporary host addresses were removed and full host network preferences matched
the baseline after each run. Known host-local discovery was retained separately
from ADB. The exact private evidence hashes are in the result manifest.

## Decision

Prioritize logical accession and the active specimen APKs immediately. Preserve
`/rigol` as a separate logical corpus, plus active application directories and
relevant system/configuration files. Extract native libraries locally from the
acquired APKs and compare against the existing stock/community corpus before
further emulator implementation.

The operator has now explicitly authorized one `adb root` attempt, with daemon
restart and subsequent `id` verification, to enable read-only acquisition. That
new transition belongs in the next admitted batch; the inventory did not perform
it. The operator also authorized maintaining only the existing isolated lease,
with no gateway, DNS or forwarding. No device reboot, remount or policy change
is included.

Raw acquisition must use the witnessed device and exact size. The host has roughly
492 GiB available, sufficient for two 31.3 GB reads plus separate full captures
and the logical corpus. Preserve the first raw image unchanged and acquire a
second independent read if access and runtime permit. Because Android and `/rigol`
are live and writable, matching whole-device hashes are desirable but not promised;
a mismatch requires preserved evidence and localized comparison, not overwriting
the first read. No quiescing or filesystem freeze is authorized here.

Physical entitlement changes and the physical 1 GHz transition remain outside
this acquisition batch. The next software work serves specimen accession,
binary comparison and disposable-guest validation.
