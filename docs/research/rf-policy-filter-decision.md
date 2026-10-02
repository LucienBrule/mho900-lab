# Policy mechanism and the next RF question

2026-10-01. The bounded [exact-stock recovery](rf-policy-filter-static.md)
supports a targeted software-policy comparison. It does not close the original
RF execution gate. Under explicit 4 GSa/s and normal-resolution inputs, enum 17
selects digital bank 27 and enum 18 selects bank 29. The two 64-word payloads
differ. Their corresponding constructor AFE tuples are both `(3, 3, 27)`;
the recovered loader's supplied 320-byte payload ends before that tuple array.

This changes the useful hypothesis. A measured difference between these policy
arms could arise from digital processing and associated scale/offset refresh,
even if the live analog tuple is unchanged. A sampled amplitude improvement
would therefore not, by itself, establish an analog front-end bandwidth change.
Conversely, equal constructor tuples do not prove equal live tuples or analog
state. Their runtime values and other writers remain unresolved.

The upper API also gates the effective selection. It reads native scale and
impedance-dependent state, can substitute lower bandwidths, and stores the
ordinary limit before substituting the model bandwidth for FULL. A FULL setting
readback alone does not establish the effective driver enum. The exact native
representation of the bench's 50 mV/div and its mapping into the driver remain
unproved. Live sample mode, channel mask, coefficient enable state and actual
DSP consumption are likewise absent from these static receipts.

The next physical observation should answer this precise question:

> In the verified stock baseline and subsequent derived arm, which effective
> driver bandwidth enum, resolution selector, native scale, impedance, analog
> tuple, digital bank, coefficient enable state, sample mode and channel mask
> are used for CH1 at 50 mV/div, FULL and reported 4 GSa/s?

This observation belongs in a separately admitted runtime-observation protocol.
It would sharpen interpretation of the
[proposed stock → derived → stock comparison](rf-policy-comparison-readiness.md),
in which the same unwindowed sampled AC RMS estimator is applied across all arms.
Verified software mappings and raw/effective policy enums are required to identify
those arms. Complete hidden DSP telemetry is needed to attribute a contrast to
particular banks; it is not a universal prerequisite for a bounded empirical
comparison of verified software policies. Keep those two questions separate.
The smallest next physical action remains a separately captured, verified
stock rollback and postboot baseline. No rollback, native change or instrument
contact was performed during this static batch, and this decision grants none.

The original `TASK.rf.execution-decision` remains open. Its matched acquisition,
reduction and determination successors remain waiting. The completed
[single-policy survey](rf-raw-qualified-survey.md) establishes useful reception
through a nominal 1.1 GHz command. The [ordinary limiter control](rf-limiter-control.md)
establishes reversible sampled sensitivity to a channel setting. Neither contains
the stock/derived counterfactual. The [reusable RAW statistics delivery](rf-raw-ac-statistics.md)
supplies a tested metric primitive; it does not supply experiment eligibility or
authorize software transitions.

Further static confirmation of the same table entries has low information value.
The missing evidence is now the matched physical response, with actual runtime
selection needed for a specific mechanism attribution. DSP coefficient interpretation could support a later independent
specification, but a guessed encoding or another synthetic selection matrix
would not replace either missing witness. The next batch should be chosen from
those questions after the operator evaluates the transition proposal.
