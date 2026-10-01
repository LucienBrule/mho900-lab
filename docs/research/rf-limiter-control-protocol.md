# Fixed-frequency ordinary channel-limiter control

This experiment asks whether CH1 OFF → 250M → OFF produces a large reversible
change in retained sampled AC output at a fixed source command. The installed
software policy, firmware, entitlements, calibration and wiring remain fixed.
It does not compare software policies or certify calibrated analog bandwidth.

The preserved official MHO900 Programming Guide, section 3.6.1, printed page 82,
documents `:CHANnel1:BWLimit OFF`, `:CHANnel1:BWLimit 250M` and the query.
The preserved PDF SHA-256 is
`a671c065bd04a85d05e9d4cef732df3ba4884c2218054f64d1a83fb5a43cffd5`.
It supplies no 975 MHz attenuation or settling guarantee. The thresholds below
are engineering discriminators frozen before acquisition.

## Physical sequence and fixed acquisition

Start a new full Layer Two capture before the isolated temporary host address
and SCPI connection. Verify the existing one-client lease, separate default
route, disabled forwarding/NAT/Internet Sharing, interface identity and capture
health. Use only the documented SCPI endpoint and factory source point sender.
Check USB ancestry and absence of another serial owner before each source write.
Preserve raw requests/responses, source frames, settings and capture statistics.

Command 975 MHz, raw power code zero, exactly once. Acquire these conditions in
order, with five fresh records each: OFF-A, explicit 250M, OFF-B. There is no
source command between groups. Verify the limit query and fixed acquisition
settings at each condition. Run for five seconds after each selection, then
use a fresh RUN for one second followed by STOP for every record. Keep CH1 at
50 ohms, DC, 1×, zero offset, 50 mV/div; CH2–CH4 disabled; normal acquisition,
1 µs/div, 100,000-point RAW ASCII, actual 4 GSa/s, start 1 and stop 100,000.
Retain built-in measurements as observations, without a lower-level or
frequency gate on the 250M condition. Do not alter triggering to obtain data.

After all fifteen records complete, make the separately recorded planned
100 MHz/raw-zero return command once. Restore original channel limit,
scale, timebase, memory, waveform export and RUN state while SCPI is healthy.
On a bounded failure there is no extra source return, retry or replacement
record. Retain every attempted and missing slot. Stop physical acquisition on
recorder, transport, unexpected network, uncertain source-write, hard input or
unexpected guard failure. Reserve twenty minutes before the three-hour deadline
for cleanup. Gracefully terminate the recorder with drop statistics, remove the
temporary address and lease helper, verify restoration and seal the acquisition
before final numerical reduction.

## Record validity and suppressed reception

Every record requires original finite volts, identical valid RAW preambles,
100,000 samples, acquisition count one, full memory extent and consistent
reported/interval-derived 4 GSa/s within relative tolerance 1e-8. Recompute
strict absolute extrema below 180 mV and Vpp below 360 mV from original samples.
Preserve and independently recompute the unchanged default `mho-rf` receipt
with profile hash
`25401a53b0b9b9a14581f740b5d8cf665ccfb2b37c962d925c77b46389409358`.
Both OFF groups must receive-qualify under that complete default profile.

For 250M only, after all independent hard checks pass, preserve a qualified
receipt or a receive rejection with code `band-peak-frequency`,
`global-peak-frequency` or `energy-fraction`. A `range:vpp-range` rejection is
permitted only when recomputed original Vpp is between zero and 5 mV inclusive;
label this `suppressed-below-receive-floor`. Never allow that code alone, because
it also represents an upper-range failure. All other rejections stop the run.
These outcomes permit AC statistics; none alone establishes suppression.
Keep original receipts unchanged. Do not widen a receive profile or fit noise.

## Frozen decision

The primary metric is **unwindowed demeaned population AC RMS**:
`sqrt(mean((y - arithmetic_mean(y))**2))`. Retain DC, extrema, Vpp, each RMS,
group arithmetic means, population SD and min/max. No Hann window, fitted
carrier, built-in RMS or Vpp-derived sine substitution enters this metric.

A positive sensitivity result requires both:

- Every middle-group record is at least 6 dB below every OFF record:
  `max(R_250M) <= 10**(-6/20) * min(R_OFF_A + R_OFF_B)`.
- The uncorrected OFF group means return within 0.3 dB:
  `abs(20*log10(mean(R_OFF_B)/mean(R_OFF_A))) <= 0.3`.

Report individual comparisons and the complete fifteen-slot denominator. A
valid failure of the 6 dB criterion is a negative result for this discriminator;
hard invalidity, missing records or anchor disagreement makes the conclusion
inconclusive. Exact zero sampled AC may satisfy the ratio algebraically but is
labeled zero/below-floor; it is not infinite measured analog attenuation or an
independently measured noise floor. Apply no drift correction or interpolation.

AC RMS includes harmonics, aliases, broadband and receiver noise. An agreeing
OFF return constrains endpoint drift but cannot exclude a temporary source
change during 250M. Loading, digital processing or quantization may contribute.
The conclusion concerns setting-associated sensitivity of the sampled complete
chain. Physical frequency origin, isolated analog gain, calibrated bandwidth
and the matched software-policy effect remain separate questions.
