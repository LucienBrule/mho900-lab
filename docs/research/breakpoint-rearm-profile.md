# Breakpoint clear and rearm profile

The first remaining-initialization control exposed a wrong cleared-state assumption.
Choose a fixed, phase-specific readback profile for the next private experiment while
retaining the complete four-store, ten-checkpoint region. Actual checkpoint delivery,
atomic progress and an old-site revisit must establish that rotation works; cached
control bits alone cannot do so.

## Evidence and reference explanation

Direct guest evidence establishes only the initial transition: empty slot 0, successful
address-zero/control-zero SET, then address zero and control `0x1e4` on GET. The observer
stopped before arming a target. Its raw evidence and executable remain preserved in
[the negative control](remaining-init-controls.md).

The inspected reference is upstream Linux v3.18 commit
`b2776bf7149bddd1f4161f14f79520f17fc1d71d`, already pinned by the earlier
execution-stop investigation. The four local source hashes match that prior manifest.
It is not proven to be the exact guest kernel source.

[ARM64 ptrace](https://github.com/torvalds/linux/blob/b2776bf7149bddd1f4161f14f79520f17fc1d71d/arch/arm64/kernel/ptrace.c)
processes the address before the control within each SET. Creating an absent slot creates
a disabled four-byte execution event. A disabled control request preserves its type and
length. GET returns the event address and the encoded cached architecture control.

[Generic breakpoint updates](https://github.com/torvalds/linux/blob/b2776bf7149bddd1f4161f14f79520f17fc1d71d/kernel/events/hw_breakpoint.c)
copy the address/type/length, skip architecture validation for a disabled request, and
assign the new disabled attribute at the end. During validation,
[ARM64 control construction](https://github.com/torvalds/linux/blob/b2776bf7149bddd1f4161f14f79520f17fc1d71d/arch/arm64/kernel/hw_breakpoint.c)
therefore reads the previous disabled attribute. Physical installation separately sets
or clears the enable bit according to debug state. This yields the following reference
derivation, which the next guest run must test rather than assume:

| Transition | SET address / control | Predicted GET address / control | Evidence status |
| --- | --- | --- | --- |
| Initial clear | `0 / 0` | `0 / 0x1e4` | Directly observed |
| Arm from disabled | `target / 0x1e5` | `target / 0x1e4` | Reference-derived; earlier single-stop controls support this case |
| Clear previously armed slot | `0 / 0` | `0 / 0x1e5` | Reference-derived, untested here |
| Rearm cleared slot | `next / 0x1e5` | `next / 0x1e4` | Reference-derived, untested here |

For armed clear, the address setter validates while the old event is enabled, leaving
cached control `0x1e5`; the following disable skips rebuilding that cache. Rearming first
changes the address while disabled, then validates the enabled request while the stored
disabled attribute is still true, leaving cached control `0x1e4`. An independent review
reproduced this ordering from the pinned source.

The encoding retains four-byte execute type at EL0 (`0x1e4` without the enable bit).
No relaxed mask or accept-either-enable-bit rule is selected. Require exactly the table's
phase-specific value, metadata `0x0606`, full GET size 264, first-slot SET size 24, and all
unused slots zero. Before each rotation, require the previous target and `0x1e4`.
The final clear uses the same previously-armed profile. Do not reprogram until a desired
readback appears; any other result is another terminal negative.

## Selected test and limits

Run the already defined private arms 40–58 with this profile and the existing 0–39
regressions. Preserve all general registers across debug operations and permit normal
execution between checkpoints. Require the atomic counter to reach each expected value,
old checkpoint 0 to execute without another trap in arm 53, exact successful-open
sentinel stops, divergence rejection, timeout cleanup, and the uncompleted final R4.
The verifier must require each SET result, readback and register-invariance event.

The only observer change is its clear/readback interpretation and exact profile metadata.
The ADC/SPU prefix, SCU/LA operands, transport predicates, two synthetic DNA reads and
protected mapping remain fixed. No new device result or hardware behavior is introduced.
The stock task stays behind the new control and explicit decision. Failure closes this
profile's question without modifying the captured experiment.

Passing these controls would establish the combined clear/rearm observer lifecycle in
this guest. It would not expose physical debug-register contents continuously, prove
that unrelated threads performed no transport work, or establish any FPGA behavior.

See [the pinned profile](../../experiments/remaining-init/rearm-profile.toml).
