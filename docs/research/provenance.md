# External inputs and provenance design

Inspected 2026-09-24. This document defines a proposed manifest contract and a bounded inventory, not a completed
artifact-ingestion tool. [Observed inputs](observed-inputs.json) records fresh sizes and SHA-256 values for selected
files. No proprietary payload is copied into the tracked source tree.

## Source hierarchy and useful entry points

All paths below are relative to `local/reversing/`, the untracked location for external inputs. They are locators,
not content identities. Prefer the normalized `firmware-extracted/` tree when several extractions coexist.

| Purpose | Corpus path |
| --- | --- |
| Official `.26` archive | `MHO900_Firmware_Update_v1.00.zip` |
| Normalization inventory | `firmware-extracted/manifest.json` and `firmware-extracted/README.md` |
| Stock GEL | `firmware-extracted/stock-0.26/package/MHO900_Firmware_Update_v1.00/MHO900_Update.GEL` |
| Stock APK | `firmware-extracted/stock-0.26/firmware/app/Sparrow.apk` |
| Stock native libraries | `firmware-extracted/stock-0.26/sparrow/base/lib/arm64-v8a/` |
| Stock platform dependencies | `firmware-extracted/stock-0.26/firmware/{shell,driver,resource,data,FPGA}/` |
| Model analysis and patch specification | `analysis/model-selection/{REPORT.md,patch.json,model-table.json}` |
| Bounded model result and implementation | `analysis/model-selection/{verification.json,verify.py,SUPPORT.md}` |
| Prior integrity report | `analysis/model-selection/source-integrity.json` |
| AFE/filter analysis and experiments | `analysis/three-way/{REPORT.md,SUPPORT.md,verification.json,emulate.py}` |
| Detailed static disassembly | `analysis/three-way/official26-full.asm` |
| NK archives | `MHO900_NK_0.1.2-1.zip` and `MHO900_NK_0.1.4.zip` |
| Effective NK APKs | `firmware-extracted/nk-0.1.2/firmware/resource/mod/apk/Sparrow.apk` and analogous `nk-0.1.4` |
| NK native inputs | `firmware-extracted/nk-0.1.2/sparrow/mod/lib/arm64-v8a/` and analogous `nk-0.1.4` |
| Platform properties | `firmware-extracted/nk-0.1.4/firmware/resource/mod/root/system/build.prop` |
| RK3399/initramfs/DT investigation | `notes/21-SEP-26-1045-MHO900_NK_0.1.2-1-exploration.md` |
| Earlier working record | `notes-bundle/21-SEP-26-session-1-NV-libscope-auket-analysis.md` |
| Manuals and archived product pages | `MHO984D-Intel/` |

The `.26` release notes are UTF-16 text; decode before searching. They identify `.26`, date May 9, 2026, and added
MHO984D support. Release-note date, publication date, retrieval date, embedded firmware version, and wrapper filename
are separate fields. In particular, `v1.00` in the ZIP filename is not the embedded application version.

All 2,650 stock entries matched the existing normalization manifest during this pass. This checks local integrity;
it does not independently authenticate a vendor download. The streamed APK member `lib/arm64-v8a/libscope-auklet.so`
also hashes to the normalized ELF's SHA-256:

```text
4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e
```

The original ZIPs were freshly hashed and match the source digests in that manifest. The entire NK extraction was
not revalidated in this pass. Selected NK inputs are independently hashed in the observed inventory.

Prior session notes describe a vendor download receipt under a separate `outputs/upstream-comparison/` tree.
That receipt was not located in this mounted corpus during the bounded inventory. Do not upgrade a locally matching
archive to independently authenticated origin on that basis; recover the receipt or reacquire from the vendor later.

## Proposed versioned manifest

Use UTF-8 JSON with a documented schema version. Separate content identity, source attribution, transformation,
claims, and local resolution. A digest proves byte identity, not authorship or correctness.

| Record | Required fields and meaning |
| --- | --- |
| Artifact | Stable ID, kind, byte size, SHA-256, media type, distribution classification. |
| Origin | Vendor/community/local-derived kind, original name, URL if known, retrieval time or explicit unknown. |
| Container edge | Parent artifact ID, exact member path, extraction layer, child digest. |
| Derivation | Input IDs, tool/version/hash, exact arguments, working directory rule, output IDs. |
| Claim | Subject ID, evidence category, statement, evidence IDs, locator, assumptions and limits. |
| Experiment | Input IDs, environment ID, fixture IDs, command, timeout, outcome, log hashes, observation time. |
| Environment | Host/guest architecture, Android/API, kernel/image hashes, signing identity, page size, graphics. |
| Local resolution | Root alias and relative path; absolute host paths live in an ignored resolver file. |

