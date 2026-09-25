# Private exclusive-operation observer comparison

The private comparison reproduced a consistent difference: continuous execution completed the exclusive store on
its first attempt; instruction stepping failed all eight attempts. Both results repeated in the same pinned API-25
ARM64 guest. This supports an observer-effect explanation for the earlier
[stock libc retry trace](xdma-two-word-profile.md), while leaving the exact mechanism unresolved.

This experiment did not install or launch Sparrow, supply device responses, or modify stock artifacts.

## Observed result

Run `exclusive-01` completed on 2026-09-25 UTC. All arms used the same 6,640-byte ELF and fresh private children.
These are repetitions within one guest boot, not independent guest replications.

| Arm | Resume mode | Attempts | Store status | Initial → final word | Observer steps |
| --- | --- | ---: | ---: | --- | ---: |
| 0 | Continuous | 1 | 0 (success) | 1 → 0 | 0 |
| 1 | Instruction stepping | 8 | 1 (failure) | 1 → 1 | 67 |
| 2 | Instruction stepping | 8 | 1 (failure) | 1 → 1 | 67 |
| 3 | Continuous | 1 | 0 (success) | 1 → 0 | 0 |

Each arm reached its own terminal `brk` at `0x210fac` with signal 5/code 1 and matching signal address. Each
supervisor exited 0 after terminating and reaping its child with status 9. Stepped arms recorded failure status
1 for every exclusive store and reached the eight-attempt bound within the unchanged 128-step observer budget.
Continuous arms recorded one successful store and left the seven unused status slots at their initial sentinel.

The independent Kotlin verifier checked the ELF instruction words, trace ordering, branch destinations, relevant
register values, memory/status agreement, bounds and same executable bytes across all four arms. It reports the
outcome without requiring a particular mode to succeed. A separate copied capture with a contradictory terminal
word and a regenerated hash index was rejected; the original capture was untouched.

`system_server` retained PID 1057 across the root-adbd restart and all four arms. Both enforcement samples read
`Enforcing`; package and process checks found no Sparrow or Frida execution. Cleanup acknowledged emulator
shutdown, and all four reserved experiment ports were free afterward. No additional guest run was performed.

## Hypothesis and controls

Instruction stepping may prevent an exclusive store from succeeding even when the same sequence completes under
continuous execution. The comparison uses one freestanding native ELF and four fresh process invocations, in
continuous–stepped–stepped–continuous order. Each invocation creates a single-thread child with `clone(SIGCHLD)`
and a private address space. Its initialized halfword is 1; it attempts to store 0. No other process writes that word.
The child writes the initial word and log entries before its first stop, resolving copy-on-write pages before
the compared sequence begins.

Both modes use the same initial traced stop and terminal handling. The selected observation regime uses either
`PTRACE_CONT` or `PTRACE_SINGLESTEP`; stepping also adds the corresponding stops, instruction reads and register
snapshots. The parent never writes the child's registers, instructions or memory. Both modes read initial and
terminal memory.

The child executes adjacent `ldxrh w10, [x19]` and `stlxrh w11, w8, [x19]`, matching the operations and operands
in the observed libc loop. It records the store status into a private eight-element array after each store attempt,
increments an attempt counter, and stops retrying on success or after eight attempts. The status-log write is outside
the exclusive pair. The same counter and logging instructions execute in both modes.

Both paths end by executing the program's own `brk #0x123` instruction. The observer requires the expected terminal
PC and opcode, signal 5/code 1, and matching signal address. Intermediate step stops require signal 5/code 4 and
signal address equal to PC, as established for this guest. A fixed 128-resume budget bounds stepped observation.
At the terminal or an unexpected stop, the supervisor terminates and reaps the child. No stock code is involved.

The [fixture](../../experiments/guest-exclusive-control/fixture.toml) pins the arm order, limits and expected stop
semantics. The native-language exception is confined to the ARM64 instruction fixture and Linux guest observation
ABI; independent evidence verification uses Kotlin with explicit event and register types.

## Guest and evidence boundaries

The existing launcher validates guest image and tool inputs before boot. Its new private-control mode selects
`admission-exclusive.sh`, which restarts guest adbd as root for the private controls and retains SELinux enforcement.
It does not invoke APK installation, Frida, labeling or admission-policy helpers. The outer launcher still checks
its existing local APK/tool inputs; those host-side checks do not execute the application in the guest.

The harness records system-server identity across root-adbd restart and every arm, enforcement before and after,
package absence and process inventories. It pulls the executed control binary after each arm so their hashes can
be compared to the input ELF. The raw evidence index includes those ELF files and the runtime source snapshot.
All raw artifacts remain under ignored output directories.

This is a control of observer effects in a particular emulator/kernel combination. It does not determine the
physical instrument's exclusive-monitor behavior, register semantics, or the exact kernel mechanism responsible
for any difference. A stock inference must remain separate from this private comparison.

The [results manifest](../../experiments/guest-exclusive-control/results.toml) pins source, fixture, input ELF,
raw index, individual captures and verification outputs. The verifier used for the run matches its captured source
snapshot. Guest and runtime input manifests remain the existing pinned baseline and admission manifests.
Input validation comes from the launcher's preflight hash checks; the Kotlin verifier does not independently
interpret those manifests. Teardown is supported separately by cleanup and post-run port evidence.

## Decision and next question

In this private control, the observation regime is sufficient to change exclusive-store progress without competing
writers. The result does not distinguish stepping exceptions, scheduling, trace reads or their combination as the
underlying mechanism. The stock mutex retry is consistent with this effect; it is not independently reproduced
here because Sparrow was absent. Increasing the stock instruction budget is therefore not the supported next step.

The next bounded question is whether a hardware execution breakpoint can stop a private child at a selected PC
after this sequence runs continuously, with the same successful memory/status outcome as the continuous control.
That would test an observation boundary compatible with unmodified synchronization instructions. Its private
controls should establish breakpoint availability, stop semantics, precise PC, success state and an unexpected-stop
case before any stock adaptation. Lack of support or an unexpected stop is a valid result, not a reason to change
guest policy or force a stock mutex return.

For a later stock experiment, mapped-register observation would remain at the known device reads. A validated
execution stop could replace instruction stepping through intervening libc code. It would trade per-instruction
visibility for progress to a precise boundary; read-only terminal inspection would still need to establish any
global store, and thread coverage and intervening device accesses would remain explicit limitations. A software
instruction replacement would add code mutation, while intercepting a mutex return would change stock behavior;
neither is justified by this result. No successor experiment is admitted or executed by this report.

## Reproduction

Configure `NATIVE_CC`, `NATIVE_LD` and `ANDROID_SDK_ROOT` locally, then use a fresh run ID:

```sh
tools/guest/build-exclusive-control.sh
tools/guest/run-admission.sh fresh-run-id exclusive
kotlin tools/guest/VerifyExclusive.main.kts out/guest-admission/fresh-run-id
```
