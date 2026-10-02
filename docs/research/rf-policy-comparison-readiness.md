# Matched software-policy RF comparison: readiness hold

Historical hold recorded on 2026-10-01. The later
[execution decision](rf-policy-comparison-go.md) supersedes the readiness status
below; the original assessment is retained.

2026-10-01. Offline preparation under `TASK.rf.execution-decision`.
**Execution remains held at the initial stock rollback and its evaluation.**
The controller preparation task is closed. Operator continuation accepted the concrete
stock → derived → stock proposal, including its initial rollback and final stock
state. The preparation, rollback and evaluation batch is admitted and committed.
The original execution task stays open until those readiness conditions pass.
The completed fixed-policy survey and ordinary-limiter control are supporting
evidence; the comparative samples remain to be acquired.

The [comparison preparation](rf-policy-comparison-preparation.md) records the
typed numerical controls and independent software-observation gates. Preparation
fixtures and historical observer inputs do not establish a current physical arm.
The [controller preparation](rf-policy-transition-preparation.md) records the
tested healthy transition, captured-lease and acquisition handoff. Its frozen
inputs do not establish an executed rollback.

## What is now resolved

The [RAW survey](rf-raw-qualified-survey.md) established a repeatable supplied
record path at 100,000 points and 4 GSa/s, including nominal 1 GHz and 1.1 GHz.
The initial 100 MHz anchor returned within 0.034 dB. The
[ordinary-limiter control](rf-limiter-control.md) established a large reversible
sampled AC response to an ordinary setting, with a 0.002 dB OFF return. The
built-in frequency reading is unsuitable as the primary frequency guard;
original waveform bytes and the separately frozen receive analysis are retained.
None of these controls changes native policy or authenticates the physical
fundamental amplitude at the connector.

The last physically established software state is the
[derived standalone native library](physical-d-capability.md), with raw/effective
enums 18/18, the signed stock APK, retained public identity and ordinary options.
The latest RF session made no native-policy observation. A historical hash is
therefore a comparison target; it must be revalidated before a transition.

## Proposed narrow question

At a fixed source command of 1 GHz, with CH1 alone, 50-ohm DC input, 1× probe
ratio, zero offset, ordinary limit OFF, 50 mV/div, normal acquisition and
100,000-point RAW export at 4 GSa/s, does changing only the verified native
software-policy arm produce a reversible change in sampled AC output?

Use A1 stock → B derived → A2 stock. The starting derived state requires an
initial verified rollback before A1. Proposed final state is **stock A2**, with
source returned to 100 MHz/raw-zero and original ordinary scope/export/RUN
settings restored. Restoring derived software afterward would be an additional
explicitly authorized transition, not implicit cleanup. No cable, source power
setting, option, calibration or host security change belongs to this comparison.

This first question concerns sampled complete-chain response. It does not certify
analog bandwidth. The uncalibrated source and folded harmonics still prevent a
corrected fundamental transfer function. A positive result would establish an
association with the verified software transition under recorded conditions;
reboot, thermal, source/load and digital-processing effects require their own
limits. A negative result is useful: stock may already pass the received signal
at this gain, or the policy may affect a different path.

## Candidate acquisition and decision rules

These engineering discriminators are frozen in the numerical contract, with
tested controls established before comparative data.
The prior single-policy records are exploratory support, not A1/B/A2 samples.

For each arm, visit 100, 800, 975 and 1000 MHz, then return to 100 MHz. Retain five
fresh RUN/STOP records at each visit: 25 per arm, 75 scheduled slots. Use the
existing factory point encoder at raw output zero. Allow at least five seconds
RUN after each setting and one second fresh RUN before each STOP. Do not replace
failed slots or append points after seeing the response. Keep all original
preambles, exact voltage bytes, source writes, setting readbacks and captured
management streams.

The primary metric is unwindowed demeaned population AC RMS in original volts.
At 1 GHz, a positive engineering contrast requires every B record to exceed
every A1/A2 record by at least 1 dB. A contrast in the opposite direction of at
least 1 dB is a contrary result: every A1/A2 record must exceed every B
record by that margin. Intermediate contrasts are unresolved at this
discriminator. These are not confidence intervals or metrological uncertainty
bounds. The 800 and 975 MHz contrasts remain separately labeled controls and
secondary observations; they cannot replace a failed 1 GHz criterion.

Every comparison frequency requires A2/A1 arithmetic-mean RMS return within
±0.3 dB. Each arm's repeated 100 MHz anchor requires the same return criterion;
initial 100 MHz means across arms must also agree within ±0.3 dB. Report raw
ratios without anchor correction. Failure of a return criterion makes the
policy contrast inconclusive. Exact zero is a named outcome with no invented
finite dB ratio; missing, unrepresentable or invalid records prevent a positive
primary decision. Dispersion of five records is descriptive, not independent
sample or confidence-interval evidence.

