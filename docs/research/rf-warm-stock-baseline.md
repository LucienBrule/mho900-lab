# Verified warm stock baseline for the RF comparison

The read-only continuation completed with the original APK-backed native library
and repeated cached policy values 17/17. The process and boot remained unchanged
through warmup, observation and the final check. Exactly four fixed reads were
performed, totaling 16 bytes; the temporary reader exited successfully and was
reaped. This run introduced no native-file change, reboot or root-daemon restart.

The requested serviced warmup was 1,801 seconds. The completion event records
1,800.964761 seconds, which satisfies the frozen requirement of more than 1,800
seconds. The fresh normal-UI screenshot was accepted against the same process
epoch before the observation. The display retained the ordinary settings restored
by the preceding boot; [separately reviewed normalization](rf-remaining-arm-preparation.md)
will establish the fixed capture preconditions without changing the RF protocol.

The initial and final logical data archives are byte-identical. Original option
statuses, identity data and licenses remain preserved; the bandwidth option
reports zero and the ten previously enabled ordinary options report one. The
320-byte calibration coefficient payload remains byte-identical to the protected
baseline. No calibration action was requested.

The completed capture contains 153,080 stored frames. Independent review checks
isolated traffic, two read-only SCPI option-query flows, the terminal recorder
statistics and graceful exit. The recorder reports zero kernel drops. Temporary
host addressing was removed, isolation was restored, and persistent networking
configuration matches the sealed predecessor's restored state. This run inherits
that baseline; it does not contain a new local baseline audit.

Two review-code assumptions were corrected without changing the experiment or
its evidence. The first verifier used a stricter 1,801-second acceptance threshold
than the frozen contract. A separate version applied the actual greater-than-1,800
criterion. Its first actual review then rejected a nonexistent local baseline
path. That rejection is preserved. The final version checks the actual inherited,
sealed baseline. Original verifier sources and preparation remain immutable.

The raw run is native-sealed at
`out/rf/policy-stock-continuation-20261002T024500Z.toml`, SHA-256
`b040ec36ac8378e833bac9231dd62b050e8c38d641fec6a048fdea3bcab73bac`,
covering 257 artifacts and 300,892,191 bytes.
The final independent review is native-sealed at
`out/rf/stock-continuation-independent-final-20261002T032000Z.toml`, SHA-256
`5cca3da59fd36f8b0e4c78afd85d7f42a7c27bb198004a9cb4d9b6bff8aba128`.
The rejected review is separately sealed with SHA-256
`46d4ad0dc915a526f4850d5b1231608bc337f094b850d2aada9acd6d653eaabf`.

This result completes the stock readiness evidence linked to the
[preserved single rollback](rf-stock-timestamp-check.md). It does not retrospectively
turn the earlier partial transition or host/layout failures into successful runs.
The stock and execution decisions can now evaluate the already frozen
stock–derived–stock comparison. Actual RF response, comparative gain and
calibrated analog bandwidth remain unestablished by this baseline.
