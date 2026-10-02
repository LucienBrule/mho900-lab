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
