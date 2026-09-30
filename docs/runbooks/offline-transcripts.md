# Offline TCP transcript evidence

The `mho-transport` library reconstructs one explicitly selected IPv4 TCP
connection from a preserved classic Ethernet pcap. It performs no network I/O.
The Click adapter accepts literal addresses and ports solely to select captured
frames; it does not resolve a hostname or contact either endpoint.

```sh
uv run --locked mho-lab transport inspect out/example.pcap \
  --client-address 192.0.2.1 --client-port 41000 \
  --server-address 192.0.2.2 --server-port 5555
```

Those addresses are documentation examples. Supply the exact connection recorded
in the run evidence. The client labels the request direction and the server labels
the reply direction; a port number does not authenticate a service or instrument.
The tool does not select the first apparent connection or search for a scope.

Successful CLI output is a TOML summary with the capture digest, frame and byte
counts, retransmitted byte count, and request/reply hashes. It does not print raw
payloads or endpoint addresses. Library consumers receive named request/reply byte
fields and metadata through `TranscriptAccepted`. `TranscriptRejected` carries a
specific issue, with a frame number where available. CLI rejection returns exit 1;
invalid arguments return exit 2.

Reconstruction requires a unique initial SYN sequence and a consistent FIN extent
for each direction. SYN occupies one sequence number; payload begins after it.
Identical retransmitted bytes are deduplicated. Conflicting overlaps, gaps, resets,
ambiguous origins or inconsistent final extents prevent acceptance. Out-of-order
capture records and sequence wrap are handled within the bounded stream extent.
An empty payload direction is permitted when its SYN and FIN establish that extent.

This is a deliberately bounded capture profile, not a full TCP implementation:

- Classic pcap version 2.4, Ethernet link type, microsecond or nanosecond timestamps,
  either file byte order. pcapng and other link types require another decoder.
- Captured records must contain the complete recorded frame. Truncated records,
  invalid lengths and exceeded resource limits are rejected.
- Selected traffic is unfragmented IPv4 TCP. TCP fragments between the selected
  address pair are rejected even when fragment offsets hide the ports.
  VLAN-tagged frames and selected urgent-data semantics are unsupported;
  simultaneous SYN and FIN flags are rejected. IPv6 and unselected traffic are
  counted as ignored; this is not an inventory of all protocols or destinations.
- Checksums are not verified. Captured bytes may reflect host checksum offload.
  This tool reports that limitation explicitly.
- Capture-size, frame-count, frame-size and stream limits are explicit library
  configuration. The CLI uses the bounded default profile: 1 GiB capture,
  1,000,000 total frames, 262,144-byte snapshot/frame bound, 100,000 selected
  frames, 1 MiB per reconstructed direction and 8 MiB selected payload storage.
  Timestamp fractions are range-checked; chronology and clock accuracy are not.

Acceptance means the retained selected frames support one contiguous, consistent
byte transcript under this profile. It does not prove peer delivery, a valid TCP
state-machine exchange, SCPI interpretation or device execution. A pcap also does
not contain the recorder's final kernel-drop statistics. Preserve and evaluate
those independently. Exact request/response comparisons and experiment-specific
acceptance remain separate steps.

The input must be a regular file. The library compares its descriptor and named
file identity around reconstruction and rejects observable changes; this does not
create an atomic snapshot or authenticate where the capture originated.

The sequence semantics follow [RFC 9293, section 3.4](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.4).
The capture layout is checked against the [PCAP format draft, revision 06](https://www.ietf.org/archive/id/draft-ietf-opsawg-pcap-06.html).
These references explain wire and file fields; the narrower acceptance profile
above is a project contract, not a claim to implement every protocol behavior.

Public inspection and reconstruction revalidate supplied capture limits and
endpoint models before opening a capture, including unchecked model copies.
Malformed limits return explicit `invalid-limits` or `invalid-contract` outcomes;
they cannot turn an explicitly bounded operation into an unbounded read.
