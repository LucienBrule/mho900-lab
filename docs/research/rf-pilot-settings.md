# SCPI preparation for the first RF signal check

2026-10-01. The operator reported RF OUT connected directly to CH1 with the
source off, then requested that channel settings be established through SCPI.
Tasking was admitted and committed as `1936d96` before instrument contact.

The baseline query found CH1 at **1 MΩ**, despite the earlier operator report
of 50 Ω. It also found 50 mV/div and a 2 µs/div timebase. Three ordinary setting
commands corrected the pilot setup; all settings below were then read back.

| Setting | Before | After |
| --- | --- | --- |
| CH1 input impedance | `OMEG` — 1 MΩ | `FIFT` — 50 Ω |
| CH1 vertical scale | 50 mV/div | 500 mV/div |
| Main timebase | 2 µs/div | 10 ns/div |
| Reported sample rate | 500 MSa/s | 4 GSa/s |
| Reported memory depth | 10,000 points | 10,000 points |
| Enabled analog channels | CH1 only | CH1 only |
| CH1 coupling / probe ratio / offset | DC / 1× / 0 V | Unchanged |
| CH1 bandwidth limit / invert | OFF / off | Unchanged |
| Acquisition mode | Normal | Unchanged |
| Trigger | Edge, CH1, rising, 0 V, Auto, DC coupling | Unchanged |

The exact writes were:

```text
:CHANnel1:IMPedance FIFTy
:CHANnel1:SCALe 0.5
:TIMebase:MAIN:SCALe 1e-8
```

The vendor programming guide defines the impedance, scale and timebase commands
in sections 3.6.7, 3.6.8 and 3.26.5. Its bandwidth query returns `OFF` when the
channel bandwidth limit is disabled; this corresponds to the intended full
bandwidth selection, not an independent measurement of analog bandwidth.
The retained official guide has SHA-256
`a671c065bd04a85d05e9d4cef732df3ba4884c2218054f64d1a83fb5a43cffd5`.

## Connection and evidence

The linked dock interface had no host IPv4 address and no lease helper running.
The host baseline was preserved; interface identity, the independent default
route, disabled forwarding, inactive automatic addressing, absence of a bridge
membership and disabled Internet Sharing/PF were checked. A full Ethernet
capture began before the temporary address and single-client lease helper.

The operator reconnected Ethernet once while leaving the source off and the RF
cable untouched. The capture retained DHCP Discover, Offer, Request and ACK for
a six-hour private lease, without router or DNS options. Scope traffic consisted
of local IPv6 discovery, DHCP, ARP and the requested SCPI connection. Host-local
discovery traffic accompanied address assignment, consistent with earlier host
observations; it is retained in the capture. No external route was introduced.

One TCP connection carried 25 queries before and 25 queries after the three
writes. The request files match the captured TCP application payload exactly.
Identity was unchanged and reported MHO984 with software prefix `00.01.00`;
the serial remains private. No firmware identity or capability-memory claim is
derived from that version prefix.

Cleanup removed the temporary host address and stopped the lease helper.
The recorder exited zero after SIGINT, reporting 264 captured packets, 264
received by its filter, and zero kernel drops. Offline assessment accepted the
264 stored frames. These counters do not establish absolute wire completeness.
The host isolation checks passed again after cleanup. The scope retains the
new ordinary acquisition settings and its issued lease; the RF source remains
off according to the operator's latest report.

The private run is `out/rf/bench-preparation-20261001T214136Z`, with raw requests
and responses, before/after host and scope state, controller source, packet
capture, lifecycle events and an independent readback/stream check. Its exact
inventory contains 162 files and was verified after sealing.

| Artifact | SHA-256 |
| --- | --- |
| Complete run manifest | `1f002ddd3201dd4543628483827179e52d98b89c7539ea1ff71df52f7a6ad8d9` |
| Packet capture | `51dca59ca5e8497ba1ad3b51b4db0396fda6e4f2fca3f7c3af9ea5114ace8e59` |

## Decision

The instrument settings support the next bounded first-signal check. The next
physical transition is operator power-on of the source using the existing USB
connection, leaving RF OUT connected to CH1 and MCLK unconnected. Revalidate
the source endpoint, use the already demonstrated factory point path to select
100 MHz at raw power zero once, and observe the actual waveform and frequency
through SCPI. Startup persistence and delivered level remain unmeasured.

This is preparation for a pilot, not an RF-response result. No RF source command,
waveform acquisition, frequency sweep, calibration, firmware transition or
option change occurred here. The broader preparation, waveform-export,
integration and matched-policy comparison gates remain open. A successful
100 MHz signal check would establish the connected signal path at that point;
it would not establish 1 GHz bandwidth.
