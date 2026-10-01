# Raw acquisition-memory pilot

2026-10-01. The workstation retained one complete 100,000-point RAW ASCII record
at the unchanged 100 MHz source setting. This closes the export question that the
earlier [display waveform](rf-display-waveform.md) left open.

The admitted tasking was committed and pushed as `42aa892` before execution.
The operator's three-hour authorization covers this acquisition preparation.
The connected RF path, source firmware, instrument software, entitlements and
calibration were preserved. No source command was sent in this run.

## Acquisition

Fresh readback confirmed CH1 alone, internal 50-ohm termination, DC coupling,
1x probe ratio, zero offset, full channel bandwidth and normal acquisition.
Temporary settings were 50 mV/div, 1 microsecond/div and 100k memory depth.
The scope reported 4 GSa/s before and after stopping acquisition for RAW export.

ASCII data are actual voltage values under the official programming guide,
section 3.28; no BYTE/WORD scaling was applied. Preambles before and after the
complete 1,400,000-byte waveform response were identical:

```text
2,2,100000,1,2.500000E-10,-1.250000E-5,0.000000,6.6667E-06,0,32768
```

The mode is RAW, the selected extent and record count are 100,000, and the
250 ps interval agrees with the actual reported rate. The nominal record
duration is 25 microseconds; first-to-last sample span is one interval shorter.
This is acquisition-memory evidence under the documented RAW semantics, rather
than the earlier interpolated display grid.

| Quantity | Observed or derived value |
| --- | --- |
| Minimum / maximum | -135.473 / +131.467 mV |
| Peak-to-peak voltage | 266.940 mV |
| RMS voltage including DC | 112.198 mV |
| Fitted frequency using the scope timebase | 100.002060 MHz |
| Apparent fundamental peak amplitude | 147.087 mV |
| Fundamental-only residual RMS | 42.087 mV |
| Harmonic-fit residual RMS, orders 1 through 9 | 9.719 mV |

A bounded frequency search followed by least squares avoids assuming an exact
100 MHz frequency over the longer record. Known DC, fundamental and third-harmonic
synthetic controls passed. The fitted frequency inherits the scope timebase
uncertainty; it is not an independent frequency calibration. Amplitudes describe
the complete source, cable and scope chain.

## Preservation and restoration

Full packet capture began before assigning the isolated host address. The
existing six-hour lease and endpoint remained valid. Before/after checks retained
the separate normal default route and disabled forwarding, NAT and Internet
Sharing. No gateway or DNS service was introduced to the scope-facing segment.

All retained application bytes match the packet capture: 104 request files,
83 response files, 1,961 request bytes and 1,400,736 response bytes. The recorder
exited zero after SIGINT with 1,805 captured, 1,805 received by its filter and
zero reported kernel drops. Offline capture assessment accepted the stored
record. This does not establish absolute wire completeness.

Original export format, mode, point extent, vertical scale, timebase and memory
depth were restored and read back. Acquisition resumed; all queried settings
matched the initial values apart from transient trigger status. Temporary host
addressing and the lease helper were cleaned up.

The separately verified private run manifest at
`out/rf/raw-pilot-20261001T221500Z.toml` covers 253 files and has SHA-256
`b0e07f18a1ebb72069613b10712e74e1af8b4aa94ed955b948e878d76138afb3`.
It includes raw responses, capture, host manifests, controller provenance,
stream verification and offline reduction source. Earlier runs remain immutable.

## Decision and next question

Raw acquisition is ready for a bounded current-policy survey. Keep a fixed gain
setting, a predefined frequency sequence, repeated independent records and
reference returns. Interpret the survey as the apparent sampled response of
the connected chain, with source amplitude and spectral limitations explicit.

Offline controls exposed an additional limitation: at 4 GSa/s, a 1 GHz signal's
third harmonic aliases onto its fundamental. A synthetic 0.2 V peak fundamental
plus a 0.06 V peak third harmonic can appear as 0.14 V peak, a -3.098 dB bias,
with essentially zero fit residual. At 800 MHz, a ninth harmonic can similarly
coincide. More points or a cleaner residual cannot identify coincident components.

Nearby frequency controls can reveal resolved alias components, but cannot
substitute for the exact 1 GHz measurement. The survey must flag these ambiguities.
A qualified sine source or a characterized bound on folded harmonic energy is
needed before treating fitted amplitude as isolated analog fundamental gain.
The matched-policy comparison and corrected absolute bandwidth gates remain open.
