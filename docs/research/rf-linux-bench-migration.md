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
