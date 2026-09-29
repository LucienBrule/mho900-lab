# Physical documented option-status baseline

The operator approved read-only physical baseline observation after the
acquired-input guest comparison. This first bounded pass uses the supported
SCPI interface: one `*IDN?`, then eleven
`:SYSTem:OPTion:STATus?` queries, one each for BND, AFG100, AFG50, AUDio,
CAN-FD, FLEX, AERO, RLU-05, BWU03T05, BWU03T08 and BWU05T08.

Official MHO900 Programming Guide section 3.24.18, printed pages 293–294,
defines these selectors and boolean 0/1 replies. Section 3.24.19 describes
VALid as the compatibility alias and recommends STATus. The locally preserved
official PDF SHA-256 is
`a671c065bd04a85d05e9d4cef732df3ba4884c2218054f64d1a83fb5a43cffd5`.
Its [official download](https://www.rigol.com/dam/global/downloads/brochures/en/program-guide/oscilloscopes/MHO900-ProgrammingGuide.pdf)
and acquisition provenance are preserved. TCP5555 is implementation-derived
and previously physically observed; numeric port provenance remains distinct
from the guide's socket transport documentation.

Preparation freezes the exact request list, bounds responses and stops on
unexpected identity, format, timeout or extra reply bytes without retries.
A local socketpair control passed the complete sequence and an invalid-reply
stop. The existing single-client lease responder passed offline packet-shape
and foreign-client rejection checks. No physical contact occurred in preparation.

Fresh host baseline retained hardware/interface mapping, routes, addresses,
forwarding, NAT/sharing, listeners, DNS and network preference files. Before
contact the supervisor rechecks isolation, starts full-packet Ethernet capture,
then introduces only the temporary isolated host address and single-client
lease maintenance. A new captured ACK is required. Only source-bound TCP5555
SCPI traffic is initiated; no ADB, Web Control, USB or helper staging occurs.

Preparation seal: `614166d34e2bb9d8c3afbd30bd92d9603db186dfb403eb5cbb3a4fc88f553178`. Unit identity and raw packet/response
evidence remain private under the dedicated physical run.

This is eleven documented installable-option states, not the entire fourteen
entry native catalog. The three built-in flags and cached raw/effective
bandwidth remain separate gaps. Identity alone is not a cached bandwidth read.
No install, reboot, capability change or calibration action is authorized by
this task.

## Attempt stopped before SCPI

Run `mho984-option-status-20260929T132549Z` armed capture at approximately
13:27:27 UTC and waited ten minutes for a fresh client DHCP request and captured
ACK. None arrived. The earlier recorded lease had expired at 13:10:08 UTC;
the run did not assume that old address was still valid.

The frozen supervisor stopped at the lease gate. It sent zero SCPI requests,
zero DHCP offers/ACKs, and made no ADB or other management connection.
No physical option state or fresh identity was obtained.

The full capture contains 204 complete frames, all from the host and matching
previously characterized local background traffic. No scope-originated frame
was captured. Both recorder counters equal 204 with zero reported kernel drops.
Independent replay checked every frame and these counters. This observation
does not establish why the scope was silent or whether its UI was stable.

Cleanup removed the temporary host address, stopped the single-client responder,
terminated capture gracefully with exit zero and rechecked isolation.
Both copied network preference files match baseline bytes. The privileged
host shell was closed. No cable, device setting, entitlement or capability
transition was performed.

| Private evidence artifact | SHA-256 |
| --- | --- |
| `live/capture.pcap` | `1cf393c0825ddb3269283ec088e8a47d70a357b6e859b86a1bfc96e0a61cd7c2` |
| `evidence-sha256.txt` | `6d1a15069b5173cd03ea26fb84a462874536fb1027fa65e006c3642f5911dcbd` |

## Decision

The query sequence remains ready, but there is no new option result to compare
with the guest. Preserve this attempt as a lease-acquisition stop, not a SCPI
failure or evidence that options are absent.

The next useful input is the operator's current scope UI and LAN indication.
Any later link refresh should occur as an explicit transition under a new
capture. Do not silently probe the expired address or infer the three native
built-in flags or cached bandwidth values. The broader physical baseline
objective remains incomplete.

### Verification correction

The initial offline capture checker omitted host gratuitous ARP, although the
live classifier permitted it. It stopped at the first such frame. The initial
closure assertion incorrectly stated that independent replay had passed because
the recording command continued after that verifier error.

A separately preserved corrected audit accepts exactly one host gratuitous
ARP and 203 previously characterized host IPv4 frames. It verifies all complete
frame lengths, matching final counters, zero drops, no scope packets, no SCPI
requests or DHCP replies, graceful recorder exit, responder closure and unchanged
network preference files. The sealed run and original failed checker remain
unchanged. Correction audit seal: `2dd9f365404c8e3b9e77307ae05af5d30453156474b666a174331bd656ffbda5`.
The task assertion is reconciled explicitly; there is still no option result.

## Six-hour lease and explicit link refresh preparation

The operator reported unchanged UI and requested a six-hour private lease plus
an Ethernet unplug/replug. A new run preserves the previous timeout intact.
The responder now advertises exactly 21600 seconds to the same single client,
with the same isolated subnet and no router or DNS options. Offline packet
construction verifies the exact duration and option set.

Fresh host baseline is retained. Full capture and responder readiness must
precede the operator transition. The supervisor records sampled carrier changes,
requires an explicit reconnect-confirmation marker and a captured valid ACK
before the unchanged twelve-query SCPI sequence. The operator-confirmation
wait is bounded to fifteen minutes, with a subsequent ten-minute ACK limit.
The expected carrier drop during the requested reconnect is allowed; identity,
address and isolation checks remain enforced.

Preparation seal: `54525c5373b92f3fa6aac7ccc5549a9abb4c75957bec40a5adfe1f1521aae934`.
This combined lease-duration/link-refresh intervention cannot by itself prove
why the previous lease stopped renewing. No device controls, power, USB,
entitlements or capability configuration are changed.

## Six-hour lease: physical baseline obtained

The explicit Ethernet reconnect was captured as carrier inactive at
2026-09-29 13:46:30.620655 UTC, then active at 13:46:48.511853 UTC.
The operator confirmed completion before SCPI contact. A complete DHCP
DISCOVER/OFFER/REQUEST/ACK exchange granted the known client 21600 seconds,
without router or DNS options. The ACK packet timestamp is
13:46:49.496731 UTC (06:46:49 PDT); lease expiry is 19:46:49 UTC
(12:46:49 PDT). The responder was stopped after this observation; the duration
is the granted client lease, not a promise of six hours of responder service.

One TCP connection to port 5555 carried exactly the frozen twelve queries at
13:47:11 UTC. The identity response matches the prior physical response exactly;
its public model/version remain MHO984 / 00.01.00. Unit identity stays private.

| Documented option selector | Physical reply |
| --- | --- |
| BND | 0 |
| AFG100 | 0 |
| AFG50 | 0 |
| AUDio | 0 |
| CAN-FD | 0 |
| FLEX | 0 |
| AERO | 0 |
| RLU-05 | 0 |
| BWU03T05 | 0 |
| BWU03T08 | 0 |
| BWU05T08 | 0 |

These are eleven documented option-status results. They do not establish the
three native built-in flags, cached raw/effective bandwidth, or the complete
fourteen-entry native catalog. A zero bandwidth-upgrade option does not negate
the instrument's base model bandwidth. Physical FLEX=0 agrees with the guest's
pre-install baseline; the acquired disposable guest's installed FlexA=true is
an intentional guest-only difference.

Independent offline verification reconstructed both TCP byte streams, checked
every raw request and response, validated the lease options and ordering, and
classified all 161 complete captured frames: 44 SCPI TCP, four DHCP, three ARP,
eight local IPv6, 99 characterized host background UDP and three host IGMP.
The final recorder counters report 161 captured, 161 received, zero kernel
drops. This is capture evidence, not a claim of omniscient wire observation.

Capture exited gracefully with status zero. Cleanup removed the host address,
stopped the lease responder, and verified isolation. Both saved network
preference files match their baseline bytes. The privileged shell was closed.
No ADB, Web Control, USB, installation, reboot or capability change occurred.
UI stability was last operator-reported before these queries; this run does
not add an independent visual observation.

Private run: `out/physical/mho984-option-status-six-hour-20260929T134427Z`.
The raw transcript, host manifests, audit source/result and capture are retained
under the sealed run, with read-only file permissions.

| Artifact | SHA-256 |
| --- | --- |
| `live/capture.pcap` | `eab7ce0e664d5ed7b30d87291826103be879d3ea24557dcbbc33006c79d0366e` |
| `evidence-sha256.txt` | `a3ca231812e3cabeb969785e3f8b53cb4125afbbc55c5a8c46463825c50b2319` |

## Six-hour decision

The requested link refresh plus longer lease enabled the authorized read-only
baseline. This combined intervention does not identify the earlier renewal
failure's cause. There is no reason to repeat these eleven status queries now.

The next bounded question is whether the physical cached raw/effective bandwidth
and native built-in flags agree with the specimen-derived guest's stock baseline.
That question remains separate from these SCPI results and needs its own admitted
observation contract. Preserve the current baseline before any physical option
installation; this batch does not perform or validate physical installation.
