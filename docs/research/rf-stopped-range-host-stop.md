# Stopped RAW diagnostic: host prerequisite changed

The separate one-record diagnostic stopped on 2026-10-02 at 18:23:00 UTC,
before packet capture, DHCP maintenance, host address assignment, ADB, SCPI,
or a source command. No waveform was acquired. This is an explicit host
prerequisite abort; it neither verifies nor disproves an RF policy effect.

The controller began at 18:22:58.473030 UTC. Its first host audit recorded
IPv4 and IPv6 forwarding as enabled. The first isolation assertion then failed
on IPv4 forwarding. The after audit also recorded both forwarding values as
one. The scope-facing interface had no IPv4 or IPv6 address and was not a
bridge member; the default route remained on a different interface. The packet
filter was enabled in both audits. Internet Sharing preferences reported NAT
as disabled. These observations do not establish which process changed the
host state or establish full isolation under the new configuration.

The controller logged `RESTORATION_FAILURE` when its final isolation check
encountered the same unmet baseline. No owned address or helper had been
created, and no scope settings had been touched. This message does not mean
that a scope restoration command failed. There is no pcap or drop-statistics
claim because the recorder was never started. No current specimen epoch,
policy, UI, source delivery or protected-corpus observation was made.

The actual run is preserved separately at
`out/rf/stopped-range-20261002T182200Z`, with native manifest
`out/rf/stopped-range-20261002T182200Z.toml`, SHA-256
`06f63e03319def529cc041dd9fa9a556c6e6f71c238fd2e5dfcf530f2a368a8d`
(70 files, 17,075,206 bytes). The frozen control inventory still verifies as
`03e7f9c0cd4ee26dabd3cf37d555458ee5c034de943c3c2c2c1a1c332dcbff33`.
The failed run must never be rerun or edited to hide the changed prerequisite.

The exact next bench question is: can the operator restore a host environment
with IPv4 and IPv6 forwarding disabled, keeping the scope, source, wiring and
controls unchanged? Any fresh diagnostic must independently recheck the actual
host routes, scope-facing addresses, bridge membership, sharing and NAT state.
If packet-filter state remains different, reconcile it explicitly through a
bounded read-only assessment; do not disable security controls to obtain a run.
No host routing or security-policy mutation is authorized by this finding.

The [one-record contract](../../experiments/rf-stopped-range/contract.toml)
remains a separate diagnostic. The original 75 comparison slots remain missing,
and the original matched-comparison abort remains preserved. A useful waveform
is still needed before selecting a common range for a newly declared comparison.
