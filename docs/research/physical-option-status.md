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
