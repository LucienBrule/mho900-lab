# Guest evidence capacity review

The workspace fell below the unchanged 2 GiB preboot gate after the stock capture.
A read-only inventory found 180 generated disk files across guest runs, including
60 raw userdata backings. Their reported block allocation is substantial, but
those counts do not establish uniquely reclaimable space on a COW filesystem.
No evidence or reference file was changed or removed during this review.

Two finalized raw backings are suitable candidates for a separately admitted
lossless archive experiment:

| Run | Raw bytes | Reported allocated bytes | Streamed gzip size |
| --- | ---: | ---: | ---: |
| `stock-calibration-loaders-02` | 838860800 | 580386816 | 9452830 |
| `calibration-file-access-01` | 838860800 | 580386816 | 9452833 |

Compression was streamed to a byte counter and discarded; no archive was created.
The files have different SHA-256 hashes and must be preserved separately. They
are not interchangeable copies of the original Android userdata input. The
emulator expanded and changed their backing state during their respective runs.

Both files have one link and no open process was observed during review. Their
raw bytes and dependent qcow2 overlays are pinned in the review manifest. The
native `qemu-img info --backing-chain` output identifies a qcow2 overlay over each
raw file. The raw backings are outside the respective evidence indexes, but they
remain useful runtime evidence and must not simply be discarded.

## Recommended restoration contract

A successor may create a separate gzip archive for each exact raw image, verify
the archive, decompress into a fresh independent file, and verify restored size
and SHA-256 before considering removal of the uncompressed original. It must
retain a project-relative restoration manifest, archive hash, original hash,
file mode, dependent overlay hash, and required original restoration location.
The overlay and every indexed artifact remain unchanged. Restore the raw backing
to its original location before opening the dependent overlay.

Archive creation, restore testing, and any replacement/removal require a new
admitted task. That task must reject changed inputs or active image users, leave
failed transactions recoverable, and record actual free-space recovery. Reported
blocks suggest about 1.06 GiB could be recovered from these two candidates after
compression, but shared blocks may reduce the actual result. The 2 GiB guest gate
must be checked again after any operation. No archival action is admitted by
this review alone.