Model `ArtifactKind`, `OriginKind`, `EvidenceCategory`, and outcomes as enums/sealed types in Kotlin. Model locators
explicitly: archive member, ELF symbol/VA, file offset, report section, or line span. Represent unknown values with
an explicit reason; never substitute zero, an empty digest, or a fabricated retrieval timestamp.

Maintain separate observations for declared, embedded, and inferred release identities. Track NK base and effective
modified APKs as distinct artifacts even when a package also carries a loose copy. A repacked ZIP has its own ID
and digest even when its normalized payload is identical. Do not use a patch's proposed output digest as evidence
that such an output exists.

Example content chain, with each arrow requiring recorded member identity and a verified digest:

```text
stock ZIP -> package/MHO900_Update.GEL -> firmware/app/Sparrow.apk
          -> APK member lib/arm64-v8a/libscope-auklet.so
          -> static observation at ELF VA 0x270280
```

The last arrow denotes analysis, not extraction. Preserve the distinction in typed records. Existing extraction
manifests record files and hashes but do not fully specify tool versions and every parent/member derivation;
that lineage must be completed before claiming a reproducible clean-room re-extraction.

Validation should reject duplicate IDs, unresolved parent IDs, path traversal, missing required provenance,
size/hash mismatches, and unsupported schema versions. Resolve only enumerated files; do not recursively follow
guest-root symlinks. Some extracted initramfs symlinks point to absent Android paths, as expected outside a guest.

Public manifests may contain hashes, relative locators, and authored findings. Firmware/APKs/ELFs, factory data,
license material, raw instrument identifiers, guest disks, and unreviewed traces remain local. A later trace
export must classify or redact payloads explicitly and preserve the original locally.

## Public reference pins

Resolved through GitHub's read-only API on 2026-09-24. Pin these revisions before any subsequent source comparison;
the reconnaissance did not build, flash, or install them.

| Repository | Branch inspected | Commit |
| --- | --- | --- |
| `norbertkiszka/Orange-Rigol` | `main` | `2b89f9a662f1a564b712d7f625af5ef578b9ea4d` |
| `norbertkiszka/rigol-orangerigol-linux_4.4.179` | `main` | `d23adbd11626f12abaf4bc742e250204fe2b9f8a` |
| `norbertkiszka/rigol-orangerigol-uboot_2017.09_light` | `main` | `4a73991393f3c17527d5905a1e1c1161cc63ecec` |
| `norbertkiszka/Linux-5.10-Rockchip` | `develop-5.10` | `5f000f33e00ceedefa56dde5ed192dc1c8f77ed0` |

Repository links and the specific reasons to consult each are in [architecture](architecture.md).

## Reproduce this inspection

The following commands read the corpus. They do not run firmware or write extraction results.
Set `ANDROID_SDK_ROOT` locally and make LLVM's `llvm-readelf` and `llvm-objdump` available on `PATH`.
The inspection used Android build-tools 35.0.0.

```sh
root=local/reversing/firmware-extracted/stock-0.26
sdk="${ANDROID_SDK_ROOT:?Set ANDROID_SDK_ROOT to the local Android SDK}/build-tools/35.0.0"
elf="$root/sparrow/base/lib/arm64-v8a/libscope-auklet.so"
"$sdk/aapt" dump badging "$root/firmware/app/Sparrow.apk"
"$sdk/aapt" dump xmltree "$root/firmware/app/Sparrow.apk" AndroidManifest.xml
"$sdk/apksigner" verify --print-certs "$root/firmware/app/Sparrow.apk"
llvm-readelf -d -l "$elf"
llvm-objdump -d --start-address=0x27017c --stop-address=0x2707f4 "$elf"
llvm-objdump -d --start-address=0x37de94 --stop-address=0x37e0b8 "$elf"
unzip -p "$root/firmware/app/Sparrow.apk" lib/arm64-v8a/libscope-auklet.so | shasum -a 256
```

Raw inspection output is local under `out/reconnaissance/`, including `stock-integrity.log`, APK metadata/signature,
and the two native disassembly excerpts. Prior Python/Unicorn tooling is retained as external evidence; no new
Python/JavaScript project tooling was introduced. A future bounded-test port may justify Unicorn bindings as an
explicit ecosystem exception rather than silently abandoning the Kotlin-first policy.
