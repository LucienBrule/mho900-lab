# Stage Two A: isolated DHCP exchange, then five minutes of silence

The already-powered MHO984 requested the offered private IPv4 address and received
one DHCP ACK. The full Ethernet capture contains four frames: Discover, Offer,
Request, ACK. No further frames were captured during the following 300.237 seconds
before recorder shutdown began. The operator reported an unchanged UI and no new
prompt during the post-ACK window. No physical connection or control was changed.

This establishes a completed DHCP exchange and the absence of additional recorded
traffic in this interval. It does not independently establish installation of the
address or the instrument's route table: there was no subsequent address-bearing
traffic or management read. No inference of absent services, disabled update
logic, or unchanged persistent storage follows from network silence.

## Intervention and isolation

A bounded Ethernet-level DHCP responder served only the previously observed
specimen MAC and one private address. It supplied a /30 subnet and 3600-second
lease, with no router, DNS, domain, static-route or classless-route options.
Replies contained only message type, server identifier, lease time, subnet mask
and the echoed client identifier. There was one Offer and one ACK; the responder
closed immediately after ACK. It performed no address-conflict probes.

The Mac remained unnumbered on the specimen-facing interface. The server
identifier was used only in the raw Ethernet replies; it was not assigned to a
host interface. This avoided enabling ordinary host services on the segment.
No IP listener, ARP responder, NAT, forwarding, sharing, bridge membership or
route was added. Both host service configurations remained inactive, the default
route remained elsewhere, and the full host network preferences matched before
and after. Existing Stage One isolation and restoration instructions remain in
effect. The specimen Ethernet must be disconnected before ordinary host network
configuration is restored.

The private fixture used Scapy 2.6.1 to construct and send explicit Ethernet
frames. Offline fixtures were decoded with tcpdump before the responder was
enabled. The actual captured negotiation was separately checked for a single
transaction, matching requested/offered address and the allowed reply option set.
This fixture is a single-exchange experimental responder, not a general DHCP
service. No renewals, NAK, FORCERENEW or cleanup packets were sent.

## Timing and evidence

Times are UTC on 2026-09-29; local PDT on 2026-09-28 is seven hours earlier.

| Event | UTC |
|---|---|
| Capture process started | 02:09:14.642411 |
| Capture Ethernet header verified | 02:09:14.891193 |
| Responder ready | 02:09:29.361547 |
| Captured Discover | 02:10:40.955840 |
| Captured Offer | 02:10:40.961916 |
| Captured Request | 02:10:40.966550 |
| Captured ACK | 02:10:40.970646 |
| Stop requested after passive window | 02:15:41.207442 |
| Recorder forcibly stopped | 02:15:49.218307 |
| Final audit and run completion | 02:15:53.955128 |

Two scope frames and two responder frames were recorded; all four were IPv4
broadcast DHCP. There were no captured post-ACK packets, new protocol emissions,
off-segment destinations, ARP, IPv6, DNS, mDNS or SSDP in this run. Exact MAC,
address and DHCP hostname remain in private evidence. No update indication or
configuration-changing prompt was reported. There was no Web Control, SCPI,
ADB, USB, scan, discovery request or authentication action.

The capture used Ethernet link type, a 262144-byte snapshot length, no capture
filter, immediate delivery, packet-buffered file writes and live text decoding.
All four stored records are full length, with no partial trailing record, and
tcpdump independently counted four packets. Raw and sealed files are identical.
Host isolation was checked every five seconds and in privileged before/after
audits. The original Stage One capture hash and this run's pre-intervention
artifact hashes were reverified unchanged.

The recorder again failed to exit on SIGINT and SIGTERM and required SIGKILL.
Kernel-drop counters are unavailable. Complete stored records are established;
capture completeness for all traffic on the wire is not independently proven.
This recurring host recorder shutdown problem should be resolved with an offline
or separate host-only control before a later physical acquisition depends on
drop statistics. No extra specimen run was used to troubleshoot it here.

## Decision

Stage Two A is sealed. Its address-only intervention did not produce additional
captured traffic or an operator-reported UI change. Capture, responder and
supervisor processes are stopped, capture promiscuity has cleared, and host
isolation is retained. The one-hour offered lease has no renewal service running;
its future expiry or retention was not manipulated or tested.

Stage Two B is not authorized or admitted. No further scope action follows from
this result. The [result manifest](../../experiments/physical-first-contact/stage-two-a-result.toml)
binds the separate private evidence run and report.
