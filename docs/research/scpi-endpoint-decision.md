# B1 endpoint decision after stock implementation recovery

**Decision: the combined offline evidence is sufficient to select IPv4 TCP port
5555 and an LF-terminated `*IDN?` for the bounded B1 proposal. B1 execution remains
unauthorized.** No physical execution task is admitted and no specimen contact
or host networking change occurred.

This supersedes the unresolved endpoint/framing assessment in the
[original B1 proposal](physical-stage-two-b1-proposal.md), which remains unchanged
as a historical record. It does not supersede its isolation, recorder, lease,
one-query, preservation, rollback or stop requirements. In particular, the
numeric port is now implementation-derived and corroborated, not retroactively
vendor-documented.

## Why this is enough for the proposed query

The [static recovery](scpi-endpoint-static.md) shows the stock `.26` SCPI startup
passing decimal 5555 through a TCP-server member into `sockaddr_in.sin_port`,
followed by bind/listen/accept. That is substantially stronger than a generic
port convention or an incidental literal. The byte-identical stock Web Control
APK separately uses 5555 and sends LF-terminated commands. Pinned scopehal code
explicitly declares MHO900 LAN transport on 5555 and uses the same framing.

The official guide establishes the parameterless identity query and its four
returned fields. Combining that documented command with the recovered transport
justifies one narrowly bounded attempt once separately authorized. It does not
justify probing several ports, retrying alternate terminators, discovering
services, or starting a general-purpose instrument driver with implicit queries.

The approved candidate request would be exactly six ASCII bytes:
`2a 49 44 4e 3f 0a` (`*IDN?` plus LF), sent once over one connection. The original
five-second connect deadline, ten-second response deadline and 4096-byte ceiling
remain proposed harness bounds. A negative result is a result to preserve and
reconcile, not permission to broaden the experiment.

## Remaining uncertainty and gates

- **Firmware applicability:** this is evidence from the local stock `.26`
  package. The as-delivered specimen's software identity is still unknown.
  The first response can supply identity text, not establish byte identity to
  a corpus artifact. Listener availability and success remain unobserved.
- **Authorization:** this turn authorizes offline research and reassessment.
  B1 execution still requires separate operator authorization; no execution
  task has been admitted. Resolving the endpoint does not activate the proposal.
- **Address lifetime:** Stage Two A recorded a one-hour DHCP lease ACK at
  `2026-09-29T02:10:40.970646Z`. Nominal expiry is
  `2026-09-29T03:10:40.970646Z` (September 28, 20:10:40.970646 PDT), conditional
  on client acceptance and retention. Check time and continuity before any
  future execution. If expiry, retention or adequate remaining lifetime is
  uncertain, stop. This decision does not authorize another lease, renewal,
  address change or reboot.
- **Capture and isolation:** a future run must revalidate host isolation and
  the corrected recorder, then start a fresh full capture before introducing
  the temporary isolated host address. Unexpected traffic or recorder failure
  stops progression. No unobserved interface change is justified by this result.
- **Protocol limits:** Web Control's client convention supports LF; it does not
  fully specify the server parser. Preserve all response bytes, including
  terminators and partial responses, without normalization or fallback queries.

All other management remains outside B1: option queries, Web Control, ADB,
USB, scanning, discovery and device configuration. On completion of an authorized
B1 attempt, seal the pcap with graceful shutdown/drop statistics, preserve raw
request/response, restore the temporary host configuration, reconcile offline,
and stop for review.

## Provenance boundary

| Evidence | Classification | Role in decision |
| --- | --- | --- |
| Official MHO900 guide, section 3.12.1 | Vendor-documented command | Identity-query semantics; no numeric-port claim. |
| Stock Auklet bind path and Web Control client | Implementation-derived | Port 5555 and LF candidate, for pinned local stock inputs. |
| scopehal revision `e812615f5d1ce9498952fd1f6847f8bda151d5a3` | Third-party corroboration | Explicit MHO900 transport declaration and matching framing. |
| Physical SCPI connection/response | Not observed | Reserved for a separately authorized B1. |

The exact artifact hashes, native addresses, source links and private evidence
manifest are in the static recovery report. Earlier receipts and the original
proposal are preserved rather than rewritten to imply this knowledge was already
available at the previous gate.
