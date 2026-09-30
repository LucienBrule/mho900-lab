# Synthetic sealed-review example

Every byte here is manufactured offline. No instrument, socket or recorder
produced this fixture. The address range is reserved for documentation; the
locally administered MACs, timestamps, identity and counters are synthetic.

See the [walkthrough](../../docs/runbooks/synthetic-review-walkthrough.md).
`walkthrough.sh` copies the six-file `bundle/` into a fresh output directory,
uses the existing CLI to seal and review it, and preserves two expected failures.
It opens no endpoint and launches no packet recorder.

`manifest.toml` is the exact inventory. Its independently retained expected SHA-256
is `b049d958172b0b013aa9934c66e029d2a33559e13aed9d3e362719e8ce9672f6`.
`profile.toml` assigns roles; `provenance.toml` describes the manufactured packet
fields, checksum algorithm, timestamps and expected extents. These files and all
reports remain outside the sealed bundle.

The capture carries two canonical queries and their synthetic replies in one
payload per direction. Its six records provide the sequence origins and FIN
extents required by the reconstruction profile. It is deliberately not a complete
TCP state-machine transcript: pure ACK packets and the final ACK are omitted.
IPv4 and TCP checksums are valid; Ethernet padding reaches the minimum frame size
without an FCS. The statistics file is authored test input, not process evidence.

The fixture demonstrates content consistency and documented rejection boundaries.
It cannot demonstrate physical behavior, recorder lifetime, wire completeness,
response causality, device execution or option persistence.
