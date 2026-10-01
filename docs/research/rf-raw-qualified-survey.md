# Raw-qualified current-policy RF-chain survey

2026-10-01. The separately frozen
[raw-qualified protocol](rf-raw-qualified-survey-protocol.md) completed all twelve
visits and all sixty fresh RAW records. Every record passed the admitted sampled
receive criteria. This extends physical observation of the connected
source/cable/CH1 chain through the nominal 1.1 GHz command under the installed
software policy.

The [earlier survey](rf-current-survey.md) stopped at the built-in 600 MHz
frequency gate. Its records and conclusion remain immutable. The
[discriminator](rf-frequency-diagnostic.md) justified a new experiment using
supplied raw samples for qualification; no threshold was relaxed within a run.

The commanded visits were `100, 400, 600, 800, 900, 950, 975, 1000, 1025,
1050, 1100, 100` MHz, with five separate RUN/wait/STOP acquisitions at each.
CH1 remained internally terminated at 50 ohms with DC coupling, 1x ratio, zero
offset and FULL bandwidth. The temporary acquisition profile was 50 mV/div,
1 microsecond/div, 100k memory and reported 4 GSa/s. Each RAW ASCII record had
100,000 voltages and a 250 ps interval. ASCII voltages were retained directly.

The source received exactly one factory point command per visit at raw power
code zero. All twelve retained requests and driver-accepted byte sequences
match their expected nine-byte frames. These transport records provide no
serial device acknowledgement. The source ended at the planned 100 MHz return
visit; no retry or extra cleanup command was sent.

The committed [receive library](../../packages/mho-rf/README.md), introduced in
`0dba44e`, qualified each record online. Its explicit default profile fingerprint
was `25401a53b0b9b9a14581f740b5d8cf665ccfb2b37c962d925c77b46389409358`.
All sixty independent offline recomputations match the complete retained online
results. Each preamble/data/preamble file also matches its exact socket response,
with distinct waveform-query sequence numbers and recorded RUN/STOP transitions.
No record or scheduled visit is missing or censored in this acquisition.

The fresh full Layer Two capture retained 91,848 frames in 91,566,306 bytes.
The recorder exited gracefully with zero reported kernel drops. Reconstructed
TCP streams match all 610 retained request files (9,990 bytes) and 458 response
files (84,010,572 bytes), including both connection termination directions.
These are stored-frame, process and transcript observations; they do not prove
that every frame on the wire was captured.

Acquisition began at 22:58:35 UTC and all visits completed at 23:04:58 UTC.
At 23:05:06 UTC, readbacks confirmed the original scope and export settings were
restored: 500 mV/div, 10 ns/div, 10k memory, reported 4 GSa/s, running acquisition,
and the original normal/WORD waveform export extent. The temporary host address
was removed, the lease helper stopped, and host isolation checks passed. Wiring,
firmware, capability policy, entitlements and calibration were unchanged. These
are SCPI and host observations; no live camera UI witness was available.

The private acquisition root is
`out/rf/raw-qualified-survey-20261001T224500Z`, with a separate manifest at the
same name plus `.toml`. Its verified manifest SHA-256 is
`9ca142a9fafc0d810469e22aa2ecd20f9ea72318f8203c5a61ad0029673d4ec9`
over 1,710 artifacts and 281,077,070 bytes. The capture SHA-256 is
`a2b1cc3b4192c94ff3ad4b956ef7ca262e57ceeb74b2eb9f3a822a2527f69965`.
Unit identity and host/interface details remain in local evidence.

Final command-centered estimation follows this seal in a separate derived root.
Receive acceptance establishes a dominant sampled component near each command;
it does not establish physical carrier origin, calibrated amplitude or valid
final fits. Source/cable response, clock uncertainty, folded harmonics and the
missing matched software-policy comparison remain explicit limits.
