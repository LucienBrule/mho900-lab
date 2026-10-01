# Current-policy RF survey: bounded partial acquisition

2026-10-01. The [frozen survey](rf-current-survey-protocol.md) stopped at its
predeclared frequency qualification gate. It retained five fresh RAW ASCII
records at each of 100 and 400 MHz. At the commanded 600 MHz visit, the scope's
SCPI frequency measurement returned 571.43 MHz, outside the required 1% window.
No 600 MHz raw record was requested, and no remaining frequency was attempted.
The original experiment was preserved rather than extended after the failure.

## Observed prefix and stop

| Commanded source frequency | SCPI frequency | Records retained | Outcome |
| --- | --- | --- | --- |
| 100 MHz | 100.00 MHz | 5 × 100,000 points | Receive and raw metadata qualification passed |
| 400 MHz | 400.00 MHz | 5 × 100,000 points | Receive and raw metadata qualification passed |
| 600 MHz | 571.43 MHz | 0 | Frequency guard failed before raw export |
| Remaining visits, including final 100 MHz | Unobserved | 0 | Not executed |

Each source visit used one nine-byte factory point command at raw power code
zero. USB ancestry and absence of another serial owner were checked per visit.
The sender reported transport completion without device acknowledgement; the
scope's independent measurements supplied the receive observations. At the
failed visit, Vpp was 279.55 mV, with extrema −145.37 and +134.43 mV. The received
level passed the declared range checks. Frequency remained the stop condition.

All ten retained records have matching before/after preamble bytes, exactly
100,000 finite ASCII voltages, 250 ps sample interval and reported 4 GSa/s.
The new [typed waveform boundary](../../packages/mho-waveform/README.md)
independently qualified the files and confirmed their bytes match the retained
socket responses. Each record followed a separate RUN, settling interval and
STOP; repeated export of unchanged stopped memory was not used as repetition.

## Preservation and final state

The full Layer Two capture retained 15,616 frames. The recorder exited normally
after SIGINT and reported 15,616 packets received by the filter and zero kernel
drops. Reconstructed SCPI streams matched all 186 request files and 143 response
files, including 14,002,268 response bytes. These facts establish recorder and
transcript consistency, not an independently complete observation of every
packet on the wire.

The scope's original acquisition and waveform-export settings were restored
and read back: 500 mV/div, 10 ns/div, 10k memory, running acquisition, CH1 with
internal 50 ohms, DC, 1x, zero offset and FULL bandwidth. Original NORMAL/WORD
export with 1,000 points was restored. The temporary host address was removed,
the one-client lease helper stopped, and host isolation was rechecked. Wiring,
firmware, calibration and entitlements were unchanged by this experiment.

Because the survey stopped before its final anchor, the source remains powered
and connected at the last commanded 600 MHz. There was no extra serial cleanup
command. Its actual output frequency has not yet been independently resolved.

The private acquisition is sealed under run identity
`current-survey-20261001T223000Z`: 490 artifacts, 61,318,507 bytes; manifest
SHA-256 `ab281cf449af856e37a125642216f98a740053354111f0e04c9058372642763c`.
Capture SHA-256:
`52018a036c65e623f515bb415139c45c0bb9d78a42b73d931186e5707c686b2e`.
Private unit identifiers, endpoint addresses and host inventories stay with
local evidence. Subsequent analysis must use a separate derived run.

## Decision to resolve

This is a valid negative result for the frozen survey's receive gate. It does
not demonstrate a source-frequency error or a scope bandwidth limit. A possible
explanation is frequency-estimator quantization: 4 GSa/s divided by seven is
571.428571 MHz. That numerical correspondence is an inference, not a finding
about the instrument's implementation.

The smallest next bench question is: with the source left at the same commanded
600 MHz, does a fresh raw record contain a coherent component near 600 MHz or
near the reported 571.43 MHz? A separately admitted experiment must retain both
predictions and distinguish them without relaxing this survey retrospectively.
No drift estimate is available because the return anchor was not reached. The
matched software-policy comparison and absolute bandwidth determination remain
open.

## Offline evaluation

The frozen bounded estimator accepted all ten acquired records. Unacquired
records remain missing in all 60 scheduled result slots; they do not enter means.
The fit used the supplied raw sample interval, centered times and the committed
frequency-search limits, with independent off-bin, noise and alias controls.

| Commanded frequency | Fitted mean frequency | Apparent peak mean | Population SD | Fundamental residual RMS |
| --- | --- | --- | --- | --- |
| 100 MHz | 100.002069 MHz | 146.374869 mV | 0.008453 mV | 42.083648 mV |
| 400 MHz | 400.008216 MHz | 134.215352 mV | 0.015767 mV | 22.272000 mV |

The 400 MHz mean is −0.753287 dB relative to the initial 100 MHz mean. This is
source/cable/CH1 sampled response, not isolated scope gain. The small within-visit
dispersion does not bound source amplitude error, scope calibration, mismatch,
alias bias or drift. Neither an end anchor nor a policy comparison was acquired.

Actual fitted detuning separates the ninth-harmonic alias from the 400 MHz
fundamental by roughly 82.16 kHz, versus the record's 40 kHz inverse-duration
scale. This avoids claiming an exact collision solely from nominal frequency;
it does not establish that omitted folded harmonics contribute no energy.
The order-one-through-nine sensitivity fit and all residuals remain diagnostics.
Synthetic exact-collision controls show that substantial amplitude bias can
coexist with a nearly zero fit residual.

The decision is to resolve the 600 MHz readback ambiguity with the separately
frozen [receive-frequency discriminator](rf-frequency-diagnostic-protocol.md).
Source and scope clocks are uncalibrated. Further survey admission depends on
that discriminator, and the failed survey remains immutable.
