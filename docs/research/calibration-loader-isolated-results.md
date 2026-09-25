# Whole-loader observation controls

Run `group-calibration-loaders-03` validates the private whole-loader observer: all fourteen arms 76..89 reached their
specified positive or negative outcomes. The native build11 bytes are unchanged from run02, whose 76 legacy runtime and
30 malformed-input controls remain the inherited baseline. No stock application or calibration filesystem fixture ran.

The positive cases captured complete entry and terminal buffers, preserved post-atomic checkpoints, interpreted signed
32-bit return values, and revisited a removed breakpoint without stopping there. Negative cases rejected an incorrect
PC, instruction, worker thread, binding, pointer, length, short read, corrupted buffer, unexpected mapped access, clone,
and missing checkpoint. The fourteen arms produced 37 raw files totaling 9,005,056 bytes. All 43 private threads were reaped.
The inherited 466-store prefix ran in each arm; the loader phase supplied no additional mapped response.

The frozen per-arm verifiers accepted 14/14. The frozen aggregate then failed because the evidence collector omitted
`reference.tsv` from its extension list. Independent review found this was the sole missing required index member;
all 307 indexed files were present, unique, and hash-valid. The table itself matches the canonical SHA-256 already pinned
before execution. The original run, index, failed aggregate output, and failed first verifier-control report remain intact.

An offline correction binds the table directly to that canonical hash and retains all other index and semantic checks.
It accepts the unchanged run. A fresh nine-case verifier test accepts the original and rejects eight altered copies,
including a changed table header, failed final health, wrong status, missing debug state, changed checkpoint register,
missing cleanup, changed prefix write, and corrupted vertical data. Each altered copy has a regenerated index, so a
semantic failure cannot be attributed merely to an outdated file hash. Future capture indexes now include TSV files.
No guest rerun or native change was needed for this bookkeeping correction.

All 17 recorded system_server samples, including the final sample, retained PID 1059. Final enforcement, process, package,
and command-status checks passed; the dedicated listeners were absent after teardown. The stock APK and native library
hashes remain unchanged. These are private observation controls, not evidence that stock calibration loading succeeds or
that the synthetic register values describe a physical instrument.

The next independent question is filesystem construction. Static mount-tool inspection shows that adding explicit
`rootfs` operands would repeat the already failed remount transition. A separately pinned disposable ramdisk containing
an empty `/rigol` mountpoint, followed by one bounded tmpfs mount, is the candidate to evaluate before stock execution.
See [the independent decision](calibration-loader-independent-decision.md) and
[the result manifest](../../experiments/calibration-loaders/run03-results.toml) for tasking and evidence pins.
