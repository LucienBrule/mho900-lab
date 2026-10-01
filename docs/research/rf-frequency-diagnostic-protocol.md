# Frozen 600 MHz receive-frequency discriminator

2026-10-01. This is a separate experiment following the
[partial survey](rf-current-survey.md). That survey stopped before a 600 MHz raw
export when SCPI reported 571.43 MHz. No earlier guard or interpretation changes.

Preserve the source at its last commanded 600 MHz and raw power code zero. Send
no source command during this experiment. Preserve wiring and installed software
policy. Start a fresh full capture and verify the existing isolated host/lease
prerequisites. Retain all requests and responses. Stop on transport, recorder,
network, raw metadata or +/-180 mV range failure; no retries.

Temporarily set CH1 to 50 mV/div, 1 microsecond/div and 100k memory, with reported
4 GSa/s. Keep internal 50 ohms, DC, 1x, zero offset and FULL bandwidth. Read the
built-in frequency, Vpp and extrema. Treat frequency as an observation rather
than a gate. Acquire exactly three fresh RUN → settle at least one second →
STOP → RAW ASCII 100k records, preserving matching preambles and exact bytes.
Independently qualify the files with the typed waveform library.

After those exports, restore NORMAL waveform mode, RUN, change only the timebase
to 10 ns/div, wait five seconds, and repeat the same built-in frequency, Vpp and
extrema queries. No additional raw record or source adjustment. Restore original
export, scale, timebase, memory and RUN, and verify readbacks. Source remains at
its previous commanded 600 MHz.

## Frozen predictions

Fit DC plus sine/cosine with centered sample times in two fixed candidate bands:
599.8–600.2 MHz and 571.23–571.63 MHz. Use a global grid no wider than 5 kHz,
refine candidate minima, and retain boundary or competing solutions. Also retain
a Hann-window FFT diagnostic and the strongest bin in 500–650 MHz. Do not widen
bands after seeing the data. Compare candidate amplitude, explained variance
and residual separately for all three records.

H600 requires every record to have an interior, noncompeting 600-band solution
with apparent peak at least 20 mV and at least ten times the 571-band apparent
peak. The strongest 500–650 MHz FFT bin must be in 599.8–600.2 MHz, and the
three fitted frequencies must span less than 50 kHz. H571 applies the symmetric
criteria in the other band. Neither passing means inconclusive. These thresholds
are declared engineering discriminators, not calibrated uncertainty estimates.

Preference for H600 establishes a received sampled component near 600 MHz on
the scope's reported clock, not independently accurate RF frequency. A built-in
frequency change with timebase supports measurement-mode dependence, not a
proven internal algorithm. The numerical correspondence between 4 GSa/s divided
by seven and 571.428571 MHz remains an inference. This experiment measures neither
analog bandwidth nor the effect of the installed capability policy.
