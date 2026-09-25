# Decision: reconstruct files and observe whole loaders

The current model boundary remains mapped-access observation with precise
execution stops. Neither a guest character-device backend nor a higher-level
function replacement is needed to answer the next question. No driver ABI
expansion follows from this batch: the next region is file consumption before
ADC programming, with no new mapped-register response.

Hypothesis: with the byte-identical available LSB and vertical stock defaults
installed at their logical paths, the stock first-three-loader region produces
statuses 192/1794240/-1, loads the two complete payloads, and leaves the ADC record
unchanged when both ADC paths are absent. The initial ADC zero-fill is established
statically; its actual bytes at this point must be observed rather than assigned.
A filesystem permission error or unexpected earlier write falsifies some of this
prediction and is a valid result.

Prefer this bounded complete region to a terminal checkpoint alone: the three
returns are overwritten in one stack slot, and status alone cannot establish
buffer contents after a failed load. Prefer reconstructing real available files
to synthesizing loader returns or authoring a guessed ADC calibration record.
This does not claim defaults measured for an actual instrument or credible
acquisition. They are exact stock software inputs in a synthetic environment.

Private controls must first validate complete capture, post-return stop rotation,
atomic-sequence preservation, thread convergence and divergence handling. The
stock experiment is not yet admitted. A controls decision will freeze or reject
its exact observer and may admit the stock run and evaluation afterward.

The symbolic static ADC parameter grammar is retained for the next decision.
Do not analyze every deterministic store again. Use the observed calibration
state to instantiate that grammar only after deeper unresolved selectors or
feedback boundaries have been separately evaluated.

The [review result](../../experiments/calibration-static/review-results.toml)
and [exact candidate](../../experiments/calibration-static/loader-candidate.toml)
are the inputs to this decision. The bounded
[task batch](../../.agents/plans/calibration-loaders.yaml) contains observer and
private-control work followed by an explicit gate. Preserve the existing stock
run and observer binary as the baseline. The new observer may run private
controls, but another stock continuation requires that gate's evaluated result
and separately committed successor tasking.
