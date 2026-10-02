# Unattended RF and tooling checkpoint

2026-10-01. The connected source/cable/CH1 chain produced useful RAW reception
through the nominal 1.1 GHz command under the installed software policy. A
separate ordinary channel-limiter experiment produced a large reversible change
in sampled AC. These observations advance physical qualification while leaving
the matched software-policy comparison and calibrated analog bandwidth open.

| Bounded question | Evidence and conclusion |
| --- | --- |
| Can the existing bench supply coherent RAW records? | The pilot qualified 100k original ASCII voltages with the reported 4 GSa/s clock and 250 ps sample interval. |
| Can built-in frequency alone gate the survey? | The first survey stopped at its frozen 600 MHz frequency gate. A separately admitted three-record discriminator favored the commanded-frequency component in RAW data over the conflicting built-in reading. The stopped run was preserved. |
| What does the current policy receive? | Twelve visits and sixty fresh RAW records, including nominal 1 GHz and 1.1 GHz, passed the admitted receive guard. The initial/return 100 MHz apparent-amplitude difference was +0.033589 dB without correction. |
| Does an ordinary limiter affect the sampled chain? | At a fixed 975 MHz command, OFF → 250M → OFF retained five records per condition. All fifty middle-to-OFF comparisons passed the 6 dB engineering criterion; the weakest reduction was 34.894429 dB. The OFF mean return difference was −0.001600 dB. |
| Can the metric be reused outside the experiment? | A typed pure RAW AC statistics operation and Click command passed 822 workspace tests and a separate installed-wheel consumer. All fifteen archived limiter metrics were reproduced from their original bytes. |
| What distinguishes the software policy enums? | Fresh exact-stock decoding selects digital bank 27 for enum 17 and bank 29 for enum 18 under explicit 4 GSa/s normal-resolution inputs. Constructor AFE tuples match; live selection and physical effect remain unobserved by this static batch. |

The authoritative details and separate artifact seals are in the
[RAW survey](rf-raw-qualified-survey.md),
[limiter result](rf-limiter-control.md),
[statistics delivery](rf-raw-ac-statistics.md) and
[exact-stock recovery](rf-policy-filter-static.md).
The [policy mechanism decision](rf-policy-filter-decision.md) explains the
remaining runtime witness. The original experiment receipts, failed development
checks and stopped survey remain separate; later interpretation did not rewrite
them.

The apparent survey response is a property of the complete sampled chain.
Source amplitude, source/cable response, folded harmonics, clock uncertainty and
digital processing have not been calibrated away. The roughly 35 dB limiter
contrast uses every sampled AC contribution, not a fitted isolated 975 MHz
carrier. Neither result establishes calibrated −3 dB analog bandwidth, all-gain
performance, all-channel performance or the effect of the stock-to-derived policy
transition.

After the last physical run, SCPI readbacks confirmed restoration of 500 mV/div,
10 ns/div, 10k memory, running acquisition, ordinary limit OFF and the original
normal/WORD export extent. The source received its planned 100 MHz/raw-zero
return command; host driver acceptance is recorded, without a new display or
serial acknowledgement claim. Temporary host addressing, capture and lease
processes were stopped. Network preferences and interface mapping retained equal
hashes, forwarding/NAT/sharing remained disabled, and the normal default route
remained separate. Wiring, firmware, policy, entitlements and calibration were
unchanged. Subsequent analysis operated only on retained files.

The original RF execution decision remains open, with matched acquisition,
reduction and determination waiting. The
[stock → derived → stock readiness proposal](rf-policy-comparison-readiness.md)
is concrete enough for evaluation, but requires its own verified physical
transition and software-arm evidence. Hidden runtime-selection evidence would
sharpen a mechanism claim rather than gate every empirical contrast. The next smallest physical action is
a separately captured stock rollback and postboot baseline. Independent source
and reference-plane characterization remains necessary for an absolute analog
bandwidth claim.
