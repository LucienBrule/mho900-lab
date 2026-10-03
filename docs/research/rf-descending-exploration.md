# Six GHz descending exploratory response

The operator requested a broad descending survey under the original and derived
software selections. This is a new exploratory experiment. The earlier failed
stock return control and the missing original comparison arms remain preserved.
These records do not fill or revise the frozen seventy-five-slot comparison.

Each arm uses the existing source-to-CH1 coax path, internal 50 ohm termination,
DC coupling, one-times probe ratio, zero offset, FULL bandwidth and normal
acquisition. The planned record profile is 50 mV/div, 100,000 RAW ASCII points
and a reported 4 GSa/s. Original ordinary, waveform-export and run settings are
saved and restored. The source uses raw power code zero throughout; that code
is not a calibrated output level.

The source command list, in MHz, is:

```text
6000, 5500, 5000, 4500, 4000, 3600, 3200, 3000,
2500, 2000, 1800, 1600, 1400, 1200, 1100, 1000,
950, 900, 850, 800, 700, 600, 400, 100
```

Every listed factory frame must pass the existing encoder, including its CR
delimiter exclusion, before a source port is opened. Each visit has one source
command and three separate RUN, wait, STOP acquisition positions. There is no
automatic command retry or replacement record. The planned final visit returns
the source to 100 MHz. After an early stopped prefix, a separate one-shot
100 MHz return is permitted only if the latest source attempt finalized with
all nine bytes accepted, no transport issue and a successful close, and fresh
registry identity still matches. No return is attempted after source ambiguity,
partial output, an unfinished intent, changed identity or an already attempted
final 100 MHz visit. Cleanup never supplies a missing visit or repeats an
ambiguous write. Its result, or the last held source command, remains explicit.

## Sampled observations

ASCII values are retained directly in volts. Adjacent preambles, exact original
response bytes, sample interval, record geometry and query provenance accompany
every complete record. The common amplitude metric is whole-record demeaned
population AC RMS. Finite, correctly framed, nonoverloaded weak or constant
records are valid exploratory outcomes. A minimum amplitude, a peak near the
commanded frequency or a return-amplitude threshold does not gate continuation.
Framing, nonfinite values, overload, software identity, protected-material,
capture, lease or ownership failures preserve the stopped prefix.

Under uniform sampling at the reported 4 GSa/s, the first Nyquist interval ends
at 2 GHz. The principal folded-frequency predictions include:

| Source command (GHz) | Principal alias (GHz) |
| --- | --- |
| 6.0 | 2.0 |
| 5.5 | 1.5 |
| 5.0 | 1.0 |
| 4.5 | 0.5 |
| 4.0 | 0.0 |
| 3.6 | 0.4 |
| 3.2 | 0.8 |
| 3.0 | 1.0 |
| 2.5 | 1.5 |
| 2.0 | 2.0 |

These are predictions under the reported clock, not independent identification
of a physical carrier. DC and Nyquist cases depend on sampling phase; zero AC
at an exact folding point need not mean the source or analog path is silent.
Source harmonics and other components can also fold. Results therefore report
the commanded frequency separately from the observed sampled spectrum and RMS.

## Software and evidence boundaries

The original arm must establish the original APK-backed native selection and
stock capability values. The derived arm must establish the exact previously
approved standalone native bytes, mapping and derived capability values after
one normal reboot. Stock restoration removes only the file whose introduction
is proven, followed by one normal reboot and stock verification. The signed
APK, firmware images, option/license material and calibration remain preserved.

Each actual arm has a fresh full Layer Two capture in the existing isolated
Linux namespace. Its DHCP service supplies only the specimen's private lease,
without a gateway or DNS. Recorded owned processes, graceful capture closure,
drop statistics and retirement evidence are retained. The Mac controls only
the existing USB serial source; its routing table is not a bench dependency.

Stock results are sealed and committed before the derived transition. Every
result uses the same numerical metric, with no exclusion of inconvenient
records or substitution of fitted peak amplitude for RMS. Arm differences are
descriptive until source/path and temporal repeatability support attribution.
This survey can reveal where a narrower follow-up is useful. It does not by
itself establish a calibrated analog bandwidth or a physical six GHz waveform.

