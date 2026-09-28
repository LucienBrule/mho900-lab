# Checked calibration record, stock .26 profile

Status: a recovered byte-format specification with host conformance tests.
It describes the envelope used by stock `CCheckedStream`, not the meaning or
correctness of the enclosed calibration values. It is suitable for independent
read-only parsers. It does not authorize writing calibration records to an
instrument or define a complete Gorilla instrument API.

The reference library SHA-256 is
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
Pinned load/save ranges and supporting call edges are in
[the AFE inventory](../../experiments/afe-calibration-static/inventory.toml).
The earlier [checked-stream recovery](../../experiments/calibration-static/checked-stream.toml)
and [AFE behavior](../research/afe-calibration-static.md) provide interpretation.

## Byte layout

All integer fields are unsigned little-endian values. Decode bytes explicitly;
do not overlay a native C structure whose padding or alignment may differ.
There is no magic number or record-type tag in this envelope.

| Offset | Bytes | Field |
|---|---:|---|
| 0 | 4 | CRC32 of bytes 8 through 27 inclusive |
| 4 | 4 | Header-body length, exactly 20 for this profile |
| 8 | 4 | Raw metadata word (save-side version field) |
| 12 | 8 | Time metadata bytes; retain their exact representation |
| 20 | 4 | Declared payload length, N |
| 24 | 4 | CRC32 of payload bytes at offset 28, length N |
| 28 | N | Payload |
| 28+N | remainder | Trailing bytes, outside both checksum regions |

CRC32 uses the reflected IEEE polynomial `0xedb88320`, initial state
`0xffffffff`, and final XOR `0xffffffff`. The standard check value for ASCII
`123456789` is `0xcbf43926`. The header CRC excludes its own word and the
header-body-length word. The payload CRC includes only the declared payload.

A caller must supply the expected payload length from a separate, trusted
contract. The filename and valid CRCs do not identify the correct instrument,
channel, calibration family or firmware. No unit-specific AFE values are defined
by this specification.

## Envelope validation

A conforming read-only parser for this profile validates, in this order:

1. At least 28 bytes are available.
2. Header-body length is 20.
3. The 20-byte header-body CRC matches.
4. Declared payload length equals the caller's expected length.
5. All declared payload bytes are available, using overflow-safe bounds checks.
6. The payload CRC matches.

Trailing bytes do not invalidate this profile. Preserve the original file and
report trailing length/hash separately; a valid prefix is not permission to
truncate or normalize a record. The recovered stock load reads its requested
payload without requiring end-of-file. The stock save path does not truncate an
existing file, so a successful save can leave old trailing bytes.

Version/time metadata is preserved, not interpreted as a compatibility or expiry
check. The recovered save constructs version and local-time-derived metadata;
the AFE save uses a fresh checked-stream object whose version is zero. The loader
copies the metadata but does not establish its semantic validity. An inspector
must not invent a date encoding rule or reject unfamiliar metadata solely from
that interpretation.

## Stock behavior versus independent parsing

Stock load returns the requested byte count on success, `-1` on open failure,
`-2` for structural/short-read failure, and `-3` for integrity failure or a
mismatched declared payload length. A short payload may alter a destination
prefix before failure; a bad payload CRC can leave all payload bytes copied.
A separate parser should validate before publishing a successful result. Its
result model need not reproduce those partial destination writes.

This validation order is the independent parser's contract, not a promise to
reproduce every stock diagnostic. Stock first tests total file size against N
(not `28+N`) and then performs its component reads. A malformed file can therefore
fail at a different check in stock. The success predicate for this profile is
equivalent within the inspector's resource/input bounds; failure reasons are
inspector categories, not stock return codes.

Stock save writes four components: 4-byte header CRC, 4-byte body length,
20-byte header body, then payload. Mode 2 changes process umask to zero, opens
with `O_RDWR|O_CREAT` and mode `0666`, and does not truncate. Short writes fail;
there is no retry loop in the recovered wrapper. `flush` is a no-op, and `fsync`
and close outcomes do not control the reported success. These are compatibility
observations, not recommended independent storage policy.

Envelope validity establishes byte consistency only. It does not establish
calibration accuracy, record provenance, physical applicability, or whether stock
Sparrow would reach this loader with the same filesystem and runtime state.

## Read-only inspector

```sh
kotlin tools/calibration/InspectCheckedRecord.main.kts "$RECORD_FILE" "$EXPECTED_PAYLOAD_BYTES"
```

The inspector reads one regular, non-symlink file, writes TOML to stdout, and
returns 0 for a valid envelope or 2 for rejection. It never writes the input.
It reports full-file, payload and trailing hashes and CRC-covered raw metadata; it emits
neither payload bytes nor the input pathname. Metadata appears only after all
checks pass. Reports identify the reference library SHA-256. Rejections include
a stable reason and, when the complete file fit the input cap, its byte count
and hash. Oversize input produces no file hash: a bounded prefix must not be
presented as the complete file.

The 16 MiB input cap and positive expected-length requirement are inspector
resource policies, not discovered instrument limits. Files must be stable during
inspection; a report describes the bytes read, not an atomic filesystem snapshot.
Special files and symlinks are rejected. Resource-limit, path and I/O failures
are distinct from malformed record bytes.

Known caller sizes include LSB 192, vertical 1794240, ADC 1936, AFE zero 560 and
AFE bandwidth 320 bytes. Only the existing LSB and vertical records are available
as stock positive fixtures in this repository's local corpus. Public conformance
vectors contain synthetic payloads and convey no factory calibration values.

## Reproducing conformance

From the repository root, with Kotlin 2.3.21 and JDK 23 (the recorded environment):

```sh
kotlin tools/calibration/test-checked-record.main.kts "$NEW_OUTPUT_DIRECTORY"
cmp experiments/calibration-record-spec/vectors.toml "$NEW_OUTPUT_DIRECTORY/vectors.toml"
```

Use a fresh output directory. The suite generates the public vectors using a
separate bit-at-a-time CRC implementation, invokes the actual inspector, and
checks 24 outcomes including compound malformed precedence and unchanged input
hashes. [Public vectors](../../experiments/calibration-record-spec/vectors.toml)
are reusable by other parsers. The
[result manifest](../../experiments/calibration-record-spec/results.toml) pins
the implementation, controls, source evidence and stock-file reports. Host
conformance does not constitute a new dynamic stock-loader validation.
