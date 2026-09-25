# The next stock access is a register write

Run `stock-next-access-01` continued beyond the established identity store with only the two existing synthetic
reads. The next observed access was a main-thread 32-bit store through `Dev_WriteRegister`:

| Field | Observed value |
| --- | --- |
| Device-relative byte offset | `0x3000` |
| Value in `w9` | `0x05630000` |
| Stock ELF PC | `0x27043c` |
| Instruction | `0xb9000109`, `str w9, [x8]` |
| Completed modeled reads | 2 |
| Completed modeled writes | 0 |
| Terminal `m_DNA` | `0x0123456789abcdef` |

The store was captured before completion and received no response. No post-store breakpoint was installed.
All threads used normal continuous resume after the second read. The run began with 21 covered threads and
observed one new thread created by the main thread. All 22 terminal members were traced, stopped and exactly
reaped, followed by `ECHILD`. There was no runtime thread exit or unsupported worker access before this boundary.

## What the stock implementation suggests

The pinned stock library's `Dev_WriteRegister` locks a mutex, obtains the mapping, adds the zero-extended offset,
and stores the supplied 32-bit word at the witnessed instruction. The normal path then sets its local return
status to zero and unlocks. This establishes instruction semantics; it does not establish device-side effects.

Static `Dev_AdcWrite` at ELF `0x2717c8` constructs a command from two 16-bit arguments and a mode. Mode zero,
arguments `(0, 0x63)`, produce exactly the observed `0x05630000` at offset `0x3000`. The routine then masks the
command with `0x03ffffff`, calls `usleep(100)`, and writes the resulting word to `0x3000` again.
`DevAcquireADC_Init` contains loops calling this routine. ADC initialization command programming is therefore
a supported static candidate for the observed operation. The current capture has no runtime stack, so the exact
caller and table entry remain inferred. Neither names nor matching constants establish physical ADC/FPGA behavior.

The public Orange-Rigol XDMA reference explains how mapped writes reach a BAR; it supplies no semantics for
this register or command. Its role remains [transport reference](xdma-boundary.md), not confirmation of the
candidate ADC operation or MHO984 hardware effects. The words supplied at `0x4048/0x4044` remain synthetic inputs.

## Verification and preservation

The observer checker validates the two responses, byte-matched stock instruction at the terminal PC, mapped
fault geometry, thread and clone accounting, final state, exact cleanup and raw evidence index. The stock APK
and native library are unchanged. Snapshot validation accepted 988 map rows. `system_server` remained PID 1058,
final enforcement was `Enforcing`, and the guest was torn down. No physical instrument was accessed.

The initial full check stopped at the reused admission checker's requirement for native exit zero. This run
correctly uses exit 78 for the unsupported mapped boundary, while its orchestration helper returns zero.
The original capture and failed check are preserved. An explicit `admission-next-access` profile now requires
that exact pair, and a pinned offline verifier override validates the existing capture without rerunning it.
The old zero-exit profile still accepts the earlier stock witness and rejects this run. This is a checker
contract correction, not a changed experiment or an ignored guest failure.

The [results manifest](../../experiments/group-observer/next-stock-results.toml) pins runtime evidence, static
extracts, the failed and corrected checks, and the separate read-only continuation review assertion.

## Decision

Admit a one-write experiment: after the same two reads, permit only the observed main-thread store at exact PC,
opcode, offset and value. Record it in an observer-side write ledger and advance PC by four while preserving all
other registers. Keep the mapping inaccessible and stop at the next access from any observed thread.
Do not supply a new read value, accept an arbitrary write stream, or claim ADC completion, timing fidelity or
hardware side effects. Private controls must test the single-write bound and rejection of altered operands.

The static candidate predicts a second word `0x01630000` at the same offset, but that is a hypothesis for the next
capture. It is not admitted as a response or a completed write by this decision.

```sh
tools/guest/run-admission.sh fresh-next-access nextmodel
kotlin tools/guest/VerifyGroupObserver.main.kts out/guest-admission/fresh-next-access next-stock
# The historical capture needs the explicit corrected admission checker:
kotlin tools/guest/VerifyGroupObserver.main.kts out/guest-admission/stock-next-access-01 next-stock tools/guest/VerifyNative.main.kts
```
