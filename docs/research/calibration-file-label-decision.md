# Two-file calibration label hypothesis

The preceding control observed `EACCES` for both default files from the actual `system_app` domain, with matching kernel
audit records. Directory traversal succeeded. Select one narrowly scoped fixture correction: assign the existing
`u:object_r:system_app_data_file:s0` type to exactly those two files. Keep directories, bytes, ownership, modes, guest
policy, probe APK, and ramdisk unchanged.

Matching Android policy source grants this type the `getattr`, `open`, and `read` permissions required by the recovered
loaders. It is intended for application data. The alternative `system_app_tmpfs` has no explicit `getattr` or `open`
permission in the reviewed macro and is not selected. The exact guest policy contains both type symbols; complete
compiled-rule and constraint decoding is still unavailable. This remains a hypothesis until the private probe reads
the complete expected bytes under the corrected labels.

In one fresh guest, reproduce and verify the original fixture, record both specific label assignments and all labels
and metadata, then run the unchanged probe once. Preserve command failures and stop without trying another type.
Complete reads must match both stock file hashes. A negative result closes this question and selects another bounded
decision; it does not justify changing the experiment in place. Final health and package cleanup remain mandatory.

This is a disposable guest data fixture, not a claim about the physical instrument's filesystem or policy. If it passes,
whole-loader stock validation is the next question. Its terminal boundary remains before `SetADCParameter(0)`.

The source review is pinned in `out/calibration-access/label-decision-review.toml`; the successor task plan is
`.agents/plans/calibration-file-label.yaml`.
