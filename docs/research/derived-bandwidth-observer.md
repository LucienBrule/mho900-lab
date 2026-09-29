# Fixed derived-library bandwidth observer

A separate standalone-library reader is ready for deployment verification. It
accepts only the already tested derived Auklet ELF and reads two cached four-byte
bandwidth fields twice: exactly 16 requested process-memory bytes. The original
stock standalone and APK-backed profiles remain unchanged.

The accepted derived SHA-256 is
`09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e`.
The fixed ranges are:

| Field | ELF virtual address | File offset | Bytes per sample |
| --- | --- | --- | --- |
| Raw bandwidth | `0xbbcce4` | `0xbbbce4` | 4 |
| Effective bandwidth | `0xbbcce8` | `0xbbbce8` | 4 |

These addresses are ordinary private, writable, non-executable file-backed data.
They are not mapped instrument registers. The ELF's writable PT_LOAD has a
`0x1000` virtual/file displacement; treating a virtual address as a file offset
would read the wrong bytes.

## Implementation and scope

`tools/guest/derived-bandwidth-reader/build.py` applies checked, count-exact edits
to pinned `read-cached-identity.c`, source SHA-256
`1a49ad8d0577cf4b29fa69d686df587e995fa3d9eec7cb7178689613aa657438`.
It changes the accepted ELF pin, fixed ranges, sample widths and semantic field
names. It does not change the predecessor's process/file/mapping validation.
The source profile and existing readers are preserved byte-for-byte.

The reader opens one read-only `/proc/PID/mem` descriptor. Before memory access it
requires the expected PID/starttime/boot identity, complete regular ELF and hash,
exact PT_LOAD layout, backing device/inode/path, unique executable load bias and
ordinary data mappings. It rejects deleted, substituted, anonymous, shared or
executable target data. It preserves raw process stat, boot and maps epochs
before, immediately after opening memory, between samples and after both samples.
Relevant library rows and file metadata must remain stable; unrelated mappings
may change and are reported separately.

The four reads are `[4, 4, 4, 4]`; two samples are each eight bytes, in raw/effective
order. The reader preserves partial-read evidence and fails on errors or short
reads. File hash/metadata are checked again after sampling. Repeated equality is
an observation over two bounded samples, not an atomic snapshot guarantee.

There is no process attachment, native function invocation, target write,
permission workaround, fallback reader or arbitrary address input. The accepted
pin identifies the backing ELF and its mappings. The 16-byte budget does **not**
hash resident instruction pages or prove that no other actor changed private
executable pages; callers must not expand the claim to a complete memory image.

## Guest controls

Run `out/guest/derived-bandwidth-control-01` completed successfully on the pinned
API-25 ARM64 guest, 2026-09-29 17:32:26–17:32:37 UTC.
The fixture maps the exact derived ELF without invoking any of its code. It
writes 18/18 into its own two private cached words. Those values are explicitly
synthetic: this task tests reader addressing and constraints, not stock capability
execution, which was established in the separate acquired component comparison.

| Control | Actual outcome | Process-memory access |
| --- | --- | --- |
| Valid derived file, mapping and epoch | Two equal synthetic 18/18 samples | 16 bytes |
| Deliberately wrong expected hash | Rejected at library hash | No open or reads |
| Stale expected process starttime | Rejected at process identity | No open or reads |
| Out-of-contract range through common validator | Rejected at target ranges | No open or reads |
| Separate fixture with read-only data mapping | Rejected at target ranges | No open or reads |

The mapping rejection uses an actual changed guest mapping, not a forced failure
flag. The exact backing ELF stays unchanged. The independent Python geometry
oracle also rejects that recorded mapping at the ordinary writable-data check.

Host controls exercised the independent geometry oracle and compiled C
SHA/ELF/maps/process parsers, including RELRO splitting, the `0x1000` displacement,
wrong geometry/device/permissions, deleted/anonymous substitutions, ambiguous file
views and overflow. Separate verifier controls rejected altered sample bytes,
read-size accounting and boot identity.

The runner verified staged binary/ELF roundtrips, child-process loopback confinement
and disabled ADB discovery. Guest SELinux stayed Enforcing, policy bytes were
unchanged, and `system_server` stayed unchanged. No physical transport was selected
or contacted. Cleanup completed without errors.

## Invocation and evidence

The built helper is
`out/overnight/derived-bandwidth-build-01/read-derived-bandwidth`:

```text
read-derived-bandwidth PID STARTTIME BOOT_ID ABS_LIBRARY_PATH ABS_NEW_OUTPUT_DIR
```

All five arguments are required. The production observation omits the optional
control mode. The output directory must be new. The expected starttime and boot
ID must be freshly captured by the calling run; a previous process identity is not
authority. A path argument selects only the pinned library, not arbitrary memory.

The output contains `manifest.toml`, `sample-1.bin`, `sample-2.bin` and raw epoch
files. Manifest schema is `mho900-lab.derived-bandwidth-reader/1`; semantic fields
include `raw_band_address`, `effective_band_address`, the two sizes, requested and
returned read counts, file metadata/pin and stability witnesses. Exit 0 means an
accepted observation, 3 a rejected observation, and 4 an evidence-preservation
failure. Acceptance does not mean the observed values equal a requested capability.

The separate offline verifier accepts an observation without any device access:

```sh
python3 tools/guest/derived-bandwidth-reader/verify.py \
  --observation "$OBSERVATION_DIR" \
  --elf "$DERIVED_ELF" \
  --output "$NEW_VERIFICATION_TOML"
```

It independently recomputes ELF/maps addressing, file identity, epoch and raw sample
hashes/bounds. It reports the observed two integers; a deployment caller must still
require the intended values and reconcile the full application state.

Build and evidence pins:

| Artifact | SHA-256 |
| --- | --- |
| Reader binary | `a7c1eda20e814426927a25998b7768e2711fadf2914b64751237118a6d3fc5ff` |
| Generated C reader | `ac23de62204a5e4e465c25d0a2e0d1e6cee44f3c3bab6f75df4d522f719afa39` |
| Build manifest | `8baee05cef8749aa6e14db5a5fd4e2421f141c3fbf3a6c8ed398c1facc664ce7` |
| Observation seal manifest | `1eea4715e980daeca2524d3061fb936a314f84664f90637c69abfe87228d5ca8` |

The observation seal covers 198 frozen build/source, command, control, raw sample
and verification artifacts. Disposable runtime disk images and emulator home
files remain local but are explicitly excluded. The generic observation verifier
and complete guest-control audit both accepted. A separate physical observation
is still required; this control cannot establish physical permission availability
or the specimen's current native-library mapping shape.

## Physical decision

The derived observer is accepted for the separately authorized capability trial,
after ordinary-option reboot persistence passes. Deployment must preserve the
original signed APK and install only the pinned sidecar in the package native
library directory established from current package metadata. Acceptance requires
normal full Sparrow UI, unchanged public identity and intended option states,
unchanged signed APK, an actual standalone derived-library mapping and repeated
18/18 cached samples after normal reboot. If loading or application checks fail,
remove only the introduced sidecar and verify original APK-backed loading after
normal reboot. No claim of measured analog bandwidth follows from this result.
