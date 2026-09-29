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
