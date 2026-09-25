# Initialization-tail direct handoff controls

The fresh private run `out/guest-admission/group-init-tail-handoff-01` passed all
17 controls, all 59 earlier runtime controls and 30 malformed-input controls.
It ran from `2026-09-25T10:40:44Z` to `2026-09-25T10:43:17Z`. No stock application
was installed or executed. The [hardware candidate](../../experiments/init-tail/candidate.toml)
remained unchanged.

The initial transition observed inherited slot zero address `0`, control `0x1e5`,
info `0x0606` and empty unused slots. Direct SET24 of checkpoint zero/control
`0x1e5` followed by GET264 returned the checkpoint address/control `0x1e4`.
All general registers, SP, PC and PSTATE were preserved. No redundant initial
clear was performed. After delivered checkpoints, clearing returned address `0`
and cached control `0x1e5`; subsequent arming and final clearing passed.

Positive arms 59 and 72 each completed ten tail reads, two writes and three
checkpoints after the 464-write prefix. Each private exclusive sequence completed
before its checkpoint, with final atomic count three. Arm 72 also executed the
old checkpoint site without an unwanted stop. Neither reached the calibration
sentinel. These are private observer controls, not evidence of stock execution or
physical register semantics.

The negative controls rejected changed offset, width, thread, operand, binding,
initial state, parent output, ready byte and checkpoint configuration. The tap
output control changed its upper 32 bits, testing the full 64-bit output. An
extra mapped read stopped the sequence, and the deadline control terminated.
Arm 75 deliberately armed the private checkpoint before the ordinary initial
guard; that guard rejected the occupied slot with zero tail accesses and zero
accepted checkpoints. This preparation remains unavailable in stock mode.

The frozen verifier independently checked ordered accesses, instruction words,
register changes, output widths and values, live bindings, debug transitions and
thread inventories. An unchanged evidence copy passed; twelve independently
altered copies failed. The preservation audit verified all 647 indexed artifacts,
83 unchanged `system_server` samples (PID 1085), enforcement, package absence,
stock input hashes, frozen source digests and absence of dedicated listeners.
Every new control reaped its three registered threads and ended with wait `-10`.

The prior [negative run](init-tail-clear-negative.md) and executable are preserved.
The new executable is pinned by
[handoff-results.toml](../../experiments/init-tail/handoff-results.toml).
This closes the observer hypothesis positively. A separate decision must bind
the waiting stock experiment to this exact executable before execution.
