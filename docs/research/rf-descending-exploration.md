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
