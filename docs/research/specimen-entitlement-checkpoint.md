# Specimen-derived entitlement checkpoint — 2026-09-29

Historical checkpoint: this records the guest/component stage before physical
installation. Its next bench questions were subsequently answered by the
[physical ordinary-option program](physical-ordinary-options.md),
[FRAM baseline](physical-fram-baseline.md), and
[physical D-capability deployment](physical-d-capability.md). See the
[RF evaluation plan](rf-performance-evaluation-plan.md) for the current remaining
objective. The original scope and conclusions below are retained.


The acquired-input component program now covers the complete ordinary individual
catalog, its process/reboot persistence, and its interaction with the separately
derived MHO984D capability record. Further repetition of those same component
checks has low information value. The remaining high-value boundary is the
instrument's ordinary installer and storage behavior during the full application
lifecycle.

## What is established

| Area | Evidence | Limit |
| --- | --- | --- |
| Active software | Acquired Sparrow, packaged Auklet and Web Control match official `.26` | Inactive copies and other firmware components have separate provenance |
| Physical baseline | Eleven queried option statuses were zero; cached raw/effective bandwidth was 17/17 | Three built-in native policy entries were not independently read as heap state |
| Acquired ordinary catalog | Ten licenses installed cumulatively; every candidate survived fresh-process and actual guest reboot checks | ART/native-component harness with modeled private storage |
| Final catalog | Thirteen true entries: ten individual licenses plus EMBD, COMP, AUTO; BND false | Validity does not prove each feature's operation |
| Complete catalog with D capability | Public MHO984 identity; selected MHO984D record; raw/effective 18/18 before/after stock option policy and after guest reboot | Explicit derived copy, not an ordinary 1 GHz entitlement or measured RF result |
| Older private state | All ten permanent licenses validate with exact older saved-time bytes; all other 21 canonical files unchanged | One initialization contrast, not full startup or physical FRAM durability |

The installed individual names are FlexA, BWU05T08, AFG100, AFG50, AUDIOA, AUTOA,
AEROA, RLU05, BWU03T05 and BWU03T08. BND was deliberately excluded; its path can
remove individual license files. Built-in policy results are kept distinct from
newly installed licenses.

The final catalog retains 22 canonical artifacts: the acquired key file, ten
stock-written licenses, ten retained witnesses and modeled private storage.
The complete-catalog stock and derived arms retain exactly the same bytes.
Original APK/native ancestors remain preserved. No physical entitlement or
capability change was performed by these experiments.

## Evidence and one failed run

- [Complete acquired catalog](acquired-option-catalog.md), final seal
  `0724e39fbfb4e2d320b2c4c48d6243f8b566d63a47d2049ab7fb9f1118758781`.
- [Complete catalog capability comparison](acquired-combined-capability.md),
  accepted stock seal `7ffb39a50f36e97c9fce32e72869b7d3698b2aa869fbb83d10992a061c36101f`,
  derived seal `061e37557df627786c11b2abe76be4d97b992f1ced51f2d67d14a239df2a6b04`.
- [Older private-state contrast](permanent-license-private-state.md), seal
  `4e06f50571f0f526dcb6affdb5ecf212ae729dde184173eef58cd3277a61cdfd`.
- [Physical option baseline](physical-option-status.md) and
  [cached bandwidth observation](cached-bandwidth-observation.md).

The first combined stock run reached the expected guest terminal, but its host
controller did not recognize the new completion label. It remains a failed run,
sealed separately. A bounded host-only repair passed rejection/regression controls;
a new run then passed the independent phase verifier. No earlier evidence or
failed result was rewritten to manufacture acceptance.

## Research judgment and next bench question

The useful next question is:

> Does one ordinary non-bundle option, installed through the running stock
> program using the exact guest-validated input, become queryable and remain
> accepted after one normal physical reboot while model and bandwidth stay at
> their stock baseline?

FlexA is a suitable first candidate because it already has isolated and cumulative
acquired-input controls. Before that mutation, preserve a fresh logical option/key
baseline and account explicitly for private storage. Existing SD images do not
include the I2C-backed FRAM. Its current contents have not been acquired, and the
guest's modeled private stream must not be called a physical backup.

The immediate read-only bench question for that gap is:

> What is the stock application's current private-store state, and can it be
> captured without invoking a save or changing the physical FRAM? If an in-memory
> snapshot is obtained, does a separately justified stored-image read agree?

A cached snapshot alone cannot establish that queued saves reached FRAM. Do not
substitute guessed private state or assume arbitrary raw I2C reads have safe
semantics. Resolve the acquisition method explicitly and preserve any remaining
backup limitation before interpreting an installation/reboot result.

A first physical install experiment should preserve the exact submitted input,
original result, before/after option query, file delta and normal-reboot outcome.
It should stop on unexpected identity, option, storage or application behavior.
The D-capability deployment and later analog bandwidth measurement remain separate
experiments; guest enum 18 is not an RF transfer-function measurement.

There is no reason to make full factory-image boot, more per-access ADC/AFE
observation, or repeated time-zero component tests prerequisites for this next
question. Timed licenses, bundle behavior, full startup timers and feature operation
remain outside the results above. No physical installation task is admitted by
this checkpoint document.
