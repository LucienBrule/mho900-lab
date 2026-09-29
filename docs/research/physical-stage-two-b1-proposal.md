# Stage Two B1 proposal: one SCPI identity query

Status: proposal only; no host address has been assigned and no instrument
connection has been made. Recorder shutdown is now verified by the
[host-only control](recorder-shutdown-control.md). A numeric SCPI socket endpoint
remains unverified, so B1 is not yet executable under the documented-endpoint
requirement. No B1 execution task is admitted.

## Official command evidence

The [official MHO900 Programming Guide](https://www.rigol.com/dam/global/downloads/brochures/en/program-guide/oscilloscopes/MHO900-ProgrammingGuide.pdf)
was downloaded from the link on the manufacturer's product page. Its SHA-256 is
`a671c065bd04a85d05e9d4cef732df3ba4884c2218054f64d1a83fb5a43cffd5`,
identical to the existing local reference copy. The product page lists document
revision PGA461012-1110, dated 2026-02-26.

- Section 3.12.1, printed pages 141-142 (PDF pages 165-166), describes `*IDN?`
  as a parameterless identity query. The documented comma-separated fields are
  manufacturer (`RIGOL TECHNOLOGIES`), model, serial number and software version.
  It specifies no setting change. That is command semantics, not a guarantee
  against incidental logging or communication-buffer changes.
- The C++ example on printed page 493 (PDF page 517) appends LF to the command
  and illustrates `*IDN?`. This example uses VISA over USB. It supports LF as
  the candidate command terminator, but is not an independently documented raw
  TCP framing contract.
- Section 3.14.11, printed pages 159-160 (PDF pages 183-184), documents a
  `SOCKet` VISA-address type. It does not give a numeric socket port. The address
  query described there will not be sent: B1 allows only `*IDN?`.

The [official MHO900 User Guide](https://www.rigol.com/dam/global/downloads/brochures/en/user-manual/oscillosopes/MHO900_UserGuide_EN.pdf)
was also checked. Its SHA-256 is
`0fcd76ebc1e454af0f699811df5c2acd6243ade8e0626a0352c2d9d493dafab2`.
Printed page 290 (PDF page 308) shows a Web Control field labelled SCPI Socket
Port, with no value. The relevant pages were rendered and visually inspected;
this is not an OCR omission. Neither this blank field nor another instrument
family's usual port establishes the endpoint for the MHO900.

Before execution, resolve the numeric endpoint from authoritative MHO900-specific
material offline. Static firmware evidence could supply a separately labelled
implementation-derived candidate, but would not by itself satisfy a requirement
for a documented endpoint. Do not use a scan, trial connection, Web Control,
VISA resource discovery, or another SCPI query to fill this gap.

## Proposed bounded procedure once the endpoint and execution are approved

1. Preserve a new private run, baseline and exact host-address rollback. Check
   the recorded interface/MAC identity, physical continuity, default route,
   forwarding, sharing, bridge membership and existing capture users. Check the
   recorded lease lifetime without contacting the instrument. The Stage Two A
   ACK offered one hour, with no renewal service remaining. If expired, uncertain,
   or too close to expiry for the bounded operation, stop; do not silently renew
   it, change the scope address or reboot.
2. Start a fresh full Ethernet capture with no restrictive filter through the
   corrected recorder launcher. Preserve its empty post-normalization signal
   mask receipt, verify the Ethernet pcap header and live decoder, and establish
   an early recorder-health stop gate. No recorder error permits progression.
3. Add only the reserved host address in the existing isolated /30, as temporary
   host configuration under capture. Keep host DHCP and IPv6 autoconfiguration
   disabled. Add no router, DNS, forwarding, NAT, sharing or route outside that
   directly connected subnet. Record the resulting addresses and route delta.
   A connected route for the isolated subnet is expected; an external route is
   not. Assigning a host address may cause ordinary OS services to emit traffic:
   inspect this transition before opening SCPI. Unsolicited service discovery
   or other unexpected traffic is a stop condition, not permission to suppress
   host services globally or continue regardless.
4. Use a minimal client bound to the isolated host address/interface and the
   exact leased destination. Make one TCP connection to the verified numeric
   SCPI endpoint. Do not ping first, enumerate resources, probe other ports, or
   use a client library that performs hidden identification/reset/clear calls.
   Ordinary ARP required for this single destination and the TCP handshake are
   transport traffic to preserve, not separate reachability tests.
5. Send one application-level query. The proposed payload is six ASCII bytes,
   `2a 49 44 4e 3f 0a` (`*IDN?` followed by LF), subject to the transport evidence
   gate above. No prefix, semicolon, extra query, option read, clear, reset,
   retry or alternate terminator is allowed. TCP retransmission of the same
   sequence bytes is distinct from issuing the query again; verify the
   reconstructed stream contains exactly one payload.
6. Preserve request and response bytes unchanged, their timestamps and the
   connection outcome. Use bounded connection/read deadlines (proposed five
   and ten seconds) and a 4096-byte response ceiling. These are harness limits,
   not claimed vendor response limits. Preserve partial, malformed, oversized
   or timed-out responses as failure evidence; do not issue an error query or
   retry. Extract the four identity fields only into a separate derived record,
   preserving whitespace and the exact software-version string. Keep the serial
   private; do not infer firmware-file identity from a version string alone.
7. Close the connection and remove only the temporary host address, returning
   to the prior isolated host state under capture. Do not revoke or renew the
   scope lease. Stop the recorder gracefully and require final capture/filter/
   drop statistics and complete pcap records. Preserve any failure as a stop
   result, hash all evidence, and make no further specimen connection.
8. Reconcile the returned model and software-version text against the existing
   official/community corpus offline. Report matching and nonmatching candidate
   builds; do not assert byte identity without subsequent independent evidence.
   Stop for operator review before any additional scope request.

## Scope and stop conditions

No option-status query, Web Control, ADB, USB, port scan, service-discovery request,
authentication approval, acquisition change, calibration, reset or firmware
operation is included. A recorder failure, unexpected peer, route/isolation
change, unexpected network behavior or UI prompt stops progression and preserves
the evidence already collected. Do not change scope configuration to resolve it.

The current physical setup is left unchanged. Proposal review and endpoint
verification do not authorize B1 execution. The next concrete research question
is: which authoritative MHO900-specific reference supplies its raw SCPI port and
framing, without querying the specimen?
