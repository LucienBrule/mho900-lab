# Resolve calibration file access before stock loaders

Both independent questions have positive results: the whole-loader observer passes its private controls and the exact
stock defaults occupy the required guest paths with complete root-shell roundtrip equality. This still leaves a concrete
stock-process precondition. The measured directories are `tmpfs`; the files created by adb-root are `su_tmpfs`.

A review of matching Android 7.1.1 policy source predicts directory traversal but file-access denial from `system_app`.
The exact guest policy is pinned, but its compiled allow rules have not been decoded. The source prediction therefore
remains an inference. Running the entire stock initialization to discover this small permission question would add
unnecessary dependencies to its interpretation.

Select a new private file-access application. Use the public AOSP platform test certificate only after matching it to the
disposable guest platform certificate. A matching signed application requesting `android.uid.system` should naturally
run as UID 1000 with the same `system_app` process context already observed for the stock application.
Both properties
must be measured. No policy, file label, or package-admission exception belongs in this control.

The probe performs only fixed-path directory metadata and file metadata/open/bounded-read operations for the two exact
calibration defaults. It records separate outcomes, errno values, byte counts, hashes, and its own identity. Preserve
the raw report and available Android audit records, then capture final guest health and teardown. One failed operation
does not prevent recording the other file's independent result; no fixture modification or alternate access path is
attempted. Missing execution is a harness no-go, not an observed denial.

A denied operation closes this question and selects a new bounded fixture decision. Successful complete reads support
admitting whole-loader stock validation. Neither outcome supplies or validates FPGA behavior, and the stock program's
predicted first three loader returns remain unobserved.

The source review is preserved in `out/calibration-filesystem/stock-access-review.toml`. The new input manifest will pin
its provenance, the public certificate, the private probe, and the complete execution recipe before a guest is started.
