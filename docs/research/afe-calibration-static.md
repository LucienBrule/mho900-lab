# Post-ADC AFE loading includes unconditional persistence

The stock `.26` AFE loader pair is principally a filesystem and software-state
contract. The recovered normal path adds no mapped-register transaction. Its
most consequential behavior is that bandwidth loading always patches twelve
words and attempts to save the primary record, even when both load attempts fail.
This batch performed static analysis and host verification only. Neither AFE
loader was executed in a new guest, and no physical instrument was accessed.

## Scope and provenance

The input is the byte-identical stock library with SHA-256
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
`RecoverAfeCalibration.main.kts` derives an inventory of 27 ranges and 158 call
edges, along with file strings, decoded store offsets and selected operands.
`VerifyAfeStatic.main.kts` independently reconstructs those instruction ranges
from LLVM disassembly and checks hashes, branch destinations, critical operands
and layout arithmetic. The semantic interpretation was also independently
reviewed against the stock instructions.

The tracked TOML contract distinguishes deterministic software operations from
runtime file/time outcomes and explicit unknowns. It is not a whole-program
proof: standard-library internals, allocation/exception paths and concurrent
writers remain bounded external questions. The inventory preserves unexpanded
edges rather than labeling them as resolved. Clock calibration is excluded.

## Loader and save behavior

- AFE zero, `0x350614`, loads 560 bytes into AFE object `+0x29e8`. It tries the
  default path only if the primary result is signed-negative, then returns the
  selected load status.
- AFE bandwidth, `0x350e44`, loads 320 bytes into AFE object `+0x2728` using the
  same fallback rule. It then writes twelve 32-bit values of 115 and always calls
  the save helper.
- The save helper, `0x350fbc`, saves 320 bytes from global calibration object
  `+0x244f60` to the primary bandwidth path. It maps negative save status to `-9`,
  otherwise zero.
- The dispatcher calls zero at `0x333bcc` and bandwidth at `0x333bd8`. It does not
  branch on either returned status.

The bandwidth loader ignores the save result and returns its earlier load status.
Thus a negative load result can coexist with a successful write of a modified
record; conversely, a successful load result does not establish persistence.
The twelve offsets are decoded in `constants.toml`; they are software object
stores, not MMIO writes. This routine does not loop over the twelve stores.

The save helper obtains its source independently through `Drv_GetScope()` and
`GetCalibration()`. Those getters yield image-relative global `0x10c4f18`; its
save source is `0x1309e78`. The dispatcher's AFE offset `0x242838` plus bandwidth
offset `0x2728` equals `0x244f60`. A future observation must still bind the actual
loader object to that global source rather than assume pointer identity.

## Checked stream and file side effects

Open failure returns `-1` without changing the load destination. Structural or
short-read failure returns `-2`; integrity failure returns `-3`. A short payload
read can alter a destination prefix, and a failed payload CRC can leave all
requested bytes changed. Failed loads therefore do not generally imply an
unchanged record. That implication is valid for the two-open-failure case only.

Saving builds a 28-byte checked header and requests writes of 4, 4, 20 and 320
bytes. Metadata includes version zero and runtime local time encoded through
`getNowTime`; those bytes are not deterministic hardware responses. The save
path computes payload/header CRCs before attempting the file open.

`RFile::open(2)` calls `umask(0)` without restoring the earlier process mask, then
requests `open` flags `0x42` (`O_RDWR|O_CREAT`) and mode `0666`. It does not request
truncation. This is recovered stock behavior, not a change made by this research.
It affects the process even if the file open fails. A successful save overwrites
from offset zero; a longer pre-existing file can retain trailing bytes. Partial
writes can leave a partially updated file, and no atomic replacement is present
in this path.

`RFile::write` delegates to `__write_chk`. `RFile::flush` is a no-op returning one.
The checked save calls `fsync` and close but ignores their results. Returning the
payload length establishes that the four write counts matched, not durability.

## Corpus, guest and physical state are different evidence

The four primary/default AFE paths are absent from the provided extracted `.26`
firmware corpus. `InspectAfeAssets.main.kts` records that bounded inventory; it
makes no claim about a real unit's data partition.

The previous guest constructed a fresh empty tmpfs containing only LSB and
vertical default files. Its captured directories are root-owned `0755`, and
Sparrow ran as UID 1000. Absence of AFE files is derived from that construction;
there is no prior AFE-specific absence probe. File creation would ordinarily be
denied by those directory permissions, subject to actual credentials/capabilities
and policy. No AFE save failure has yet been observed.

For this guest, the narrow prediction is conditional: both opens fail, zero data
remains equal to its entry capture, bandwidth changes only the twelve specified
words, and a primary save is attempted. The remaining record bytes cannot be
assumed zero. They must be captured. Neither this prediction nor the extracted
corpus establishes the factory instrument's intended calibration record.

## Useful future observation and current stop

The smallest complete observation spans the pair: entry at unexecuted `0x333bac`
and exit at unexecuted `0x333bdc`, before the dispatcher stores the bandwidth
result and before clock loading. Useful witnesses are both entry/exit payloads,
the global save-source pointer and bytes, load/save outcomes, four file paths,
file metadata, process umask and thread coverage. No new MMIO response is needed
for the recovered normal path.

Physical evidence would now materially distinguish a unit-specific calibration
load from a missing-file path that fabricates and attempts to persist a partially
initialized record. Under the current operator instruction, continuation stops
at that uncertainty. The decision records the exact bench question; this batch
does not choose synthetic calibration values or authorize a physical probe.

## Verification and reproduction

The independent checker accepted the contract and rejected four altered copies:
changed patch value, changed open flags, moved exit checkpoint and changed range
hash. A development fixture initially changed the wrong hash field; that failed
control batch remains preserved, and the corrected fresh batch passed. This
checks evidence interpretation, not live AFE behavior. All 378 artifacts from the
successful stock ADC run were rehashed, and stock APK/library hashes are unchanged.

Use configurable local inputs and fresh output directories:

```sh
kotlin tools/research/RecoverAfeCalibration.main.kts \
  "$STOCK_ELF" "$NEW_DERIVATION_DIRECTORY"
kotlin tools/research/VerifyAfeStatic.main.kts \
  "$STOCK_ELF" experiments/afe-calibration-static \
  "$LLVM_OBJDUMP" "$NEW_VERIFICATION_DIRECTORY"
kotlin tools/research/InspectAfeAssets.main.kts \
  "$EXTRACTED_STOCK_ROOT" "$NEW_ASSET_INVENTORY"
```

`experiments/afe-calibration-static/results.toml` pins the durable contract and
local control evidence. Derived disassembly stays in local output directories;
proprietary calibration payloads are not added to source.
