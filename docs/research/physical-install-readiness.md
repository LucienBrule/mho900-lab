# Physical installation readiness

Historical readiness analysis. The proposed loader control and physical stages
have since completed; see the [native-loader control](native-library-deployment-control.md),
[ordinary-option results](physical-ordinary-options.md), and
[D-capability persistence](physical-d-capability.md). The alternatives below
explain the decision at the time and are not outstanding work.


The ordinary-option path is concrete: use the documented SCPI installer with the
exact acquired-input candidates already accepted by stock code in the disposable
guest. Persistent D-capability deployment is a separate question. The component
comparison proves the native transformation, not Android package deployment or
full Sparrow startup.

This task inspected retained evidence and prepared private request artifacts. It
did not contact the instrument, execute a guest, install an option or change an
APK. The stored-FRAM preservation task and the installation decision remain gates
for subsequent execution.

## Ordinary options

The preserved official MHO900 Programming Guide, SHA-256
`a671c065bd04a85d05e9d4cef732df3ba4884c2218054f64d1a83fb5a43cffd5`,
section 3.24.16, printed pages 291–293, documents
`:SYSTem:OPTion:INSTall <license>` and the `series-option@code` format.
It specifies no return value and directs callers to `:SYSTem:OPTion:STATus?`
to determine success. TCP 5555 is separately implementation-derived and
[physically observed](physical-stage-two-b1-result.md).

The [acquired catalog](acquired-option-catalog.md) supplies ten individually
accepted candidates, with original consumer observations and process/reboot
persistence. The final source seal is
`0724e39fbfb4e2d320b2c4c48d6243f8b566d63a47d2049ab7fb9f1118758781`.
Its ten saved license files and corresponding witnesses agree. Preparation
verified the complete seal and copied their exact wire strings into ten private,
unsent request files; it generated no new tokens. These are research-produced,
guest-validated candidates, not claims of vendor-issued licenses.

| Installation order/name | Documented status selector |
| --- | --- |
| FlexA | FLEX |
| BWU05T08 | BWU05T08 |
| AFG100 | AFG100 |
| AFG50 | AFG50 |
| AUDIOA | AUDio |
| AUTOA | CAN-FD |
| AEROA | AERO |
| RLU05 | RLU-05 |
| BWU03T05 | BWU03T05 |
| BWU03T08 | BWU03T08 |

Begin with FlexA alone under the existing isolated-network capture procedure.
Reconfirm identity and the recorded option baseline, send its one exact request,
then query status. The installer has no response to wait for. Status queries may
be bounded observations of asynchronous completion; an uncertain outcome must
not cause automatic retransmission of the install command. Retain raw requests,
responses, packet capture, UI observations and the resulting stock-written file.

Require the candidate alone to become enabled, all prior states to remain stable,
and the saved file to match its accepted witness. The native outer return zero
is not a success criterion. A malformed or rejected install may still change
saved time or rejection counters. A diagnostic `:SYSTem:ERRor:NEXT?` is documented
to remove a queue entry; if used, record that additional intervention explicitly.

After the first accepted transition, continue the tested order one candidate at
a time, preserving a conclusion before the next. Exclude BND: its bundle path
can remove individual files. Do not replace Key.data or vendor data, copy guest
private storage onto the instrument, or install files directly in place of the
ordinary installer. The physical application already runs its complete lifecycle;
the guest component did not establish those live notifications, timers or saves.

After the cumulative checkpoint, perform one separately recorded normal reboot.
Require a new boot identity, stable UI, unchanged public identity and stock
application pins, ten enabled documented selectors, BND still disabled, matching
license/key files, and raw/effective bandwidth still 17/17. Reacquire private
cache/stored evidence through the admitted readers as appropriate; compare rather
than assume that the guest saved-time-only delta describes the full lifecycle.

Preserve pre-install files, metadata, option replies and stored FRAM before this
sequence. The documented uninstall command removes **all** official options and
requires restart; it is not a precise single-option undo and does not establish
restoration of private counters/time. Do not treat a blanket uninstall or an
unvalidated FRAM write as automatic rollback.

