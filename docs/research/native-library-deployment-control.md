# Normal APK native-library deployment control

The disposable API-25 Android guest loads a same-name library from the installed
package's native-library directory before its embedded APK member. The override
survived a guest reboot. Removing the introduced file restored embedded loading,
also across reboot. The installed signed APK remained byte-identical throughout.

This resolves the package-loader hypothesis raised in
[physical installation readiness](physical-install-readiness.md). It establishes
a candidate mechanism for preserving the original APK and its signature; it does
not yet establish full Sparrow startup or deployment on the physical instrument.

## Experiment

`tools/guest/native-loader-control/` contains the manifest, Java Activity, tiny
JNI library, offline builder, isolated runner and independent artifact verifier.
The package is installed normally through Android package management. It uses
API 25, `android.uid.system`, `extractNativeLibs=false`, a guest platform signature,
and the same `System.loadLibrary("scope-auklet")` operation recovered from the
stock API class. It sets no library search path and creates no custom class loader.

The uncompressed, page-aligned embedded native library returns marker 17. A second
library with the same JNI symbol and basename returns marker 18. Both are tiny,
dependency-free probe libraries; neither is a copy or modification of stock
Sparrow or Auklet. The Java Activity records the marker, `findLibrary`, ordinary
class-loader description, application native/source directories, PID and its own
actual process maps. The runner separately records boot identity and package state.

The probe APK has a verified v2 signature; its SHA-256 is
`bfd4e42abff53d971ad5e0c9485df9d259e72f2622d07ffd93f12a5134bcdfc7`.
It was pulled and compared byte-for-byte after every phase. Signature invariance
follows from that byte identity and the verified signed input, rather than from
merely observing that Android accepted installation.

| Phase | Marker | Selected and mapped native file | Boot |
| --- | --- | --- | --- |
| Normal install/start | 17 | Embedded APK member | A |
| Introduce sidecar, force-stop/relaunch | 18 | Standalone package-native file | A |
| Normal guest reboot/relaunch | 18 | Standalone package-native file | B |
| Remove sidecar, force-stop/relaunch | 17 | Embedded APK member | B |
| Normal guest reboot/relaunch | 17 | Embedded APK member | C |

A, B and C are three different retained boot IDs. Each process restart produced a
new PID. No package reinstall, APK modification, extracted-native setting change,
cache deletion or application-data clearing was used between phases.

The observed ordinary `PathClassLoader` lists these native directories in order:

1. The package's `lib/arm64` directory.
2. `base.apk!/lib/arm64-v8a`.
3. `/system/lib64`.
4. `/vendor/lib64`.

Both `findLibrary` and actual mapping paths agree with the marker. Baseline and
rollback maps include the APK-backed ELF at the independently calculated aligned
ZIP member offset; override phases map the standalone file. This is direct guest
observation of precedence, not an inference from directory existence.

The runner required the target filename to be absent, staged marker 18 under a
different basename, pulled it back for hash comparison, set ownership/mode to
system:system and 0644, and renamed it into place. The resulting file label was
`u:object_r:apk_data_file:s0`; no relabel or policy adjustment was performed. Removal
affected only that introduced file.

## Isolation and evidence

The pinned API-25 default ARM64 image was used with fresh userdata and a dedicated
ADB server and emulator. Emulator and ADB processes were confined to loopback by
the existing per-process host sandbox; mDNS discovery was disabled and checked.
The host-only network control passed. No physical transport was selected or
contacted.

Guest SELinux remained Enforcing and its raw policy bytes were identical across
all eight health checkpoints, including both reboots. `system_server` remained
unchanged within each boot. The two deliberate reboots were recorded separately;
they are not concealed as continuity. Cleanup completed without errors.

Run: `out/guest/native-loader-control-01`, observed 2026-09-29
17:20:53–17:21:33 UTC. The runner accepted all five phases. The independent
`verify.py` reconciled build pins, signed APK identity, marker/path/mapping results,
actual boot changes, process changes, policy bytes, health and transport selection.

The evidence seal contains 482 files, with SHA-256 of `sealed-sha256.txt`:
`23cae79f45b3dc3f8719c090d7d9761c8df963ff37e6aa10651cef909687a168`.
It covers frozen build/source artifacts, command results, phase observations and
verification. Disposable runtime disk images and emulator home directories remain
local but are explicitly outside this observation seal.

## Scope and next decision

The mechanism worked on the pinned Android 7.1.1/API-25 guest. The physical specimen
reports a 7.1.2 network stack and has its own platform/package implementation.
The probe uses a normal shared-system-UID APK and the relevant loading operation,
but it does not reproduce Sparrow's complete lifecycle, native dependency graph,
updated-system-package history or instrument initialization. A dependency-free
marker cannot establish that all Auklet dependencies and JNI callbacks resolve
correctly after a physical override.

This result supports a narrowly scoped physical candidate: preserve the acquired
signed APK; introduce only the verified derived native library into the freshly
resolved package-native directory; preserve original metadata and prove actual
loaded file/hash; then verify full UI, identity, policy and ordinary options across
a deliberate reboot. That candidate still needs its admitted deployment harness
and a derived standalone-library observation profile. The probe itself is not
that harness.

The tested rollback mechanism is removal of the one introduced library followed
by restart/reboot and proof of original APK-backed loading. Physical rollback must
verify those observations rather than assuming guest behavior transfers. No
physical deployment occurred in this task. Neither a marker transition nor enum
18 establishes the instrument's analog 1 GHz transfer function.