## Recorder invocation checkpoint

The first current-software collector launch stopped before contact. Its outer
supervisor supplied the recorder duration as a positional argument; the pinned
recorder requires `--duration`. Click rejected that command before its callback,
so no capture, DHCP helper, ADB server, specimen connection or source write
started. A subsequent host-only check found no namespace processes or listeners.
The stopped run is preserved separately as
`out/rf/descending-native-current-stopped-01.toml`.

The narrow remedy adds the required recorder option. The DHCP wrapper still
receives only its output argument. Pure checks exercise the actual pinned Click
commands with their physical callbacks replaced by recording spies. The original
preparation remains immutable; a fresh run identity and exact amended source
pin precede another launch. This checkpoint supplies no software or RF result.

The corrected collector armed its capture and reached an ADB connection. It
then stopped because bootstrap servicing had consumed the capture prefix before
the lifecycle decoder was constructed. That decoder received later packet bytes
where it required a PCAP header. No policy read, native change or RF source
command followed. The captured connection is preserved; this is a host stream
handoff failure rather than evidence that ADB was unavailable.

The second stopped run, `out/rf/descending-native-current-stopped-02.toml`,
retains twelve captured frames, zero reported kernel drops and graceful recorder
and DHCP exits. Owned ADB retirement precedes DHCP and capture retirement; a
fresh host check records no remaining namespace processes or listeners. The
handoff remedy gives the lifecycle its own forward capture cursor while retaining
the outer wire validator's independent cursor and all packet acceptance rules.

The next collector reached UID zero and retained current package, maps, APK and
full protected-corpus bytes, then stopped on a literal missing-file result for
the expected enforcement-status path. Its stopped seal is
`out/rf/descending-native-current-stopped-03.toml`. The subsequent narrow
observation distinguishes a readable zero, a readable one and confirmed path
absence. Absence does not establish that enforcement is disabled. Existing
unreadable or linked paths, command failures and malformed replies remain errors.
The exact observation bytes must stay unchanged across the current check and
native transition. No policy setting is changed. No native policy reader or RF
source command occurred in this stopped run; owned helpers again retired.

The fourth collector passed the fresh stock software snapshot and then rejected
normal ADB transfer progress printed on stderr, despite a zero return code.
The policy-reader file had been transferred, but no reader was launched. Its
private stage is quarantined. The stopped inventory,
`out/rf/descending-native-current-stopped-04.toml`, retains the original stop and
retirement uncertainty: the original ADB wait status was not recorded. Later
process and active-endpoint absence do not supply that missing exit status.
Recorded capture and DHCP owners were subsequently closed gracefully, with
29,992 captured frames and zero reported kernel drops.

The remedy recognizes only the exact successful single-file transfer diagnostic,
bound to the source path and byte count. Owner, mode, size and byte roundtrip
checks still precede reader execution. Owned-server retirement now records the
actual wait result first and, after a proved zero exit, observes socket closure
for at most five seconds while servicing the remaining capture and lease owners.
A fresh collector identity and pinned runtime precede execution. No native
selection or RF source command occurred in the fourth stopped run.

The fifth collector ran the stock policy reader and reached the unchanged
fixed-size observation validator. Independent replay establishes stock raw and
effective selection 17/17 in the same process and boot epoch. Its lifecycle
archive contains the five expected files as `./argv`, `./pid`, `./start.stat`,
`./go` and `./exit`. The collector's generic corpus reader preserved those
prefixes while its lifecycle membership check expected bare names. The raw
archive is preserved in `out/rf/descending-native-current-stopped-05.toml`.

The reader exited zero, its process absence and helper removal were recorded,
and owned server, DHCP and capture retirement completed. No UI witness, final
snapshot, native selection or RF source command followed. A separate lifecycle
archive parser now handles that exact flat archive grammar; protected-corpus
member naming and all reader identity, argument, exit and absence checks remain
unchanged. This resolves a host evidence-format seam, not a stock policy failure.

