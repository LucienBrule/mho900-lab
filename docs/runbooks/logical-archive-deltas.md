# Logical archive inventories and deltas

The evidence library can inspect a pinned, uncompressed logical tar archive without
extracting its contents. It returns sorted regular-file path/size/SHA-256 records,
a separate directory list, the source digest and byte extent. File payloads are
hashed in memory and never written to the filesystem or printed by the CLI.

```sh
uv run --locked mho-lab archive inspect out/before.tar \
  --expected-sha256 "$BEFORE_ARCHIVE_SHA256"

uv run --locked mho-lab archive diff \
  --before out/before.tar --before-sha256 "$BEFORE_ARCHIVE_SHA256" \
  --after out/after.tar --after-sha256 "$AFTER_ARCHIVE_SHA256"
```

Use digests from preserved acquisition evidence. Calculating a digest from an
untrusted current pathname does not independently authenticate that pathname.
Both commands emit TOML. A rejected input exits one with a structural diagnostic;
CLI usage errors exit two. Diffs identify which input failed. Reports contain
relative archive member names and content hashes, not payloads or host paths.

## Supported archive profile

This is a narrow profile sufficient for the retained logical data acquisitions:

- Explicit USTAR or GNU-USTAR headers with validated unsigned header checksums,
  octal numeric fields and UTF-8 string fields.
- Regular files and zero-length directory entries. A directory's single final
  slash is the format delimiter; all remaining names must be canonical relative
  paths. USTAR prefix fields are supported.
- Complete 512-byte blocks, bounded declared extents, zero member padding, at least
  two consecutive zero end blocks, and only complete zero blocks afterward.
- No duplicate logical names or file/directory ancestry conflicts.

Compressed input, base-256 numeric fields, symbolic/hard links, sparse members,
PAX records, GNU long-name records, GNU extension fields and other member types
are rejected. Rejection means outside this profile; it is not a claim that another
archive implementation must reject the file. The original archive remains the
authority for metadata outside this inventory.

Defaults bound the source to 64 MiB, the member count to 10,000, each member and
aggregate payload to 64 MiB, and path depth to 32. `ArchiveLimits` exposes validated
library overrides. Reads reject observable source changes and symlinks. Byte limits
do not guarantee completion within a wall-clock deadline on a blocking filesystem.
No automatic fallback to a broader parser occurs.

## Typed content comparison

`inspect_archive(ArchiveRequest(...))` returns `ArchiveAccepted` or
`ArchiveRejected`. `compare_inventory(InventoryDiffRequest(...))` compares any two
canonical sorted regular-file inventories. Its `InventoryDelta` contains named
`FileAdded`, `FileRemoved` and `FileModified` alternatives, deterministic path order,
and unchanged/before/after counts. Malformed or unsorted input is `DeltaRejected`.

At the same path, equal size and digest count as unchanged. Different size or digest
counts as modified. Equal content at different paths remains removal plus addition;
the tool does not infer a rename. It does not normalize path case or Unicode.
Directory changes, mode/ownership, timestamps, extended attributes, sparse layout
and link relationships are outside this content delta.

A file-content delta does not establish an option transition, semantic equivalence,
reboot persistence, RF behavior or a tested restoration procedure. Those conclusions
require their own experiment-specific evidence. The existing ordinary-option
verifiers remain unchanged; this library extracts a reusable operation they share.
