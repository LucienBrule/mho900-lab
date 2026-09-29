# Stage Two B1: first physical SCPI identity

The MHO984 answered one `*IDN?` request on IPv4 TCP port 5555. The exact software
version returned is **`00.01.00`**. The response identifies the manufacturer as
`RIGOL TECHNOLOGIES` and model as `MHO984`; the exact serial and complete raw
response are retained privately.

The operator renewed the instruction to perform SCPI after the preceding
[address-transition stop](physical-stage-two-b1-result.md). The admitted task
explicitly retained the already identified host-originated local discovery as
background while preserving isolation, recorder-health and single-query limits.
Tasking was committed and pushed as `dadeda9` before execution.

## Observed exchange

A fresh privileged baseline confirmed isolation and adequate remaining lease
lifetime. A fresh full Ethernet capture was running before the temporary host
address was assigned. The recorder's inherited signal mask was normalized to
empty. Initial specimen ARP requested the reserved host address using the leased
source address; that is new physical evidence that the client was using its lease.
It does not identify why it sought that neighbor.

The client bound both its source address and macOS `IP_BOUND_IF` to the isolated
interface. It opened one connection to the leased address on TCP 5555, sent exactly
six bytes (`2a 49 44 4e 3f 0a`, or `*IDN?` plus LF), received one 50-byte
LF-terminated response, and closed. No retry, alternate port, hidden client query,
option request, Web Control, ADB, USB, scan or instrument-setting command occurred.

| Event | UTC, 2026-09-29 |
| --- | --- |
| Capture ready | 02:51:35.744539 |
| TCP connect initiated | 02:52:06.601489 |
| TCP connection established | 02:52:06.608823 |
| Query sent | 02:52:06.609470 |
| Complete response recorded | 02:52:06.661704 |
| Temporary host address removed | 02:52:07.725582 |
| Recorder exited with status zero | 02:52:07.735021 |
| Final host audit complete | 02:52:12.670497 |

Local time is September 28 PDT, seven hours earlier. The response was recorded
about 52 ms after the send event; these application timestamps include observation
and scheduling latency and are not an instrument processing-time measurement.

Independent packet analysis confirms one bidirectional TCP flow, one client SYN
(with ECN negotiation flags), one six-byte request payload, and one 50-byte response
payload. Both reconstructed payloads exactly match the raw client artifacts.
Ethernet padding is excluded using the IP/TCP header lengths.

## Background, recorder and restoration

The capture contains 50 complete frames: 42 host-originated and 8 scope-originated.
Protocol counts are 6 ARP, 32 UDP, 2 IGMP and 10 TCP. The previously identified
host-local discovery classes were retained: subnet UDP discovery, SSDP, mDNS and
IGMP membership reports. These are not part of the SCPI exchange and do not imply
that the segment was quiet. There were no unexpected source MACs or external
unicast flows in the stored capture. No gateway, DNS, NAT, forwarding, bridge or
Internet Sharing path was introduced, and no DHCP lease was renewed.

The recorder stopped gracefully after SIGINT with **50 captured, 50 received by
filter, and 0 dropped by kernel**. All stored packets are full length with no
partial trailing record. The temporary address and isolated-subnet route were
removed under capture. Final host network preferences and interface-inventory
property lists exactly match the baseline; the interface is again unnumbered,
the normal default route remains elsewhere, forwarding remains off, and no BPF
capture user remains. This run made no physical cable or control transition.
No new operator UI report was solicited for this short exchange.

## Offline corpus reconciliation

The returned `00.01.00` shares the prefix of the release-note versions in the
local official package: `00.01.00.00.26`, `.25`, `.24` and `.22`. The identity
response omits the final two components, so it cannot distinguish those releases
or establish a match to any particular APK, library or firmware image. The local
release-note hash and exact observed identity fields are preserved separately.

This physically validates the chosen 5555/LF transport and the documented identity
query on this specimen. It does not establish its exact installed build, options,
ADB availability, filesystem contents or firmware byte identity. No additional
query follows from this result; stop for operator review.

## Evidence

Private run: `out/physical/mho984-stage-two-b1-idn-20260929T025112Z`.

| Artifact | SHA-256 |
| --- | --- |
| `request.bin` | `2e8c5970fd7906e35a37aa7078ed2fad7a093f63e56e340e0ff07ab935a20086` |
| `response.bin` | `37c97e07f053c85cf48a961cd1cb6c68723a0b71c86b1ee0138808c523ed0337` |
| `sealed/stage-two-b1-idn.pcap` | `aa76770bf4dbeace6430f253a48146d03de553cd1a6e9d1738c5c031832e686f` |
| `sealed/manifest.toml` | `4962edd753597a46253509f77252258048d9950ba92d3b76119e12948d5822d3` |

The manifest binds raw/live evidence, fixture and launch inputs, before/after
host audits, packet verification, exact private identity and corpus reconciliation.
Earlier captures and conclusions remain intact.
