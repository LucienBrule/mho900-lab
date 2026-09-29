# FRAM acquisition wrapper controls

The offline wrapper adds device identity validation and raw transaction journaling
to the reviewed [FRAM transaction core](fram-read-contract.md). Host injection
controls exercise full reads, incorrect device numbers, incomplete transfers,
errors, differing images and evidence-write failures. Physical execution remains
gated on an actual ARM64 disposable-guest check.

## First guest control: preparation failure

`wrapper-syscalls-01` executed the compiled reader against the guest's `/dev/null`
with deliberately mismatched device identity. It returned 4 after creating an
empty output directory, before producing its manifest. It did not establish the
intended wrong-device rejection. No physical instrument contact occurred.

The host mock accepted raw open flags without an independent ARM64 ABI check.
The next step is to verify architecture-specific directory/no-follow flags and
repair the wrapper before a new guest run. Preserve the first run as a failed
control; do not reinterpret it as success merely because it stopped.

The guest runner also shadowed its overall result with a command result object,
causing final TOML serialization to fail. Command outputs and teardown evidence
remain available; an appended classification records the incomplete final report.
That runner variable is corrected for subsequent runs. Neither failure indicates
a reason to change guest policy or contact the physical instrument.

## Corrected ABI and accepted guest control

Exact-revision ARM64 UAPI headers confirm `O_DIRECTORY=0x4000` and
`O_NOFOLLOW=0x8000`, rather than the values used by the initial wrapper.
Build 03 uses named ARM64 constants; host injection now independently requires
those exact flags. Eleven host controls pass, including evidence-write failures.
Earlier builds and the failed run remain unchanged.

`wrapper-syscalls-02` ran the corrected binary in a fresh API-25 ARM64 guest.
The wrong-device case produced its rejection manifest with zero ioctls. The
correctly identified `/dev/null` case performed exactly one ioctl, retained
return `-25` / ENOTTY and its scratch buffer, and saved a zero-byte completed
prefix. It did not attempt another page or a second image. Guest policy bytes,
enforcement and system_server identity remained unchanged; teardown passed.

The final report's `error=25` field was an expected ioctl errno accidentally
assigned to the runner's error variable. An appended interpretation identifies
this reporting defect; all actual acceptance and cleanup checks passed. The
variable is renamed for future runs without rewriting the original report.

This proves actual ARM64 syscall construction and bounded failure handling in
the guest. It does not prove a physical adapter identity or successful FRAM data
read. Physical acceptance additionally requires fresh owner/adapter brackets,
verified remote helper termination, complete capture/drop checks and restoration.

## Native metadata probe: descriptor control correction

The metadata-only `stat-node` probe follows a path through ARM64 `newfstatat`,
without opening a device or issuing an ioctl. Four actual-source host controls
pass. Its first disposable guest run accepted direct `/dev/null` and symlink
metadata, but the shell did not preserve the intended inherited fd 9 across
execution; the probe correctly reported ENOENT. The run failed and teardown
completed without errors. No physical operation occurred.

The next control uses explicit stdin redirection from `/dev/null` and follows
`/proc/self/fd/0`. That changes only the test's descriptor setup, not the probe.
The original failed run remains separately preserved.
