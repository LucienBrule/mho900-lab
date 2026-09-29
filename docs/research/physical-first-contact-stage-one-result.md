# Stage One result: stable stock UI with unanswered DHCP

The as-delivered MHO984 reached a stable oscilloscope UI during the first
controlled boot under custody. The operator reported RIGOL logo, spinner, then
main UI with Run/Stop illuminated and Auto blinking, followed by stable idle UI.
No configuration-changing prompt or unexpected reboot was reported. No active
management request or network response was sent by the investigation.

This is an observed boot result, not proof of a particular firmware, APK hash,
installed option set or acquisition performance. The physical front label reads
MHO984. Software model, firmware, options and displayed clock were not captured.
No probes or external signals were connected. The DHCP vendor class
`android-dhcp-7.1.2` is a packet field, not independent firmware identification.

## Physical transitions and timing

The operator separately confirmed Ethernet connection while the instrument was
unpowered, USB-C power connection, and a front power-key press. USB-B remained
disconnected and the front USB host port remained empty. The power indicator
changed green to red while the display remained dark; its color meaning was not
assumed. Section 5.3 of the pinned MHO900 QuickGuide supplied the documented
power-key step. No menu setting was changed to enable automatic startup.

Times below use UTC on 2026-09-29. Local time is PDT on 2026-09-28, seven hours
earlier. Operator physical actions and UI transitions have confirmation times,
not exact event timestamps; an exact button-to-UI boot duration is unavailable.

| Observation | UTC | Basis |
|---|---|---|
| Ethernet-only connection confirmed | Recorded before 01:37:12 host check | Operator confirmation; no carrier or packets |
| USB-C power-only connection confirmed | Recorded after 01:44:00 host check | Explicit clarification; screen later reported dark |
| First carrier | 01:46:37 | One-second host polling |
| Carrier inactive again | 01:46:48 | Host polling |
| Carrier active again | 01:46:52 | Host polling; no UI reboot inferred |
| First peer frame | 01:46:52.818415 | Pcap timestamp |
| First DHCP Discover | 01:47:13.808156 | Pcap timestamp |
| Main UI report recorded | 01:49:32.573889 | Operator: logo, spinner, oscilloscope UI |
| Stable UI report recorded | 01:50:39 | Operator confirmation |
| Last captured frame | 01:53:23.489534 | Pcap timestamp |
| Recorder frozen for sealing | 01:54:35.169195 | Host process control |

The first packet was approximately 15.8 seconds after the first carrier sample;
the first DHCP request was approximately 36.8 seconds after that sample. These
are network timings, not measured application startup durations.

## Passive network result

The complete capture contains 29 full-length Ethernet frames from one peer MAC,
attributed to the scope by the isolated single-peer connection. Exact MAC,
link-local address and DHCP hostname remain in the private evidence/report.

| Captured traffic | Count |
|---|---:|
| DHCP Discover, UDP 68 to 67 | 9 |
| ICMPv6 router solicitation | 10 |
| ICMPv6 neighbor solicitation | 2 |
| ICMPv6 multicast listener report | 8 |
| Host-originated Ethernet frames | 0 |

The scope used an IPv6 link-local address after duplicate-address discovery.
Captured IPv4 packets used source `0.0.0.0` and broadcast DHCP destination; no
lease reply, ARP-based IPv4 selection, DNS, mDNS, SSDP or other EtherType appeared
in the recorded window. These are scoped capture observations, not claims that
those protocols or services are absent from the instrument. No address was tested
with an active connection. Ethernet negotiated 100baseTX full duplex as observed
by the host.

The requested minimum five-minute unanswered-DHCP window was completed. Host
recorder cleanup extended recording to about seven minutes twenty-one seconds
after the first DHCP request. The normal UI therefore did not require a DHCP
response during this observation. No acquisition function was exercised.

## Evidence and capture limits

The continuous raw recorder began before physical connection. No capture restart,
packet injection or change of the physical setup was used to repair observation.
Full Ethernet headers and a 524288-byte snapshot length were retained without a
restrictive BPF filter. A separate offline parser and tcpdump agreed on 29 full
records; original raw file and sealed copy have the same SHA-256.

Two host-tool limitations are retained explicitly:

- The recorder's `--print` output buffered despite `-U`. A separate line-buffered
  decoder read the existing raw file. Native tcpdump rejected stdin pcap input;
  the already installed alternative decoder accepted it. Final text was also
  regenerated from the sealed pcap. The earlier file-only control proved decode
  content, not live stdout latency.
- The background recorder did not terminate on SIGINT or SIGTERM. It was frozen,
  its complete flushed records copied and fsynced, and then forcibly stopped.
  Kernel-drop statistics are unavailable. Completeness of stored frames is
  established; completeness of every frame on the wire is not independently
  established. The carrier watcher stopped before this cleanup interval.

The redacted [result manifest](../../experiments/physical-first-contact/first-boot-result.toml)
binds the private raw capture and 64-artifact boot-phase manifest. Earlier host,
Ethernet-only and power-connected phase hashes were reverified unchanged. Private
raw evidence remains under the stable local run; it is not committed to source.
The full local report includes specimen identifiers, exact artifact paths and
hashes. There is no claim that normal stock boot leaves storage unchanged: future
filesystem acquisition will be post-first-controlled-boot evidence.

## Stage Two recommendation and current host state

Stop here for operator review. Stage Two has not been admitted or executed.
The next bounded step should be an explicitly authorized, isolated DHCP lease:
keep forwarding/sharing disabled, advertise no router or external DNS, start a
new verified capture before introducing the server, and preserve the lease
exchange. DHCP itself may cause the instrument to persist lease state; do not
represent it as guaranteed write-free.

After that address-only checkpoint, separately authorize narrowly ordered
identity/provenance reads through the chosen management interfaces. Establish
actual firmware and filesystem state before treating the recovered `.26`
calibration behavior as this unit's behavior. Preserve per-unit calibration and
storage evidence before adjustments, updates or reset operations. No USB-B or
USB storage phase is implied by this recommendation.

All recorder, watcher and decoder processes are stopped, and capture-related
promiscuity has cleared. The scope remains powered and Ethernet-connected by the
last operator report. The host interface remains up with its IPv4 and IPv6
service configurations inactive; its normal Internet route is elsewhere.
Forwarding and sharing remain disabled. Restoration has not been executed while
the specimen remains connected. The private restoration record preserves the
original service and full baseline and requires explicit specimen disconnection
before restoring the host's DHCP/link-local behavior.
