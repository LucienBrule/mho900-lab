# ADC transcript consumer controls

The private guest suite validates a consumer for the complete 452-write ADC prediction. Both full-sequence
cases accepted exactly 452 W32 operands and stopped at the next unanswered read: once on the main thread,
once on a worker. They preserved non-PC registers at every accepted store and completed exact thread-group
cleanup. No stock application ran in this suite.

The [control specification](../../experiments/adc-transcript/controls.toml) defines twelve new runtime arms,
thirteen malformed-input cases and the thirteen existing regression arms. All passed in
`out/guest-admission/group-adc-transcript-01`:

| Cases | Result |
| --- | --- |
| Full sequence followed by main/worker access | 452 accepted writes each; next read unanswered |
| Wrong second operand, wrong second offset, one-entry exhaustion | One accepted write each |
| Wrong order, worker store, 64-bit store | Zero accepted writes |
| Wrong live function binding, shadow, table word or source word | Zero accepted writes |
| Malformed input | Exit 2 before target creation/discovery |
| Existing arms 0–12 | All existing expectations retained |

Each runtime arm observed two initial threads and the fixture's third thread through its clone event. Every
terminal group was quiesced, killed and reaped with the final no-child result recorded. `system_server` stayed
at PID 1124 across all 28 samples; enforcement was enabled before and after. The stock package was absent.
The emulator and dedicated local services were stopped after capture.

## Independent verification

The private program issues its commands from a compiled reference array, while the observer loads the
expected transcript from a separate input buffer. The compiled bytes were independently extracted and
matched to the pinned stock fixture. Deliberate mismatches test the comparison and rejection paths.

The frozen run verifier passed. A subsequent review strengthened the current verifier: private function
bindings are now tied to symbols in the executed ELF, and data pointers to independently checked AArch64
fixture offsets. The same captured evidence passed that stronger verifier without a guest rerun. Mutated
evidence with a self-consistent but false reported binding or a changed non-PC post-store register is rejected.
The [result manifest](../../experiments/adc-transcript/control-results.toml) pins both verification versions.

The private fixture explicitly updates its own software shadows after its complete command sequence. This
tests capture and sequencing; it does not prove the stock ADC routine performs the predicted transformation.
That remains the next task. Terminal ADC capture reads the objects whose bindings were checked initially;
it does not prove that their GOT slots or shadows remained unchanged between observations. SPU pointers are
checked again at capture, but the captured values make no hardware-semantic claim.

The protocol has capacity for 512 writes. This consumer deliberately accepts only prefixes of its pinned
452-write reference; an otherwise well-sized 453-entry private input is rejected. The shared runtime deadline
remains ten seconds, and is checked even when wait events remain available. No device behavior, readback,
interrupt, timing response or DMA state was added.

Proceed to the already admitted stock ADC task using this exact tested native executable, the pinned stock
input and a fresh guest. Validate the live bindings and initialized shadows, accept only the ordered region,
and stop at any divergence or the next access. Commit and push this conclusion before that run.
