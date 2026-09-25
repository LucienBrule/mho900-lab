# Decision: recover the initialization tail before modeling returned state

The [stock region result](stock-remaining-initialization.md) matched all four predicted
SCU/LA stores and ten transport checkpoints. The next unanswered access is the first
mapped version read. Natural guest device absence permitted the recovered failure
paths to return; no UART or GPIO model was needed for this branch.

Continue static-first. Recover the whole remaining `Drv_Init(bool)` region through its
return paths, including transitive version, DAC, DDR skip-tap/reset and self-test
routines. Preserve software call ordering, loops, mutable selectors, masks and error
propagation in a typed operation graph. Extend recovery to the immediate caller only
far enough to identify how initialization success/failure is consumed and where the
next subsystem begins. Explicit unknown leaves are preferable to silent expansion.

The existing graph already shows three version reads (`4`, `0`, `0x401c`), their
immediate logging consumers, a DAC timing candidate and a writable DDR selector. The
DDR body remains unresolved. Choosing version values merely to advance to that body
would spend a guest run without answering the larger returned-state question.
Recover the body and its read dependencies first. A deterministic write derived from
code is a candidate operation, not evidence for its physical effect. A poll predicate
can define a synthetic response hypothesis without establishing reset state, latency,
read side effects or actual FPGA completion.

Use the pinned stock library as the software-consumer authority. Correlate any newly
reached device interfaces with the already pinned kernel/reference ABI only where
relevant; a BAR-mapped load does not acquire FPGA semantics from the driver. Keep
static determination, runtime selection, hardware-returned state, asynchronous behavior
and unknowns distinct. Table and loop expansion should remain reproducible and retain
branch predicates rather than becoming a flat unconditional list.

Admit two tasks: recover and independently check this bounded graph, then choose a
selective falsification batch using its real decision points. No guest run, new
register response, observer change or physical access is part of this static batch.
The decision must identify coherent fixture values, exact observation scope, thread
coverage, negative controls and a terminal boundary before runtime implementation.
Retain mapped-access observation unless the recovered contract exposes a specific
limitation that justifies a different boundary. Commit and push tasking before work.
