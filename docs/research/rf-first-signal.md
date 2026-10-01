# First physical 100 MHz signal

2026-10-01. The prepared CH1 path received a physical signal that the MHO984
reported as **100 MHz, approximately 284 mV peak-to-peak and 112 mV RMS**.
The source display restored 100 MHz after power-on according to the operator,
who described the oscilloscope trace as square-shaped. The automated run ended
before waveform export because an optional fall-time query returned `9.9000E+37`.

## What was observed

The source was powered once through its established USB connection, with RF OUT
connected directly to CH1 and MCLK unused. USB VID/PID, dock location and serial
client ancestry matched the previous trial; no other open port user was observed.
The RF task was admitted and pushed as `bd62538` before this operation.

Fresh SCPI readback confirmed CH1 alone, 50 Ω, DC, 1×, 500 mV/div, zero offset,
bandwidth limit disabled, normal acquisition, 10 ns/div, 4 GSa/s and a 10,000-point
memory. The trigger status was `TD`. Channel units were `VOLT`.

| Scope measurement | As powered | After one point command |
| --- | --- | --- |
| Frequency | `1.0000E+08` Hz | `1.0000E+08` Hz |
| Peak-to-peak voltage | 284.40 mV | 283.80 mV |
| RMS voltage | 111.83 mV | 112.21 mV |
| Maximum | 133.00 mV | 135.00 mV |
| Minimum | −145.13 mV | −145.13 mV |
| Average | Not requested | −2.40 mV |
| Positive duty ratio | Not requested | 0.50000 |
| Rise time | Not requested | 0.600 ns |
| Fall time | Not requested | `9.9000E+37` — unusable result |

These queries sample a running acquisition and need not refer to one identical
record. In particular, subtracting independently queried maximum and minimum
values need not reproduce the separately queried peak-to-peak result.
The values are scope-reported observations, not calibrated source measurements.

One factory frame selected 100 MHz with raw power zero:
`55 55 00 64 00 00 00 0D 0A`. The host accepted all nine bytes, returned no serial
input, and closed normally. The transport outcome remains
`transport-complete-device-unconfirmed`. Since the source was already displaying
100 MHz and producing that frequency before the command, these measurements do
not independently prove a command-caused transition or the physical raw-power
selection. The earlier delivered-unit trial remains the command-path evidence.

## Bounded stop and evidence

The collector rejected the fall-time result as outside its numeric validity
bound. This preserved the first post-command measurement set, but prevented the
remaining planned repeats and waveform export. There was no retry or additional
source command. The measured peaks were well inside the configured vertical
window; the unusable fall-time value alone does not establish an input overload
or a hardware failure. It also supplies no useful physical fall-time estimate.

The inherited six-hour lease was validated against the preceding capture. Fresh
capture preceded temporary host addressing and SCPI. Host isolation checks passed
before and after, and the address and lease helper were removed/stopped during
cleanup. The recorder exited zero after SIGINT with **197 captured packets,
197 received by its filter and zero kernel drops**. Offline capture assessment
accepted the 197 stored frames. Absolute wire completeness is not claimed.

Private evidence is retained under `out/rf/first-signal-20261001T215225Z`.

| Artifact | SHA-256 |
| --- | --- |
| Complete run manifest, 159 files | `6f7f74fede0685e150d083bdad6c10ea060f24497611287e90d7b214b59df1e3` |
| One-command transcript manifest | `604d56969c6393eb497d3f2e262912c53d987334e7f0831d59aff780a32ce9a1` |
| Packet capture | `52afc6cf75139c87d9f6c313e86d5cbd34681ac86c517c37d65725572e2a772f` |

Both manifests were verified after sealing. The scope retains its pilot settings;
the source remains powered with the single 100 MHz command submitted. There was
no scope firmware, entitlement, calibration, reboot or acquisition-setting change.

## Decision

The first signal question has a positive, limited answer: a triggered 100 MHz
signal reaches the prepared 50-ohm channel at a readily measurable level.
Startup frequency-setting persistence has an operator witness and matching
scope-reported frequency. Longer stability, calibrated level, waveform shape
and spectral composition remain open.

The next useful observation is a separately recorded display-waveform export
at the unchanged settings, with no further source command. Optional automatic
edge measurements should be represented as unavailable values rather than used
as prerequisites for unrelated waveform export. This conclusion preserves the
stopped run instead of modifying it to obtain a desired result.

The original RF preparation and matched-policy comparison tasks remain open.
This result establishes neither 1 GHz bandwidth nor a difference between the
stock and selected capability policies.
