# Application-domain calibration file access

`calibration-file-access-01` confirms the predicted file-access failure. The private probe ran naturally as UID 1000 in
`u:r:system_app:s0`, with no package-admission exception or guest policy change.
It inspected all three fixture directories successfully.
For both stock default files, metadata and read-only open returned `EACCES` (errno 13).

No file descriptor was obtained, so the probe did not call `Os.read` or `Os.close` for either file. Four kernel audit
records correlate the probe PID 2445 with denied `getattr` and `read` permissions on the measured `su_tmpfs` file type.
The latter check occurred during open. The aggregate verifier's `file_N_read = "denied"` describes overall readability;
the raw report's `read_attempted = false` is the precise operation history.

The frozen verifier accepts this complete negative observation. Its host controls accepted both synthetic complete
readability and complete denial, and rejected the wrong report UID. Independent altered-evidence review is pinned in
the result manifest. The original 177-entry index, report, package state, process identity, labels,
and audit logs remain unchanged.
The outer run's generic `install` and `launch` fields retain their stock-admission defaults; the separate
private-control install/launch records and process report prove that the private application executed.

The unique probe package was stopped and uninstalled. All 20 access-helper statuses and all five final-health statuses
were zero. The three system_server samples retained PID 1052; enforcement remained enabled. Final copies of both files
still match the stock hashes and their labels are unchanged. No stock application ran. The original emulator ramdisk,
stock APK, and stock native library remain byte-identical, and the dedicated listeners are absent after teardown.

The public test certificate used for this disposable guest is byte-identical to its framework certificate. It comes
from AOSP `platform/build`, commit `8ed39f49ba645b55f400e736dc3415a9aedec1e8`, under
`target/product/security/platform.{x509.pem,pk8}`. The private probe is a new research artifact; it is not a modified
Sparrow package or an instrument identity. Its two independent builds produced the same APK bytes.

This closes a specific environment question before another stock initialization run. Directory traversal is usable;
the current file labels are not. The next decision should select a narrowly scoped label fixture supported by existing
policy, preserve both file contents, and validate access with the same private probe before proceeding to stock loaders.
No permission has been inferred for another file type, and this result says nothing about FPGA behavior.

See [the input manifest](../../experiments/calibration-access/inputs.toml) and
[the result manifest](../../experiments/calibration-access/run01-results.toml) for exact pins and limitations.
