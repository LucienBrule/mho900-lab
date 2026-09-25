# Durable finalization for early guest collection failures

The outer runner now records each boot collection command's status and phase.
A failed mandatory `getprop` or `uname` command stops admission immediately.
Its EXIT path still attempts final guest health collection, final log capture,
teardown, result writing, and evidence indexing. No command is retried. Optional
graphics and platform-signature collection remain optional, with their statuses
preserved. Teardown command statuses are recorded separately.

`admission-runtime.sh` contains the actual collection and finalization functions.
Seven host-only controls source those functions and replace the guest transport,
health helper, and cleanup with deterministic fixtures. They cover success,
property output followed by exit 255, a later kernel-query failure, failed final
health collection, optional collection failures, an early runtime abort, and an
index hash failure. The last case preserves the incomplete first index and
checks that the corrected result agrees with the failing process exit.
They verify the original exit status and phase, admission suppression after
mandatory failure, health attempt rules, cleanup exactly once, and every
indexed digest. They do not prove emulator or stock application behavior.

The repeat keeps the original prediction manifest as
`source/calibration-stock-inputs.toml`, consumed by the unchanged frozen loader
verifier. Its original task and run identifiers describe that prediction's
lineage. The separately copied `source/calibration-stock-runtime-inputs.toml`
records the actual repeat task, run identifier, and current harness hashes.
The runner validates that manifest and its run identity before starting a
guest. The repeat manifest pins the original prediction manifest as an input.
The actual result must name `stock-calibration-loaders-02`; the independent
audit must check the runtime manifest as well as the frozen behavior verifier.

Stock code, native observer, register values, loader expectations, and terminal
checkpoint are unchanged. A positive host control is permission to test the
same guest candidate once, not evidence that its prediction has passed.

Receipt metadata correction: the two actor receipts committed in `b11a03c` and
`a28cc85` contain manually entered `recorded_at` values later than their actual
commit times. Those fields are not valid experiment timestamps. The commits
were recorded at 13:08:58 UTC and 13:10:18 UTC respectively; raw run logs remain
the timing evidence. The immutable receipts are preserved as written.
