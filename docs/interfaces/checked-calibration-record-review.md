# Checked-record reuse decision and bench handoff

The recovered stock `.26` envelope is mature enough for an independent read-only
parser. The [specification](checked-calibration-record.md), typed Kotlin CLI and
public vectors were committed in `fa29f9b`; the recovery task closed in `779b612`.
This decision does not establish the correctness of enclosed calibration values.

## Review result

The implementation matches the recovered load success predicate within its
documented input bounds: little-endian length fields, header-body length 20,
independent header and payload CRCs, exact caller-selected payload length, and
permitted trailing data. It preserves opaque metadata without assigning version
compatibility or date validity. The stock source remains the pinned library and
ranges linked by the specification.

The independent read-only review found no acceptance bug. Its concrete review
suggestions were incorporated before closure: raw metadata naming, reference
library identity in reports, complete-file versus bounded-prefix hash wording,
CRC-covered rather than semantically verified metadata, and four compound
malformed controls establishing the documented rejection precedence. The final
suite passed 24 cases. Its bit-at-a-time CRC generator is separate from the
inspector's Java CRC32 implementation and checks the standard `123456789` value.

Both available stock positive records, LSB and vertical, pass with the previously
recorded lengths, CRCs and complete-file hashes. These are file-format witnesses;
this batch did not execute the stock loader. The final review also rechecked all
nine evidence hashes, four preserved-original hashes, twenty public vector hashes,
twenty-four recorded control outcomes and the control report's inspector identity.

The independent interface intentionally has its own policies:

| Concern | Independent inspector | Recovered stock behavior |
|---|---|---|
| Input | Stable regular file; no symlink; 16 MiB cap | RFile-based open/read; no such cap recovered here |
| Expected length | Explicit positive argument within the cap | Positive caller-selected length; assertion on zero |
| Validation order | Full header available, then explicit field/checksum checks | Early total-file-size test against N, then component reads |
| Failure result | Named typed rejection; no published payload metadata | Numeric status; destination may already be partly or fully overwritten |
| Trailing bytes | Accepted and separately hashed | Accepted without end-of-file check |
| Persistence | None | Save can change process umask, leave trailing bytes and ignore durability outcomes |

This is a parser contract, not a drop-in emulation of all RFile/CCheckedStream
side effects. Failure categories must not be interpreted as stock return codes.
No claim is made about another firmware version without comparison. File stability
remains an input assumption; the inspector does not create a filesystem snapshot.

## Reusable implementation boundary

Keep the envelope parser separate from instrument operations. It needs bytes and
a trusted expected payload length, not kernel privileges, an MMIO mapping or a
running Sparrow process. These responsibilities are ready to reuse:

| Surface | Ready to carry forward | Deliberately unresolved |
|---|---|---|
| Small kernel/device layer | No involvement in envelope parsing | Device ownership, DMA lifetime and acquisition completion contracts |
| Userspace daemon | Own original file provenance, snapshot bytes, parse and expose a read-only result | Which per-unit record is applicable; when instrument state may be changed |
| C ABI / CDEF | Explicit byte buffer and length, expected payload length, typed status, raw metadata and validated payload/trailing extents | Exported names, ABI versioning and representation layout are not frozen here |
| Kotlin/Native | A sealed valid/rejected result; separate byte-consistency and calibration-applicability types | Payload meaning, units, model-specific calibration transforms |
| scopehal/ngscopeclient | Provenance/status can be surfaced by a future backend | Waveform scaling, sample format, trigger position, timing and credible acquisition |

For a future C parser, prefer a caller-owned immutable buffer and explicit length
over a filename-taking ABI. Decode little-endian fields rather than casting a
packed header. On success, return offsets/lengths into that same buffer, raw
metadata and a status; on failure, publish no successful view. Document that any
view expires with its backing buffer. Hashing, file access and device provenance
belong in the daemon/caller, outside the minimal byte parser. A separate CDEF
surface can bind that contract after its ABI version and layout are chosen.

The present implementation is Kotlin/JVM, using Java I/O, hashing and CRC APIs.
It is a reference and conformance runner, not an already-portable Kotlin/Native
library. Kotlin/Native should reuse the byte contract and public vectors while
implementing its own platform primitives. Its semantic model should preserve a
distinction such as `EnvelopeValid` versus `CalibrationApplicable`; parsing can
produce only the first. Do not expose a valid CRC as an instrument-ready flag.

## Handoff for copied bench records

The [existing exact AFE bench question](../research/afe-calibration-decision.md)
remains unchanged. Physical collection is being prepared separately and was not
performed or authorized by this host-only task.

Once separately collected copies are supplied:

1. Preserve all four primary/default zero/bandwidth paths independently, including
   absence observations. Bind each copy to its original device path, firmware,
   collection time, whether Sparrow had already run, file and directory metadata,
   relevant mount state and original hash. A post-startup bandwidth record may
   already reflect the stock unconditional patch/save.
2. Keep originals intact. Run the inspector on stable local regular-file copies,
   using expected payload 560 for AFE zero and 320 for AFE bandwidth only after
   confirming the firmware matches this profile. Retain each TOML report alongside
   its provenance and verify the copy hash remains unchanged. Use configurable
   local paths; do not place host paths or unit identifiers in public source.
3. Treat rejection as evidence. Preserve bad CRCs, truncation, trailing bytes and
   missing files; do not repair, normalize or replace them with synthetic values.
4. Compare primary and default records byte-for-byte locally, retaining exact
   differences and lifecycle context. The parser makes no claim about the analog
   meaning of a difference. Proprietary record payloads are not public vectors.
5. Use observed file state to choose the next bounded AFE hypothesis. A valid
   record supports a concrete loader fixture; absence or invalidity leaves entry
   object bytes and the actual save outcome as explicit observation questions.

Further leaf-by-leaf envelope work has low information value now. The next useful
evidence is the actual per-unit file state and its startup provenance. There is
no new guest run, device response, physical task or calibration writer in this
batch, and no successor task is admitted by this decision.
