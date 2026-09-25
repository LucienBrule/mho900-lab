# Calibration fixture file label result

`calibration-file-label-01` establishes complete application-domain reads of both stock calibration defaults.
The same private probe APK ran as UID 1000 in `u:r:system_app:s0`. All three directory metadata calls and both
file metadata, read-only open, bounded read, and close operations succeeded. The complete 220-byte LSB and
1,794,268-byte vertical files match their stock SHA-256 values.

The only fixture change was assigning the existing `system_app_data_file:s0` type to the two explicit files.
The three directory labels stayed `tmpfs`; owners, modes, sizes, bytes, and the four absent paths were preserved.
The guest policy, derived ramdisk, stock files, and probe APK were unchanged from the preceding denied-read control.
This confirms the required operations in this disposable guest. It does not decode every compiled policy rule or
establish file behavior on the physical instrument.

The frozen aggregate verifier accepts the observation. Its host controls retain acceptance of the original denial,
accept complete readability, and reject the wrong type or UID. Independent review and altered-evidence checks are
pinned in the result manifest. All 183 indexed artifacts match their hashes.

All 26 helper statuses and five final-health statuses were zero. Three system_server samples retained PID 1093;
enforcement remained enabled. The private package was stopped and removed. Final file copies match the stock bytes,
the selected labels remain confined to the two files, and all four deliberately missing paths remain absent.
The original emulator ramdisk, stock APK, and stock native library remain unchanged. Dedicated listeners are absent
after teardown. The mounted fixture was discarded with the disposable guest; no unmount-restoration claim is made.

Sparrow was not executed in this control. The outer generic install/launch fields describe the unused stock-admission
path; separate private-probe records prove this execution. The supported continuation is one stock run covering all
three statically recovered loaders, capturing whole payloads and stopping before `SetADCParameter(0)`. That experiment
will test stock loader behavior and inherited initialization together, without adding further synthetic register values.

See [the frozen inputs](../../experiments/calibration-access/label-inputs.toml) and
[the result manifest](../../experiments/calibration-access/label-run01-results.toml).
