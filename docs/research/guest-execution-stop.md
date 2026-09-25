# Private post-atomic execution stops

The first breakpoint arm stopped at setup because its read-back enable bit differed from the requested value.
No breakpoint-controlled execution occurred, so this run establishes neither delivery nor failure to deliver a
hardware breakpoint. The continuous baseline completed the exclusive store on its first attempt.

This batch asked whether a hardware execution breakpoint can observe a precise PC after an uninterrupted exclusive
sequence. The [preceding control](guest-exclusive-control.md) found first-attempt success under continuous execution
and eight failed attempts under instruction stepping, twice each in one pinned guest.

The private child and its bounded eight-attempt sequence are shared with that control. A breakpoint is placed on
its terminal `brk`, after the complete exclusive sequence and status logging. No exception is intentionally placed
between `ldxrh` and `stlxrh`. Every arm resumes with `PTRACE_CONT`; there is no instruction stepping.

## Controls and reference provenance

One fresh pinned API-25 ARM64 guest runs the same ELF in continuous, matching, nonmatching, matching, continuous
order. Each invocation creates a fresh single-thread private child, materializes its initial word and status log,
and stops before executing the sequence. The parent reads state and, where requested, sets only hardware debug
registers. It does not write general registers, code or data.

The matching breakpoint targets the terminal PC. The nonmatching breakpoint targets the following instruction,
which cannot execute before the terminal software trap. Thus the former should stop with signal 5/code 4 before
executing `brk`, while the latter and continuous controls should reach the software trap with signal 5/code 1.
The supervisor captures one stop and terminates/reaps its child. Setup failure, unsupported debug state or an
unexpected stop ends the experiment with its evidence retained. The harness bounds each arm to 30 seconds.

The reference is upstream Linux v3.18 at this
[pinned commit](https://github.com/torvalds/linux/tree/b2776bf7149bddd1f4161f14f79520f17fc1d71d):

- ARM64 ptrace ABI: `arch/arm64/include/uapi/asm/ptrace.h`.
- Debug control encoding: `arch/arm64/include/asm/hw_breakpoint.h`.
- Regset handling and signal delivery: `arch/arm64/kernel/ptrace.c`.
- Perf breakpoint attribute update order: `kernel/events/hw_breakpoint.c`.
- Architecture validation and installation: `arch/arm64/kernel/hw_breakpoint.c`.
- Register-set identifiers: `include/uapi/linux/elf.h`.

The expected `NT_ARM_HW_BREAK` state is 264 bytes: an eight-byte header and 16 address/control slots. Slot zero uses
an aligned PC and control `0x1e5` for an enabled four-byte user execution breakpoint. The fixture queries available
slots and initial state, writes the first 24 bytes, and reads the full state back before continuing. These are
reference-derived expectations; the guest capture determines whether this emulator/kernel actually supports them.
The upstream revision is not claimed to be the exact guest kernel source.

## Result and evaluation

Run `execution-stop-01` used one fresh guest and stopped after arms 0 and 1. Arm 0 reached the software trap at
`0x211084` with signal 5/code 1, word 0, store status 0 and one attempt. Arm 1 queried 264 bytes of debug state with
`dbg_info = 0x0606` and initially empty slots. Setting address `0x211084`, control `0x1e5` returned 0. Reading back
the state returned the same address and metadata, but control `0x1e4`. The supervisor emitted
`debug-readback-mismatch`, terminated/reaped the child with status 9, and exited 82 before resuming it.

The nonmatching and repeat arms did not run. `system_server` retained PID 1060; both enforcement samples were
`Enforcing`. No Sparrow package or process appeared. Cleanup acknowledged emulator shutdown and all four reserved
ports were free afterward. Stock APK and embedded library hashes remained unchanged. The original full-success
verifier rejected this incomplete capture, as required. A separate post-run negative verification mode checks the
actual baseline, exact readback mismatch, absence of execution in arm 1 and bounded termination.

The pinned reference gives a plausible explanation for the readback. `ptrace_hbp_get_ctrl` encodes the architecture's
cached control. During `modify_user_hw_breakpoint`, address/type/length are updated before validation, but the new
`attr.disabled` value is copied afterward. Architecture validation derives the cached enable bit from the previous
disabled attribute. Architecture installation separately writes the physical enable bit according to debug state.
Consequently a cached readback of `0x1e4` after an enabled request is consistent with this reference path and does
not alone establish that the installed breakpoint is disabled. This is reference-derived explanation, not a trace
of the actual guest kernel's internal state.

The next bounded question is delivery under an explicit profile for this observed readback: keep exact address,
type, length, privilege and metadata checks; recognize the cached enable-bit difference; then require the actual
post-sequence hardware trap as the success witness. Retain continuous and nonmatching controls. Do not reprogram
until a desired readback appears. A fallback software trap would be a reproducible negative delivery result.
This changes the tested expectation in a successor batch, not the already captured run. Thread coverage remains
a separate gate before expanding stock device behavior.

## Limits

The private child does not create threads. This establishes no stock thread coverage. Hardware debug state is per
thread in the reference implementation, so any stock adaptation must record the live thread set and state exactly
which threads are supervised. Shared mapping access and newly created threads require explicit treatment before
extending the device model. A stopped main thread alone cannot establish process-wide ordering.

No Sparrow installation or launch, synthetic device response, stock artifact edit, enforcement change, physical
instrument access or host policy change is part of this batch. Native C/assembly is confined to the guest ABI and
instruction fixture; semantic evidence verification is Kotlin.

## Reproduction

Configure `NATIVE_CC`, `NATIVE_LD` and `ANDROID_SDK_ROOT`, then use a fresh run ID:

```sh
tools/guest/build-execution-stop.sh
tools/guest/run-admission.sh fresh-run-id execution
kotlin tools/guest/VerifyExecutionStop.main.kts out/guest-admission/fresh-run-id
```