The fresh current-software run then completed. Before and final snapshots retain
the exact stock signed APK, APK-backed native mapping, process and boot epoch,
identity/status replies and complete protected corpus. Two fixed-size samples
establish raw and effective stock selection 17/17. The reviewed screenshot shows
the normal oscilloscope UI. The capture contains 60,321 frames, matching final
capture statistics with zero reported kernel drops, and owned helpers retired
with recorded zero exits. This establishes the current stock software state;
it contains no descending RF records.

The two-arm survey retains a finite completion budget and the full reserves for
both native transitions and final stock restoration. A separate timing fixture
extends that selected budget by one hour after the collector remedies. Per-leg
durations, the 1,801-second serviced warm-up, single-reboot rule, 7,320-second
pre-deployment reserve and captured lease expiry remain unchanged. Earlier
fixtures and stopped runs remain immutable.

## Completed stock survey

The stock arm completed all twenty-four source visits and seventy-two records,
with three records per visit and no retries. Every record is finite, correctly
framed and within the planned headroom; none is missing, partial or invalid.
The reported sample rate is 4 GSa/s throughout. The source's final planned
command is 100 MHz, and the saved ordinary, export and run settings were restored.
The capture contains 41,179 frames, matching its final received count with zero
reported kernel drops. Recorded owned helpers exited and the isolated namespace
retains only its connected bench route, with no active management sockets.

The following values are whole-record population AC RMS, averaged across the
three records. They describe the source, cable and sampled instrument chain.

| Source command | Stock mean AC RMS | Largest sampled bin |
| --- | ---: | ---: |
| 6 GHz | 0.902 mV | 100 MHz |
| 1.6 GHz | 1.055 mV | 75 MHz |
| 1.4 GHz | 2.000 mV | 1,400.04 MHz |
| 1.2 GHz | 29.970 mV | 1,200.04 MHz |
| 1.1 GHz | 66.294 mV | 1,100.04 MHz |
| 1 GHz | 89.943 mV | 1,000.04 MHz |
| 800 MHz | 99.363 mV | 800 MHz |
| 100 MHz | 110.316 mV | 100 MHz |

This establishes substantial sampled reception at the nominal 1 GHz command
under stock selection. The higher commands retain small residual responses;
from 6 GHz through 1.6 GHz, the largest bins are near 75 or 100 MHz, rather than
the hypothetical carrier or its principal alias. The 6 GHz record therefore
does not establish reception of a physical 6 GHz fundamental. A serial write
does not independently verify the source's RF output. These data also do not
establish a calibrated analog bandwidth or a derived-selection benefit.

The immutable actual inventory is `out/rf/descending-stock03-actual-01.toml`
(`8c48d9710d332c58a694421702f4401b7960efd10288b8593c209691ba7af12c`).
The separately sealed numerical inventory is
`out/rf/descending-stock03-analysis-01.toml`
(`2abc07db9e6b774102442580104c2afee23a6aa6c3d3db16cdfa3dbf6599922a`),
with every planned position and original-voltage result retained. The complete
frequency table and execution witness are preserved in
`out/rf/descending-stock03-reduction-execution-01.toml`
(`694905d44fa278deecb5724481d0231506820ecd7a8c7308ed3d085a849db07d`).
The independent acquisition review is
`out/rf/descending-stock03-actual-independent-01.toml`
(`346c4ac197f935bcdc1b1a18291c4258c9e3bde3f39d10ad00d18d77ff8c1a57`).
It reconstructs all 1,469 SCPI requests and their responses from the capture,
binds the three stock metadata checks, checks restoration and recorded helper
retirement, and independently recomputes every RAW scalar and group statistic.
The stock metadata checks preserve the admitted process and mappings; they do
not constitute a new backing-file hash acquisition at every RF record.

The first derived launch stopped during host bootstrap, before ADB startup or
any native change, reboot or source command. A dynamically constructed health
model retained the earlier deadline cap. Its capture and DHCP owners were
identified by PID, birth, arguments and namespace, then retired through pidfds.
Their recorded child closures and the empty capture's zero drop statistics are
preserved. The original supervisor wait statuses are unavailable and remain
explicitly unknown. The stopped inventory is
`out/rf/descending-native-derived-stopped-01.toml`
(`e788da610c6433661bdeee813f8d427487896fa2c2178e235a659fe1b463da39`).

