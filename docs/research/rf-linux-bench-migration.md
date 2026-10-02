# Dedicated Linux bench controller

The operator selected a dedicated Rocky Linux workstation after shared-host
network changes interrupted RF acquisition. The specimen Ethernet cable is
disconnected during preparation. The earlier Mac diagnostic remains stopped;
its drafts and immutable evidence do not become a successful experiment through
this architecture change.

The bench host retains its Wi-Fi management connection. Its dedicated physical
Ethernet interface moves into a named Linux network namespace containing only
that interface and loopback. The namespace has a private address and connected
route, no default route, no management-facing virtual link, and no forwarding.
SSH controls processes on the bench host; ordinary ADB and SCPI sockets execute
inside the bench namespace. The workstation does not act as a router to the
instrument.

This uses the separation provided by Linux network namespaces and standard
`ip netns exec`, rather than a userspace TCP implementation. See the
[Linux namespace manual](https://www.man7.org/linux/man-pages/man7/network_namespaces.7.html)
and [ip-netns manual](https://www.man7.org/linux/man-pages/man8/ip-netns.8.html).
Existing host firewall and SELinux policy remain in place. Named ownership and
teardown are explicit, and relevant network profiles are preserved before the
interface leaves NetworkManager management.

Preparation installs the required capture and Python runtime packages from the
host's configured distribution repositories. Linux ADB is acquired from the
[official Android Platform Tools distribution](https://developer.android.com/tools/releases/platform-tools),
with its downloaded bytes, executable hash and reported version preserved.
Private SSH destinations, host paths and device-specific identities belong in
local evidence and configuration, not this description.

Host-only controls prove ordinary socket operation and graceful recorder exit
with recorded drop statistics. They supply no claim about specimen reachability
or RF response. A prepared DHCP configuration provides one MAC-bound private
24-hour lease without router or DNS options; no specimen service starts during
disconnected preparation.

Physical migration is a separate checkpoint: fresh capture first, explicit
operator Ethernet connection, then bounded lease and identity/transport checks.
The existing RF coax path and stock application, native, option and calibration
invariants remain unchanged. Moving the RF source's USB serial connection, if
needed for unattended acquisition, is another explicit setup transition.

The disconnected preparation passed its host-only control. A single loopback
TCP connection returned the exact 24-byte request and closed both directions.
The full capture contains ten complete frames; the recorder reported twenty
filter-received packets, zero kernel drops and graceful exit zero. These counts
have their own meanings and are not interchangeable. The management connection
remained available, root firewall rules compared byte-for-byte equal, and SELinux
remained enforcing. The prepared DHCP service was inactive.

The namespace service is active but is not enabled for automatic boot. Its
ownership record preserves the original NetworkManager and interface state.
Teardown was reviewed in source and has not been exercised. Host clock domains
were measured separately and must not be silently treated as synchronized.

Preparation evidence is `out/rf/linux-bench-preparation-01.toml`
(`0e672958ed89aa60c46907780ff06c6f58f46f7e7b8ac689ec2c9c9fcf3cac9d`,
44 files). Independent review is
`out/rf/linux-bench-independent-20261002T193500Z.toml`
(`2ceb818ce4e712b400da4fdf162a17fae98a2fe4a81f623d77ac0643fb3a1e3a`,
nine files). The accepted result is readiness for capture-first cable migration;
specimen reachability and RF response remain untested on this host.

The first transient recorder service stopped at systemd's `STDERR` setup
(`222/STDERR`) before tcpdump executed. No capture, DHCP, cable transition or
SCPI exchange occurred. The independently reviewed stop is preserved in
`out/rf/linux-link-01-armed.toml` and
`out/rf/linux-link-01-stop-independent-20261002T194100Z.toml`.
The path-context evidence does not distinguish ordinary permissions from
SELinux enforcement. The bounded successor uses journal stderr and a standard
service state directory, preserving the failed unit and host security policy.
It must prove actual capture readiness and graceful closure while disconnected
before a separate physical link checkpoint begins.

The journal-backed successor reached tcpdump but exited with a savefile
ownership error before capture. Its stop is sealed separately in
`out/rf/linux-recorder-service-control-02.toml`; neither failed service was
rerun. The next bounded control reuses the direct Python process-launch ancestry
that already passed the loopback recorder test. Standard tcpdump retains its
normal privilege handling; a timed supervisor records readiness, sends SIGINT,
and preserves the actual capture and exit/drop statistics. This changes the
launcher boundary without changing host security policy.
