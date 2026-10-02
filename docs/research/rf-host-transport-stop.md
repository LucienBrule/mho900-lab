# Initial stock baseline transport stop

The first renewed-window baseline attempt stopped at its initial ADB connection
on 2026-10-02T02:04:51Z. The client returned exit status zero but reported
`No route to host`; the controller required a positive connection response and
stopped before any remote inspection, SCPI request, observer read, native-file
change or reboot. This is a negative transport result, not a stock policy witness.

The workstation had recorded the isolated peer's direct subnet route through the
scope-facing interface before attempting the connection. The sealed capture holds
seven workstation-originated frames: one gratuitous ARP, two IGMP reports and four
multicast UDP frames. It contains no ARP request for the peer, TCP SYN or
scope-originated response. The evidence supports checking workstation routing,
neighbor state and the dedicated ADB daemon first. It does not establish a
specimen fault or identify a unique cause.

The temporary workstation address was removed, the recorder exited gracefully
and reported zero kernel drops, and the isolation checks passed afterward.
The failed run remains immutable at
`out/rf/policy-initial-stock-20261002T015400Z`, sealed by SHA-256
`f398bea324769f06d08cbe9c56cbc84d6c4fbdcc63d39f50855ef7979c8b0c16`.
The separate independent review is
`out/rf/initial-stock-stop-independent-20261002T020600Z`, sealed by SHA-256
`71a59ab33f8cdc4e8b442311c199d856fa9557818bc79d0d50e1adf1a42dc3df`.

The bounded continuation checks the workstation's exact peer route and neighbor
cache under a new capture, then permits one restart of its dedicated ADB daemon
only after verifying ownership and no connected transports. This is a diagnostic
hypothesis. A distinct frozen baseline attempt retains all original mapping,
visible UI, protected-content, read-budget, single-reboot and thermal gates.
The RF execution decision remains closed to execution until that successor
produces independently verified stock evidence.

The subsequent host-only control recorded the same direct subnet route and an
empty scope-interface neighbor cache. It verified the dedicated local ADB daemon's
ownership and empty transport list, then restarted that daemon once. No scope
connection or management command was issued during the control. Its full capture
contains 15 stored frames; the recorder exited gracefully with zero reported
kernel drops, and the temporary address was removed before the final isolation
audit. The diagnostic seal is
`out/rf/host-transport-diagnostic-20261002T021000Z.toml`, SHA-256
`c78a40653914d0e361d026e42f47f8b69454321bd672f785689c19fdf263d49c`.
An empty cache in this later control does not reconstruct the earlier cache or
prove that restarting the daemon resolves the error.

A fresh attempt after the daemon control successfully connected and verified the
existing root session. It collected the application, native mapping and protected
logical archive, then stopped at the SCPI helper's local output-directory
precondition. The generator had omitted required SCPI directories. A TCP
connection had been opened, but the assertion preceded any request byte. No
observer, native-file removal or reboot occurred. That separate negative is sealed
at `out/rf/policy-initial-stock-recovery-20261002T021000Z.toml`, SHA-256
`860a62448652fc792e5b4fe08665460012d0b04630e2bdb166eb33e2da3e8477`.

The correction creates and checks all four empty SCPI output directories before
launch: baseline, prechange, postboot and postwarmup. It also leaves future reader
output directories absent because their producer creates them exclusively. The
controller and physical gates remain unchanged. The recorded negatives retain
their original meaning and are not counted as completed stock transitions.

The separate initial-stock layout adapter passed 25 offline controls and strict
checking of its four typed Python files. Independent tests exercised all four
prepared directories through the original query helper with a fake socket;
missing and occupied directories still failed before any send. The adapter also
rejects symlink/file outputs and prior run state. The prepared controller,
configuration and complete frozen inventory are byte-identical to the previous
attempt. The independent readiness review is sealed at
`out/rf/transition-layout-independent-20261002T021900Z.toml`, SHA-256
`5146b1972992340e64621a20c4edcefbd3a4c18fd526725bf81c32ce5e577377`.
This initial-stock adapter pins that exact inventory; later arm configurations
require their own reviewed layout preparation. Readiness is not a stock witness.