A separately admitted correction changes only that deadline validation bound
and binds a fresh run identity. Pure controls construct the exact concrete
health model with labelled synthetic owners; the original rejects the selected
deadline and the corrected model accepts it. Other guards and warm-up and
restoration reserves remain unchanged. Independent review
`out/rf/descending-health-cap-independent-01.toml`
(`338d014f5e3135f803ce9a891fb64872fef78f4d71832240cfff05e4feb39584`)
accepts the fresh configuration and host-only validation. It acknowledges the
late constructor check missed by the earlier conditional preparation review.
This correction supplies no physical derived result.

## Interrupted derived boot observation

The second derived transition recorded the exact sidecar introduction and issued
one normal reboot request. Its boot observation stopped on a peer-origin IPv6
packet whose base Next Header is Hop-by-Hop, rather than directly ICMPv6. The
retained packet decodes as a link-local multicast-listener report. This is a
capture-classification limitation; it is not evidence of external reachability
or a failed RF channel. [RFC 3810](https://www.rfc-editor.org/rfc/rfc3810.html)
describes the Hop-by-Hop Router Alert used by these local reports.

The reboot CLI was interrupted with recorded return code -15 and remains
unproven as a completed command. Postboot software, UI, policy and RF acceptance
are absent. The capture does retain subsequent DHCP traffic; its independent
interpretation and a fresh current-epoch check are separate requirements.
The owned ADB server was reaped with exit zero. The four remaining capture and
DHCP owners were positively identified and gracefully retired; child closures
are zero, while original supervisor wait statuses are explicitly unavailable.
The final capture reports 87,160 captured and received packets with zero kernel
drops. Host observations retain only the isolated connected route, forwarding
disabled and no remaining namespace processes or sockets.

The complete stopped inventory is
`out/rf/descending-native-derived-stopped-02.toml`
(`3b526cdfa84cbe0fed1b3bddf36f9b0c29b6d4b694eb6a563a23ebe760f27681`).
Separately admitted postboot tasking permits a narrowly classified local report
and observation of the already-introduced derived selection. It has no native
transaction or reboot route. It retains a bounded observation period, full
software and corpus checks, serviced warm-up and final stock restoration.
It cannot turn the interrupted transition into a completed result.

Independent review of the complete stopped capture confirms nine checksum-valid
local reports: five link-local and four unspecified IPv6 sources. All other
frames pass the existing classifier. It also reconstructs one reboot service
request followed by a fresh paired 86,400-second DHCP lease, with no gateway or
DNS options and no later release or decline. Review inventory
`out/rf/descending-derived02-stop-independent-01.toml`
(`a7476fcb2b4ac7c5d71e8d56631618755c5be9487b07f193b09c25f565989da5`)
preserves the interrupted command and missing software acceptance.

The separate postboot fixture accepts only those witnessed report structures,
checks their lengths and checksums, and rejects unrelated extensions. Its
controller has no native transaction route and rejects normal reboot requests.
Independent preparation review
`out/rf/descending-postboot-independent-preparation-01.toml`
(`e7222e40da173e51873d31d8e4f2df94b18e08b9f4b0046d066cd92455eacabe`)
accepts the actual packet controls, copied configuration pins and the host-only
validation. Fresh binding inventory
`out/rf/descending-postboot-bindings-01.toml`
(`6648103d9accaacc719f9ffe839d5a02b0a80d80f77bf7bf8ccfde3b79d9ac3c`)
retains the current lease and original introduction lineage. It supplies no
future process, UI or policy result.

This present-state observation has its own 3,000-second cap and requires 6,320
seconds remaining at entry. While it runs, 4,320 seconds remain reserved for
the unchanged survey, final stock restoration and cleanup. The original
deployment and restoration limits remain unchanged. The observation does not
retry the interrupted native transition.
