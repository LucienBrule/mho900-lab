# Physical first contact: Stage One host checkpoint

Stage One begins with an operator-reported unpowered MHO984, disconnected power,
USB device and Ethernet connections at the instrument, an empty front USB host
port and no probes. Host preparation is complete; the first physical transition
requires the operator's explicit confirmation. No physical boot, scope packet,
firmware version, option state or stable application UI has been observed yet.
Stage Two is not admitted.

## Preparation and evidence boundary

The local run has a stable identity and UTC/local timestamps. Its raw host
baseline includes service order and configuration, hardware-port mapping,
interface flags and addresses, IPv4/IPv6 routing, default routing, forwarding,
DNS, sharing settings, privileged listener/PF checks and relevant device topology.
The private evidence also preserves initial operator photo hashes and restoration
information. Host and unit identifiers remain in the excluded evidence area;
source contains only the generic procedure and hash-bound checkpoint.

The Ethernet identity was established by following the registry ancestry from
the BSD interface through its Ethernet controller and matching the PCI tunnel
endpoint identifier to the attached dock's Thunderbolt identifier. Interface
numbering or a service display name alone was not accepted as proof.

The audit established a separate ordinary Internet route, disabled IPv4/IPv6
forwarding, inactive packet filtering/NAT, no bridge membership for the selected
interface, no active Internet Sharing and no DHCP server listener. Existing host
adapters and network policy were preserved. The selected Ethernet service's IPv4
and IPv6 configurations were then made inactive; it has no protocol addresses or
route entries, while its Ethernet interface remains up for passive capture.

On this host, the network service retained its original DHCP and link-local
method values while adding `__INACTIVE__` flags. A summary display can still say
DHCP. Verification used the persisted flags, dynamic configuration, lack of
addresses and routes, and a full before/after preferences comparison. The only
persistent changes were those two flags. The original full service dictionary,
network baseline and guarded restoration instructions are preserved locally.

## Capture and restoration discipline

One capture process records raw Ethernet and a simultaneous human-readable UTC
decode. It uses promiscuous capture, no packet filter and a 524288-byte snapshot
length. The process opens BPF with authorization and then drops to the operator
account; no global device permissions or host security policy were changed.
A separate read-only watcher records carrier at one-second intervals and checks
routing/forwarding/address conditions. Packet timestamps remain the authority
for first packet timing; carrier timing is limited by polling resolution.

Before handoff, process health, the open BPF/output descriptors, a flushed pcap
header and offline readback were checked. An independent file-only synthetic
control verified simultaneous raw writing and decoding; it was never transmitted
on a network. Zero packets and inactive carrier are the pre-link observations.
An immutable pre-link snapshot is retained separately from the live append-only
capture. Subsequent phase snapshots and the final capture must receive new
filenames, timestamps and hashes, not overwrite earlier evidence.

Capture-launch and watcher-launch failures during preparation are retained in the
private evidence. They occurred before any operator physical transition. These
were resolved and the running processes verified before declaring readiness.

After acquisition and explicit operator confirmation that the specimen Ethernet
is disconnected, stop and seal capture, restore the selected service's original
IPv4/IPv6 settings, and compare the full service dictionary and relevant host
state with the baseline. Confirm capture-related promiscuity has cleared. Do not
blindly replace global preferences if unrelated host changes occurred meanwhile.
Restoration is prepared but has not been executed at this checkpoint.

## Operator gates

The eleven host/physical-state prerequisites have passed. The last three
(disconnected USB device cable, disconnected power and empty front host port)
are operator-reported physical facts, not claims derived from network silence.

After the Ethernet-only confirmation, record the physical transition and observed
carrier state, verify continuous capture health, and return the power-only gate.
An unpowered device may present no carrier; preserve the actual observation
rather than manufacture a successful link measurement. Power requires a separate
operator confirmation. Do not infer either transition from elapsed time.

First boot remains passive: no DHCP service, management address, service request,
USB connection, storage insertion or configuration change. Visible UI facts must
come from operator photographs or transcription. Unexpected behavior stops
progression and preserves evidence. Stage Two requires separate authorization.
