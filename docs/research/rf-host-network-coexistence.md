# RF acquisition alongside VM networking

The operator identified Docker as the host-network change and directed the
investigation to coexist with it. The earlier stopped diagnostic remains
preserved. Its failure established an unmet host prerequisite, without testing
scope reachability or acquiring RF samples.

The fresh read-only assessment recorded enabled IPv4/IPv6 forwarding and packet
filtering, a VM bridge, and a DHCP daemon listening on a wildcard socket. The
scope-facing interface remained unaddressed and outside that bridge. Those
global observations alone do not establish which interfaces the DHCP service
serves or which source networks the translation rules cover.

Specific configuration evidence narrows the boundary. The daemon configuration
enables DHCP only on the VM bridge, disables BOOTP, and contains no relay
enablement. The installed daemon manual defines interface arrays as enabling
only their named interfaces. The positively enumerated packet-filter anchor
tree and successful queries of its specific children show translations for VM
subnets rather than the scope segment. A wildcard filter query reported an
embedded error despite exit status zero; that incomplete query is retained and
excluded from valid coverage evidence. These are configuration observations,
not a packet test or a guarantee that configuration will remain unchanged.

The [host fixture contract](../../experiments/rf-stopped-range/host-coexistence.toml)
retains the firewall, DHCP configuration and unrelated VM processes. Before
scope contact, it preserves the actual forwarding values and temporarily sets
both to zero. This can pause unrelated forwarded VM traffic during acquisition.
Checks at serviced execution boundaries must detect unexpected forwarding,
interface, route or relevant configuration changes and stop the run without
repeatedly forcing values back. Their actual timing coverage must be recorded.

Cleanup closes the scoped connection, retires the owned transport, proves
endpoint absence, removes and verifies the temporary address, and stops the
owned DHCP and capture helpers. Only then may the fixture restore the exact
saved forwarding values. Uncertain cleanup retains an explicit isolation HOLD.
The fixture does not disable packet filtering, flush rules, stop Docker or
introduce external routing.

The physical question remains the
[single stopped waveform diagnostic](rf-stopped-range-diagnostic.md): one
100 MHz source attempt and one coherent RAW record at the declared wider
range. The coexistence amendment supplies no RF result and cannot replace any
missing comparison slot. Actual waveform evidence must justify the range of
a subsequent matched stock–derived–stock comparison.

The read-only host audit is sealed as
`out/rf/host-reassessment-20261002T185223Z.toml`
(`df4076fc394823320465924b2564a6904273ce5b281a75e36f34aef3d5516bdf`).
Specific translation evidence is
`out/rf/host-translation-20261002T185312Z.toml`
(`673d8c815d15316b95fc7d3c2ba41adc791492d7780aa622886cab607cb13ccb`),
and daemon configuration, local manual and individually queried filter children
are in `out/rf/host-dhcp-config-20261002T185511Z.toml`
(`b8eda571262cccaca37c32587029c2aabac00171738dc1b808b3a5fca0698868`).
The independent supplemental assessment is
`out/rf/host-isolation-supplement-independent-20261002T185700Z.toml`
(`af2d07caa97222aaaee2e723681c9d223b8a6a4a4de4a7e4955ccd8311c438c5`).
The remaining parent-anchor query is preserved in
`out/rf/host-apple-parent-20261002T190452Z.toml`
(`42d7860919c09ce02bc28fdb7c6631a852c0309e9bb2ba0344ba7114d64dbcd5`).
Together, the specific queries cover eight observed anchor nodes with separate
translation, filtering and child-inventory views. Runtime checks compare that
coverage and the relevant configuration bytes with the preserved baseline.
Preparation, actual fixture operation and final restoration require separate
reviewed evidence.
