# RF bench readiness and current-policy pilot

2026-10-01. This reconciles the original preparation graph with retained arrival,
USB-control and first-signal evidence. Detailed inventory and purchase material
remain private under ignored `out/rf/`.

The available minimum path is the delivered touch-screen synthesizer, a direct
nominal 50-ohm SMA-to-BNC cable, and CH1's internal 50-ohm termination. USB control
of the stock source controller has an independent screen witness. Scope SCPI
readback and a display export establish a 100 MHz signal, normal acquisition,
4 GSa/s and an unclipped trace at the pilot settings. These are qualifications
for further integration work, not calibrated source specifications.

The delivered source has unknown manufacturer and calibration provenance. Its
screen identifies MAX2870 while the photographed RF IC has a MAX2871-family
marking. The supplied leaflet documents touch controls and startup modes. A
power cycle restored active point output; the same source subsequently accepted
the recovered factory serial protocol. Firmware equality with the public image
is not established. MCLK remains unused and electrically unqualified.

The operator reported receipt of nominal 50-ohm SMA/BNC cables and adapters.
Individual adapter markings, cable loss and RF mismatch have not been measured.
No calibrated power sensor, reference receiver, independent spectrum measurement
or characterized attenuator has been established for this bench. Ordered SDRs
and microcontroller boards are optional improvements; their availability and
qualification are not assumed.

## Preparation disposition

Use a staged experiment. First validate raw acquisition-memory export, improved
vertical utilization and fundamental estimation at 100 MHz. Then perform a
separately frozen, bounded frequency survey under the existing installed policy.
This survey describes the source, cable and scope together. It cannot determine
absolute scope bandwidth or isolate a software-policy effect.

The observed source waveform has substantial odd harmonics, so fundamental
amplitude, residuals and aliasing diagnostics replace peak-to-peak voltage as
the primary reduction. A common 100 MHz anchor is available from the source;
the original 10 MHz anchor is below its advertised range. Do not substitute an
independent clock without characterizing its amplitude relation.

The provisional later policy comparison retains matched stock/derived/stock
arms, the same source command and cable at each frequency, repeated anchors,
and actual software hash/policy observations. Its hypotheses remain increased
high-frequency response, no resolved change, or decreased response. Acquisition
failure and inconsistent controls are separate outcomes. The comparison gate
remains open: current-policy data alone cannot close it.

## Integration protocol

The current operator-authorized three-hour session covers source point commands,
ordinary scope acquisition settings, raw exports and analysis. Preserve the
existing connection, source firmware, specimen firmware, options and calibration.
Use isolated addressing with no gateway, DNS, forwarding or NAT; begin complete
packet capture before adding the host address and retain graceful drop statistics.

At the unchanged 100 MHz source setting, record scope/export settings, improve
CH1's vertical scale to 50 mV/div, use a documented raw-memory read while stopped,
retain preambles and complete ASCII voltage records, then restore settings and
running acquisition. Stop on transport or recorder failure, unexpected settings,
invalid metadata or input-range failure. A failed pilot is preserved and evaluated
before any new trial is admitted. No source frequency command is needed for this
first integration question.

Warm-up and ambient temperature are incompletely witnessed. Record elapsed time
from observed powered operation and repeated anchors; this does not substitute
for a calibrated thermal record. Use a fixed raw power code in a future survey,
allow explicit settling, and validate the received signal at each point.

## Open measurement limits

Raw-memory export and its restoration are the immediate integration questions.
Delivered fundamental level, cable loss, RF mismatch, source harmonics and
high-frequency aliasing remain measurement limitations. A subsequent matched
policy experiment needs verified software arms and explicit transition/reboot
procedures. A corrected absolute -3 dB claim additionally needs a characterized
reference-plane source and uncertainty budget.

Evidence: [source control](rf-source-factory-trial.md),
[first signal](rf-first-signal.md), [display export](rf-display-waveform.md),
and the [RF response roadmap](rf-response-roadmap.md).
