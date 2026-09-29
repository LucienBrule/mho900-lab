# APK-backed cached-identity geometry

The [first physical cached observation](physical-cached-identity-observation.md) stopped correctly before
memory access because its reader required a standalone library. The next offline batch resolves the actual
container geometry without contacting the instrument or changing the existing reader.

## Established offline

The previously acquired active APK is pinned to SHA-256
`6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b`.
Its unique uncompressed, unencrypted Auklet entry starts at `0xf05000`, has length 12,453,760 and hashes to
stock native SHA-256 `4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
The resolver verifies local/central ZIP metadata agreement, name, bounds, page alignment, CRC and payload
hash before interpreting ELF load segments. ZIP data-descriptor variants are deliberately unsupported.

The preserved physical maps yield one coherent load bias across three Auklet-backed rows. Nine other rows
share the APK path and inode but have file offsets outside the native entry. Those rows include other
libraries and non-executable APK views; they cannot be treated as Auklet load segments just because their
inode matches. The resolver rejects other APK rows overlapping the selected module's full virtual extent.

All file-backed PT_LOAD pages must be covered exactly with segment-appropriate permissions and offsets.
Both requested cached ranges remain ordinary private writable non-executable data within the stock ELF.
Their APK-relative backing offsets are `0x1ac0cf0` for DNA and `0x1ac0d1c` for file keys. Runtime addresses
are recorded privately as predictions, not acquired values.

Sixteen deterministic negatives reject a wrong APK pin, inconsistent local headers/name/size, corrupt
payload, truncated archive, wrong device identity or entry offset, writable executable/shared text,
wrong inode/deleted path, inconsistent data offset, non-writable cached data, missing executable segment
and a second candidate loaded module. No negative test edits the original artifacts.

The implementation reuses the existing independent Python ELF/maps verifier and Python's ZIP parser.
This keeps the offline comparison in the same verification ecosystem; it is not a device-side parser.
The pinned whole-APK hash intentionally limits support to the acquired build rather than promising a
general-purpose ZIP loader.

## Limits and next experiment

The maps are physical evidence; the APK hash belongs to the earlier acquisition. This batch has not freshly
hashed the currently mapped APK, read process memory or established physical read permission. No guest or
physical connection occurred. No cached identity or Key.data coherence result follows from address geometry.

The next bounded experiment should add an explicitly pinned APK-backed reader mode and test it against a
disposable process with real APK-backed mappings. Preserve the standalone reader evidence. A native fixture
can map the stock APK's original load pages privately, declare synthetic cached bytes, and expose the same
container-offset geometry without initializing the instrument or executing hardware-facing stock routines.
Use fresh process identity, negative controls, exact 8/16/8/16-byte reads and independent address verification.
That tests the new backing contract without repeating the already established entitlement installation work.

Only after that control passes should a new physical task be considered under the operator's on-scope
observation authorization. It must freshly verify the mapped APK and retain the same bounded read budget.
Entitlement installation, model changes, physical reboot and calibration are not consequences of this decision.

## Reproduction and evidence

Run `tools/guest/resolve-apk-cached-identity.py` with explicit `--apk`, `--maps`, `--mapped-path` and a fresh
`--output` path. The result is private TOML because it includes predicted process addresses. The script
opens only local files and never connects to a device.

Run: `out/overnight/apk-geometry-01/result.toml`.
Result SHA-256: `84108632710dff967fd9708efebd38873d3d88748ca8555c280829006c3bd0d8`.
