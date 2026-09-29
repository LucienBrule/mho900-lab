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