The original default receive receipt must remain attached to every record.
Strong records can use its frequency qualification. A weak stock arm must not
be rejected solely because suppression defeats that guard. Before execution,
freeze and test a separate interpretation requiring original finite RAW data,
exact count, acquisition count one, start/stop and memory consistency, actual
4 GSa/s with matching 250 ps increment, and the same strict upper voltage/Vpp
limits. Permit only named low-floor or receive-stage failures under that
interpretation; no malformed geometry, invalid rate, overload, unexpected
query or unplanned condition may be waived. A weak record supplies sampled AC
statistics, not a claimed carrier amplitude or carrier identity. The reusable
statistics primitive alone does not implement this experiment eligibility rule.

Any tone fits are descriptive secondary analysis of eligible received records,
with unchanged band, model, residual and alias disclosures. Do not compare a
tone-fit amplitude in one arm to whole-record AC RMS in another.

## Software transition and preservation gate

1. Under a fresh healthy isolated capture, revalidate package-selected native
   location, signed APK and embedded stock member, current standalone derived
   hash, executable mappings, raw/effective enum, boot/process identity, public
   model and ordinary option states. Record private paths only in private run
   evidence. Preserve a fresh logical baseline and exact introduced-file copy.
2. Stock transition: remove only the previously introduced, independently
   hash-matched standalone native file, then request one normal reboot. Bound
   readiness without repeating an ambiguously delivered reboot. Prove APK-backed
   stock Auklet selection, no standalone derived mapping, stock hash and 17/17,
   normal visible UI, unchanged options and protected logical content. Physical
   rollback has not yet been exercised; failure stops before RF collection.
3. Derived transition: follow the previously validated temporary-copy/readback/
   hash/ownership/mode/rename procedure for the exact approved derived bytes.
   One normal reboot and independent postboot mapping plus 18/18 observation
   are required. No APK replacement, entitlement installation or calibration.
4. A2 transition: repeat the same narrowly verified stock rollback. Record its
   complete result even if it fails; failure does not authorize automatic
   reinstatement, calibration repair or unrelated file writes.

The comparison targets are stock embedded Auklet SHA-256
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`,
derived standalone Auklet
`09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e`,
and signed APK
`6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b`.
All are revalidation requirements, not claims of a current fresh read.

Preserve all license/key/vendor bytes and calibration coefficient payloads
across arms. The existing boot reconciliation permits only separately validated
bandwidth-header CRC/time changes with unchanged 320-byte coefficients and the
known identity fallback cache producer/shape. Do not whitelist other changes.
Record each logical delta and compare it against the established producer before
accepting an arm. A new delta is a decision event. Self-calibration is excluded.

Use more than 30 minutes warm-up before the comparison and after each reboot as
an explicit conservative thermal control, with source left powered and wiring
fixed. Record ambient conditions and any cooling interruption. Matching elapsed
warm-up does not prove thermal equality. A substantial ambient change or needed
calibration stops this protocol rather than being silently corrected.

## Conditions still missing

- The still-unexecuted initial stock rollback and its independent evaluation.
  The controller preparation is closed with explicit offline evidence; the
  bounded rollback tasking remains open.
- Fresh specimen state and UI/thermal witnesses at the physical gate. Connectivity
  alone cannot establish that the intended native arm is loaded.
- Enough time for all three transitions, their full warmup intervals, comparison
  records and cleanup before the authorized window ends. An elapsed budget cannot
  waive a warmup or authorize a partial software transition.

The next smallest physical action is **a separately captured verified stock
rollback and postboot baseline**, once fresh bench conditions and the complete
remaining time reserve are established. It should
resolve whether the actual unit returns to original APK-backed policy without
changing protected content. That is higher-value than another same-policy RF
sweep. Failure closes that bounded transition question and preserves the
comparison hold; it does not broaden the experiment.

Independent spectrum and reference-plane amplitude measurements remain a separate
follow-up for absolute 1 GHz bandwidth. They need not block this explicitly
sampled relative comparison, and this comparison cannot substitute for them.

Recorder failure, unverified isolated routing, transport loss, ambiguous command
completion, unexpected native mapping or logical delta, visible prompt/reboot,
overload, changed termination/rate/geometry or an unavailable policy witness is
a stop condition. Seal the partial run without retries or replacement records.
Ordinary setting/source return and host cleanup are permitted only while their
state and transports are established; a stop does not authorize an unobserved
native write or reboot. Plan a lease and capture lifetime covering the thermal
intervals. Re-establish a continuous, timestamped visible UI witness or operator
check at postboot boundaries; a SCPI identity reply alone is insufficient.
