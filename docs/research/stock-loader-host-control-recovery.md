# Stock loader host-control evidence recovery

No stock-loader guest run had started when a host test setup wrote through symbolic links into earlier evidence.
The setup linked existing witnesses into a synthetic fixture, then used ordinary output redirection on several
linked destination names. This modified one stock-tail result file and four application-domain control PID records.
It was an evidence-preservation error in the test setup, not an observed change in guest behavior.

Testing stopped as soon as the write-through was identified. The changed bytes, unsafe setup, generator, synthetic
index, and link inventory were preserved. The original indexes themselves still matched their committed hashes.
Full checks identified exactly five changed indexed files: the stock-tail `result.toml`, and the earlier denied-read
control's before-root, after-root, final, and summary system_server records. Native events, probe reports, payloads,
and original program artifacts were unaffected.

Separate recovery candidates were reconstructed from the already committed run timestamps, status fields, and PID.
Every candidate matched its original indexed SHA-256 before restoration. The recovery script checked the committed
index hashes, exact candidate digests, and preserved changed bytes before writing those five destinations.
This authenticates the recovered bytes; it is not a new observation or a newly authored replacement result.
The unchanged indexes were never regenerated to accommodate the accidental changes.

After restoration, all 192 stock-tail, 177 denied-read, and 183 readable-file control entries passed their original
indexes. Both affected runs' frozen verifiers accepted their original conclusions. Independent review also checked
six linked control/review indexes: all passed. The four PID records had shared hardlinks in those earlier controls;
restoring their original inode bytes restored those aliases as well. The readable-file run was unaffected.

The unsafe synthetic fixture remains quarantined. Its attempted positive result is not accepted as verification
of the new stock-loader candidate. Replacement controls must use independent regular files for writable witnesses,
reject linked destinations before mutation, keep verifier outputs outside the index, and revalidate source indexes
afterward. The stock-loader task remains open until those controls pass and the separately frozen guest candidate
is executed and evaluated.

See [the recovery manifest](../../experiments/calibration-loaders/host-control-recovery.toml) for preserved evidence
and the independent audit. This checkpoint introduces no new guest experiment or physical-instrument claim.
