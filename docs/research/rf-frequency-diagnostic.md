# 600 MHz receive-frequency discriminator

2026-10-01. The separately [frozen experiment](rf-frequency-diagnostic-protocol.md)
retained three fresh raw records with the source left at its previous commanded
600 MHz. No new source command was sent. The experiment completed and restored
the original scope acquisition/export settings and host isolation.

## Direct observations

| Experiment | Timebase | Built-in SCPI frequency |
| --- | --- | --- |
| Earlier partial survey | 1 microsecond/div | 571.43 MHz |
| This discriminator, before raw exports | 1 microsecond/div | 666.67 MHz |
| This discriminator, after raw exports | 10 ns/div | 625.00 MHz |

The paired measurements in this experiment used the same 50 mV/div scale,
reported 4 GSa/s, CH1 with internal 50 ohms, DC, 1x, zero offset and FULL
bandwidth. Vpp was 279.39 mV at 1 microsecond/div and 271.86 mV at 10 ns/div.
Neither a serial acknowledgement nor external frequency reference was acquired.
These observations distinguish the prior survey readback from this run; they
do not establish a specific frequency-measurement algorithm.

All three raw exports retained matching preambles, 100,000 finite ASCII voltages
and 250 ps interval with separate RUN/settle/STOP cycles. The typed waveform CLI
qualified each record independently, and file bytes exactly match the retained
raw socket responses. Numerical interpretation follows only after sealing.

## Preservation and final state

The capture retained 4,776 frames and reported 4,776 packets received by the
filter with zero kernel drops. Recorder and lease-helper termination were
graceful with exit zero. All 132 request files and 102 response files matched
reconstructed SCPI streams, including 4,201,142 response bytes and FIN closure.
A capture-consistent transcript does not independently prove wire completeness.

Original scope and export readbacks matched after restoration: 500 mV/div,
10 ns/div, 10k memory, running acquisition and NORMAL/WORD 1,000-point export.
The temporary host address was removed, helper stopped and isolation rechecked.
Source remains powered, connected and at the previous commanded 600 MHz.
Wiring, firmware, entitlements and calibration were unchanged.

The private run `frequency-diagnostic-20261001T223700Z` contains 310 artifacts,
29,860,918 bytes. Its verified manifest SHA-256 is
`171f5b92b6643f863ddd5bf989785dd80053019c90699dee9c27a38c718ec443`.
Private endpoint and unit identity stay with local evidence. The previous
failed survey remains sealed and unchanged.
