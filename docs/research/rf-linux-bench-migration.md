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

The direct Ethernet recorder control passed while disconnected: a valid 24-byte
Ethernet PCAP header, witnessed live child/namespace readiness, timed SIGINT,
exit zero and actual zero captured, filter-received and kernel-dropped packets.
No namespace helper or listener remained. Independent review accepted only
host recorder readiness (`out/rf/linux-recorder-direct-03.toml`,
`98e1346583c288d5d0b792c55755717861e53095dbdc16d6288b2e6e33b33f67`;
review `out/rf/linux-recorder-direct-independent-20261002T194900Z.toml`,
`3dfe5d42bcd704c376407f4f2d5f807ea696efd35c5b26a42574eee3f040808c`).
The generic launcher checks for statistics presence; actual drop counts remain
an explicit review condition. Fresh caller preflight and runtime ownership are
required before the separate physical cable cue.

The operator connected Ethernet to the dedicated bench port. Fresh carrier and
recorder checks passed before the prepared DHCP service started. The capture
contains a matching REQUEST/ACK for a private `/30` address, lease length
86,400 seconds, and no router or DNS options. Independent inspection accepted
that lease prefix before the sole ordinary TCP `*IDN?` transaction.

That transaction returned `RIGOL TECHNOLOGIES`, `MHO984`, and software prefix
`00.01.00`; the exact serial-bearing response remains private. This prefix does
not identify a complete firmware release or the loaded native bandwidth policy.
The final capture contains 44 complete frames: 11 DHCP, 19 IPv6 local control,
four ARP and ten TCP. Independent reconstruction verified the six-byte request,
50-byte response and complete TCP close. No extra application exchange or
unexpected external destination appeared in this capture.

The recorder and DHCP helper both exited zero. Recorder statistics were
44 captured, 44 filter-received and zero kernel drops. No namespace process or
listener remained; the ordinary TCP TIME_WAIT entry was recorded rather than
claimed absent. The namespace remains configured and isolated, with forwarding
disabled and no default route. The root namespace retains its management route.
No ADB, native-policy, UI or RF acceptance follows from this checkpoint.

Completed evidence is `out/rf/linux-link-02.toml`
(`25a2df7e69ec135cbf63a4c8f808734cce51cb9ff03b001466b51a7abd8dcc02`).
The immutable raw capture SHA-256 is
`598ebf05693cb723d259a64fa167f8c581a136b9a8283b13d439cac71f08da00`.
Independent completed review is
`out/rf/linux-link-02-independent-20261002T200100Z.toml`
(`23b76cc1776810c50424023975bcd73351b1b3e468f70eccb76ba8fc0d112fdb`).
The raw timestamps belong to the recorded Linux host clock domain; they are not
silently treated as synchronized workstation timestamps.

A conventional Linux ADB observation is prepared and independently accepted.
A host-only loopback control established a foreground server, loopback-only
listener and graceful SIGINT retirement. The supported discovery switches are
explicitly disabled. A numeric listen hostname was rejected by this ADB build;
the successful control uses `localhost`. Both outcomes remain preserved.
The ordinary `exec-out` client does not convey remote exit status reliably, so
zero-output remote checks require explicit completion markers.

The prepared observation starts full capture before one ADB connection, reads
UID first, and compares the exact accepted stock boot/process, APK/native mapping
and complete protected corpus. It requests one UI image and, only after those
gates, uses the already present fixed 16-byte stock policy reader. It introduces
no root restart, reboot, source command, RF sample or new warm-up claim. The
capture health token is created only after live recorder readiness. Cleanup
binds process ownership, retires the server and retains actual drop statistics;
uncertain retirement stops the run without an automatic reconnect.

Preparation is `out/rf/linux-stock-preparation-01.toml`
(`4387387b68906402e44eff8b71223db4218b0d3384a6bb5fc6047d4dc84b2307`),
coordinator preparation is `out/rf/linux-stock-controller-preparation-01.toml`
(`b08c80c989082ada362156c0d5bc4a53ae2812611025ba308fd8f9014772a240`),
and the concrete invocation is `out/rf/linux-stock-invocation-01.toml`
(`61abace532eb0d54b00b6786af5985c950aef79e203f2f28f619c4828dc914c8`).
Independent preparation review is
`out/rf/linux-stock-preparation-independent-01.toml`
(`c6c75f93a3faaa295d1f28e714502daad5fb8c1716a218886618e72c037fa446`).
These seals establish readiness for one observation, not current specimen or RF
acceptance. The RF source remains on its existing workstation serial connection;
no USB relocation is required for the proposed continuation.

The one Linux observation reached ADB with UID 0 and completed the stock checks.
The actual APK and embedded native bytes matched the preserved stock hashes;
the original boot/process and load mapping remained in place. All 32 accepted
corpus files matched before and after. The existing reader returned stock raw
and effective bandwidth values `17/17` within its fixed 16-byte read budget.
The single screenshot shows the normal scope UI with CH1 active. Its displayed
100 MHz measurement is supplementary and does not qualify a RAW waveform.
No source command, RF sample, root restart, reboot or new warm-up occurred.

The coordinator result remains `stopped`, exit one: a process ownership read
raced with the observer's normal exit. The preserved observer was reaped with
exit zero, and its guest reader and owned ADB server retired with exit zero.
Cleanup reported no issue. The recorder closed gracefully with 34,485 captured,
34,485 filter-received and zero kernel-dropped packets. The namespace remains
isolated. This distinction is retained rather than relabeling the supervisor
result or repeating the physical observation.

Actual evidence is `out/rf/linux-stock-actual-01.toml`
(`b72b6ceb13b8c7cc0986fbac2b97b54ba3a22ced622e0c87babcfa3a0f65bf27`).
Raw capture SHA-256 is
`3758fd84612b3fa8a0c5f10b8c900e63307d6352d3c545ed1d559ad7b539fbd7`.
Screenshot SHA-256 is
`92140d7bd853a010343d719ef4af62ee3354e75e22f2c27a4ec1c9cce9b9cfe1`.
Independent evaluation of the completed evidence is the next decision boundary.