## Persistent D-capability deployment

The [complete acquired comparison](acquired-combined-capability.md) established
MHO984 identity, selected MHO984D record and raw/effective enum 18 before and after
stock option policy, including process and guest reboot. The derived library is
`09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e`;
its stock ancestor is
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
Exactly 27 bytes differ within the 32-byte span at file/ELF offset `0x42949c`.
The ten ordinary licenses remain unchanged. This is software policy evidence,
not a 1 GHz entitlement mechanism or measured analog bandwidth.

Fresh offline inspection of the acquired active APK confirms:

- Package `com.rigol.scope`, shared UID `android.uid.system`, min/target API 25,
  versionCode 1008000 and `extractNativeLibs=false`.
- APK v2 signature verification succeeds; v1 is absent. The signer certificate
  SHA-256 is `f48e7189aac174df7fd19acf58b6d15832760fcf25ac0a6d4bcd5fc1974d4c03`.
- The specimen-matched `API` class uses `System.loadLibrary("scope-auklet")`,
  not an absolute `System.load` call. Original JNI initialization therefore
  depends on the application's class loader and namespace.
- Retained package state identifies an updated system application under
  `/data/app`, with an empty `lib/arm64` directory. Physical maps show Auklet
  loaded directly from the uncompressed, aligned APK member. Inactive system
  and `/rigol` APK copies have different bytes and are not the active target.

Editing the packaged native member changes signed APK content. An arbitrary
replacement signature cannot be assumed to satisfy the existing package/shared
UID identity. No matching private signer was found in the bounded local review;
the available disposable-guest platform signer is a different identity. Repacking,
re-signing, replacing the active APK in place or editing package-manager state is
therefore not a deployment procedure established by the component experiment.

The smallest candidate is a standalone native file in the active package's own
native-library directory, leaving base.apk and its signature intact. **Its search
precedence is unproven.** Empty directory metadata does not prove the loader will
use a newly placed file when `extractNativeLibs=false`; the ART component's
explicit library path proves nothing about this package-loader ordering.

The next bounded control should install a minimal API-25 APK through normal
package management in a disposable guest, with the same extraction setting and
`System.loadLibrary` usage. Package a tiny library returning a known marker,
record `findLibrary`, actual mappings and its result, then place a distinct
same-name library in the reported native-library directory. Test fresh-process
and guest-reboot loading, APK/signature invariance, and removal/restoration of the
original lookup. Existing SDK build-tools, JDK, guest platform test key and
freestanding ARM64 compiler support that control. No new implementation or run
was performed by this readiness task.

Only a successful control supports a physical deployment candidate. Freshly
resolve the active package directory; preserve its ownership, mode and labels;
require the target file to be absent; stage and roundtrip-check the exact derived
library; publish only that file; then perform the deliberate application/boot
transition. Preserve the stock APK and original acquired native independently.
Rollback for this candidate is removal of the one newly introduced library,
followed by a controlled restart and proof of stock APK-backed loading and 17/17.
Do not remove an unexpected pre-existing file or rely on a reboot to resolve an
unknown loader result.

Verification must establish which library actually loaded, not just that a file
exists. A fixed derived-hash, standalone-library observation profile is needed
if loading moves out of the APK; the current stock APK-backed readers must not be
silently relaxed. Require exact derived mapped bytes, MHO984 public identity,
18/18 cached policy, all ten ordinary options and stable full UI after reboot.
Also prove rollback loading in the disposable control. If package loading rejects
the override, stop that hypothesis and select another bounded deployment design.
Physical transfer-function measurement remains a later, separate requirement.

Private preparation artifacts are under
`out/overnight/physical-install-readiness/`: the request plan and unsent bytes,
fresh manifest/signature output, original package-directory metadata, and a
concrete command/gate worksheet. They contain unit-specific evidence and are not
part of tracked source.
