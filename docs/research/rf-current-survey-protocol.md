# Frozen current-policy RF-chain survey

2026-10-01. This is a descriptive pilot under the existing installed capability
policy. It follows the qualified [raw-memory export](rf-raw-pilot.md). The
operator authorized a three-hour unattended session with the connected bench.
No firmware, option, calibration, cable or software-policy transition is part
of this survey. The matched-policy comparison gate remains open.

## Question and design

What repeatable sampled response does the connected source, cable and CH1 chain
produce at the declared frequencies? Does the initial 100 MHz reference repeat
after the sequence? The source has unknown calibrated amplitude response and
substantial observed harmonics. Report apparent sampled fundamental amplitude,
not isolated analog gain or an absolute -3 dB bandwidth.

The fixed visit sequence in MHz is:

`100, 400, 600, 800, 900, 950, 975, 1000, 1025, 1050, 1100, 100`.

Send one explicit factory point command per visit with raw power code zero.
Retain one-write transport evidence and validate the resulting frequency using
SCPI. Serial silence is not a device acknowledgement. The final visit returns
the source to 100 MHz; no extra serial cleanup command is planned.

At every visit, wait five seconds after the source command. Require a finite
SCPI frequency within 1% of the command, Vpp between 5 mV and 360 mV, and measured
extrema within +/-180 mV. The lower limit is a receive-qualification threshold:
a failure is a retained censored point, not a bandwidth verdict. The upper limit
is a conservative input/display-range guard at the chosen scale.

Use CH1 alone, internal 50 ohms, DC, 1x, zero offset, FULL, normal acquisition,
50 mV/div, 1 microsecond/div and 100k memory depth. Verify actual 4 GSa/s.
For each of five records per visit, RUN, wait at least one second, STOP, verify
stopped state, and export the entire 100,000-point RAW ASCII extent. Repeated
reads of unchanged stopped memory do not count as independent acquisitions.
Retain preambles before and after each complete response. Require matching
metadata, finite values, 250 ps interval, selected extent and raw extrema within
the same +/-180 mV guard. ASCII values are volts; do not apply integer scaling.

## Estimator and controls

Retain all 60 expected records or identify the exact stopped prefix. Fit DC plus
sine/cosine by least squares using centered raw sample times. Search a fixed
interval of +/-0.01% around the retained SCPI frequency, on a coarse grid no
wider than 5 kHz, then refine candidate minima. This is a search heuristic based
on observed readback precision, not independent frequency accuracy. Boundary
solutions or unresolved competing minima are flagged; do not silently extend
the fit interval after seeing the data.

Report apparent peak and RMS fundamental amplitude, residual RMS, actual sample
interval, extrema, frequency, time and repeat dispersion. Retain a fixed-order
harmonic sensitivity diagnostic through order nine, merging coincident sampled
frequency classes and rejecting rank-deficient attribution. Label components
as sampled aliases when applicable. Additional omitted harmonics remain unknown.

Controls include known-amplitude DC/sine/third-harmonic records, an off-frequency
record, and exact alias collisions at 800 MHz and 1 GHz sampled at 4 GSa/s.
At nominal 1 GHz, the third and other odd harmonics can coincide with the
fundamental; at nominal 400 and 800 MHz the ninth can coincide. Small actual
detuning may separate some components, but does not establish an external bound
on folded energy. The 975/1025 MHz points are predeclared nearby controls and
cannot substitute for an exact 1 GHz result.

Show the initial and final 100 MHz amplitudes without correction and their dB
difference. More than 0.3 dB is declared material drift for this pilot; it is
an engineering threshold, not a calibrated uncertainty. Report dispersion
separately and do not interpolate a drift correction from two anchors.

## Capture, stop and final state

Match source USB identity and serial ancestry and require no other port owner.
Begin full Ethernet capture before adding the isolated host address. Retain the
existing one-client six-hour lease with no gateway or DNS, and verify the normal
default route uses another interface, with forwarding/NAT/Internet Sharing off.
Observe network/capture health between commands; preserve raw application bytes.

Stop physical commands on capture or transport failure, uncertain source write,
unexpected state/network behavior, failed frequency/range qualification or an
invalid record. Do not retry a source command or failed export. Preserve partial
evidence, including the rejected point. Restore original scope/export settings
and running acquisition while the response framing remains healthy; if it is
uncertain, stop sending bytes and retain the restoration limitation.

On success the source remains at the final 100 MHz anchor, connected and powered.
Restore original scope settings, stop the temporary lease helper, remove the
host address, and terminate capture gracefully with drop statistics. Seal and
verify the run before reduction; retain public methods/results without private
unit or host identity. Unexpected results become a decision event and a separate
experiment, not a reason to append points to this frozen survey.
