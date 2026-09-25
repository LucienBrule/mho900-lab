# Lossless preservation of finalized guest backings

`ArchiveGuestBacking.main.kts` preserves an exact generated raw backing in a
compressed archive without modifying its dependent qcow2 overlay. It accepts
project-relative paths under ignored `out/`, rejects symlink paths and shared
hardlinks, and checks source/overlay hashes and open-file users.

Preparation creates a deterministic gzip stream, restores it to a fresh regular
file, and verifies size, SHA-256 and original POSIX mode. It writes a restoration
manifest before deleting its own temporary round-trip file. The original raw is
still present at this point. Preparation does not retire it.

Retirement verifies the archive again, repeats restoration into another fresh
file, and checks source identity, overlay identity and open users immediately
before removing the exact redundant raw. The archive and restored copy remain
available at that point. Separate transaction records document the removal and
completion before/after the temporary restored copy is discarded. An interruption
leaves the archive and phase records for explicit inspection; the tool refuses to
restart an already attempted retirement blindly.

The open-file checks are observations immediately before the action, not a claim
of a filesystem-wide exclusion lock. Run this only on finalized images with no
concurrent guest launch or other image writer.

Restore the raw to its recorded original path before opening the dependent
overlay. Restoration rejects an existing destination, changed archive or changed
overlay and verifies the restored file. A fresh alternate destination can also be
used for an independent round-trip check; that does not make the original overlay
usable until its backing exists at the original location.

```sh
kotlinc -script tools/research/ArchiveGuestBacking.main.kts -- \
  prepare RAW OVERLAY RAW_SHA256 OVERLAY_SHA256 NEW_ARCHIVE_DIRECTORY
kotlinc -script tools/research/ArchiveGuestBacking.main.kts -- \
  retire NEW_ARCHIVE_DIRECTORY/prepared.toml
kotlinc -script tools/research/ArchiveGuestBacking.main.kts -- \
  restore NEW_ARCHIVE_DIRECTORY/prepared.toml ORIGINAL_RAW_PATH
```

The initial host control exposed a restoration bug: passing an intentionally
absent raw path to `lsof` produced an indeterminate check. That failure is retained
under `out/adc-sequence-capacity/controls01`. The corrected implementation checks
existing image paths and requires the dependent overlay. No research backing was
processed by the failing version.

The subsequent independent small-fixture controls cover preparation, retirement,
restoration, a changed source before preparation, a changed source after
preparation, a corrupt archive and an active image user. They do not overwrite
or link existing research evidence. The unchanged guest preboot requirement is
2097152 KiB; actual free-space changes must be measured independently of reported
allocated blocks on a COW filesystem.
