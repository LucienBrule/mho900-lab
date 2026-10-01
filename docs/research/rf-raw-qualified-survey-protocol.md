# Frozen raw-qualified current-policy RF survey

2026-10-01. This is a new experiment after the
[600 MHz discriminator](rf-frequency-diagnostic.md). The failed survey remains
immutable. The source, cable, channel and installed software policy stay fixed;
no firmware, entitlement, calibration or wiring transition is part of this run.

## Acquisition and online receive qualification

Use the same fixed twelve visits in MHz:

`100, 400, 600, 800, 900, 950, 975, 1000, 1025, 1050, 1100, 100`.

Send exactly one factory point command at raw power code zero per visit,
checking USB ancestry and absence of another owner first. Retain intent, exact
frame and transport outcome. Wait five seconds. Record the built-in frequency,
Vpp and extrema; frequency is an observation rather than a gate. Require finite
Vpp between 5 and 360 mV and extrema within +/-180 mV. Retain any invalid built-in
frequency result explicitly; it must not be used as a fit center.

Keep CH1 alone, internal 50 ohms, DC, 1x, zero offset, FULL bandwidth, normal
acquisition, 50 mV/div, 1 microsecond/div and 100k memory with reported 4 GSa/s.
Acquire five separate RUN → wait at least one second → STOP → RAW ASCII 100k
records per visit. Require matching preambles, exact response-byte retention,
finite voltages within +/-180 mV, selected count and 250 ps interval. ASCII
values are already volts.

For each completed record, execute the same pure offline receive guard used by
the reusable library. This online qualification determines whether acquisition
may continue; it is distinct from the final sealed scientific reduction.
Preserve the input hashes, explicit profile and result for every proceed/stop
judgment. Freeze these operations:

1. Remove the arithmetic mean and use periodic Hann
   `w[n] = 0.5 - 0.5*cos(2*pi*n/N)`, for indices zero through N−1.
2. Compute the real FFT. Weight squared magnitudes by two for interior bins,
   one for DC and, for even N, one for Nyquist. Exclude DC from selection and
   total energy.
3. Select the strongest weighted-energy bin within inclusive
   `[0.5, 1.5] * commanded_frequency`. Also retain the strongest global non-DC
   bin. Require both frequencies to lie within 1% of the command.
4. Sum weighted energy in the selected peak's +/-2 bins, clipped to non-DC FFT
   extent, and divide by all non-DC weighted energy. Require at least 20%.
5. For a numerical peak tie within relative tolerance 1e-12, choose the lowest
   frequency bin and retain a tie diagnostic. Reject empty bands, zero or
   nonfinite energy, invalid profiles and failed frequency/energy criteria.

At this geometry bins are 40 kHz apart. These are engineering receive criteria,
not frequency calibration, purity or sensitivity specifications. They establish
a dominant sampled component near the command. Aliased physical frequencies,
nearby components and harmonic energy can satisfy or contaminate the guard.
The periodic Hann convention is explicit and differs from the discriminator's
symmetric Hann diagnostic; neither is silently substituted for the other.

## Final estimation and claim boundary

Seal and verify the complete raw run before final numerical reduction. Recompute
the receive guard and compare every retained online result. Fit DC plus sine/
cosine in fixed command-centered bands of +/-1e-4, with global grid no wider
than 5 kHz and existing edge/boundary/competing-solution controls. Retain command,
built-in readback, FFT bin and fitted frequency as separate quantities.

The 1% receive window is wider than the +/-0.01% fit interval. Receive acceptance
therefore does not imply a valid final fit. Boundary or competing fits remain
flagged; do not widen bands after seeing data. Retain all repeats, failures,
extrema, residuals and fixed-order-one-through-nine alias/rank diagnostics.

Report apparent sampled source/cable/CH1 amplitude, all five-record dispersions
and both uncorrected 100 MHz anchors. The 0.3 dB return threshold is an engineering
choice; no drift interpolation or calibration claim follows. Harmonic aliases
near nominal 1 GHz still limit isolated amplitude interpretation. Neither
absolute bandwidth nor a software-policy effect is established by this survey.

## Stop, capture and restoration

Start a fresh full Layer Two capture before adding the temporary isolated host
address. Preserve the one-client six-hour lease without gateway/DNS and verify
normal default route, forwarding, NAT, Internet Sharing and bridge isolation.
Observe capture/network health between operations.

Stop on capture, transport, unexpected network/state, uncertain source command,
range, byte/count/rate or receive-guard failure. No retries, added points or
post-hoc profile changes. Preserve the exact partial prefix. Restore original
scope/export settings and RUN while framing remains healthy; otherwise stop
sending scope bytes and report the restoration limitation. Final source command
is the declared 100 MHz return anchor if reached, with no extra cleanup command.
Stop helper and recorder gracefully, preserve drop statistics, remove the host
address, recheck isolation and seal all raw evidence separately from prior runs.
