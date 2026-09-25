# Two-word observation with a pinned guest step profile

All six private controls passed. Stock Sparrow received exactly the two configured register words, then exhausted
the fixed step budget in guest libc's mutex-unlock retry loop. The stock composition and global store still have
no dynamic witness. The next question concerns the observer's effect on exclusive operations.

This is the deliberate successor to the [rejected private step control](xdma-two-word.md), preserved in commit
`f0e654b`. Its tasking was admitted and pushed in `b2e97b6` before execution. The original raw capture and source
snapshot remain unchanged.

The sole behavioral adjustment to the native observer is its single-step stop guard: require `SIGTRAP`, code 4,
and a signal address equal to the stopped PC. The observed private stop and pinned Linux 3.18 ARM64 reference
support this guest-specific choice. The observer does not accept arbitrary trap codes.

The [profile](../../experiments/xdma-two-word/profile.toml) names guest release `3.18.91+` and kernel SHA-256
`3112e2210d65c276b067e6cfdd1c26caa95e45061cb08893cccd03f82f76407b`. The outer harness validates this kernel
against the baseline input manifest before guest startup; the inner helper additionally checks `uname -r`.
This pins the binary guest input without claiming that the upstream reference is its exact source.

The fixture remains high word `0xe1234567` at mapped offset `0x4048`, followed by low word `0x89abcdef` at `0x4044`.
The expected masked value is `0x0123456789abcdef`. The two-response ceiling, 256-step budget, four width/direction
controls, positive composition control and unexpected-second-access rejection control are retained. All private
controls must pass before the helper attaches to stock Sparrow.

The intended stock boundary remains ELF PC `0x42a2b4`, immediately before the converter call. Successful evidence
must include the stock global store, its source value and destination, the value read after that store, and the
value at the final stopped boundary. Step instructions are checked against the unchanged stock native ELF or the
captured guest libc, according to their executable mappings. Unknown mappings and unexpected events are rejected.

Observation remains scoped to the main thread. Other application threads are untraced. The guest uses the existing
scoped admission/process-label fixtures; their policy effects remain explicit. Stock APK and library bytes are
preserved. No physical instrument was accessed and no host security policy was changed.

## Observed result

Run `two-word-profile-01` passed the four width/direction controls, the three-instruction positive composition
control, and the unexpected-second-access rejection control. The positive control stored `0x0123456789abcdef`
and stopped at its own named boundary. The negative control received only its first response and exited 78.
This validates the private controls; it does not substitute for stock composition evidence.

The stock observer supplied `0xe1234567` and `0x89abcdef` at the two expected faults in stock accessor PC
`0x270604`, opcode `b9400109`. It then recorded 256 single-step stops, all signal 5/code 4 with signal address
equal to PC. Every recorded instruction matches its stock ELF or captured libc bytes.

Steps 20 through 255, 236 steps in total, repeat the following guest libc sequence:

| libc ELF offset | Instruction | Observed next offset |
| --- | --- | --- |
| `0x68cb0` | `ldxrh w10, [x19]` | `0x68cb4` |
| `0x68cb4` | `stlxrh w11, w8, [x19]` | `0x68cb8` |
| `0x68cb8` | `cbnz w11, 0x68cb0` | `0x68cb0` |

These instructions lie in `pthread_mutex_unlock`, at libc symbol address `0x68c88`. The observed branch back
is consistent with unsuccessful exclusive stores. The final recorded PC was libc offset `0x68cb8`, after the
last store attempt. No third device access, global-store event or pre-converter boundary was recorded on that thread.
The supervisor emitted `step-budget-exhausted`, killed the stock process, observed termination status 9 and
exited 72. The budget was not enlarged and the run was not repeated.

The byte-identical stock APK and native library were verified independently. `system_server` remained PID 1056
across three samples, SELinux reported enforcing, and guest teardown completed with all experiment ports clear.
The initial application inventory contained 21 thread IDs; only the main thread was traced. Sparrow did not reach
a useful UI. The outer harness completed evidence collection successfully; its helper's exit 72 is the experiment
outcome, not a successful composition observation.

## Evaluation and next question

The code-4 profile is supported by the complete private controls and the stock step trace. The two-response
primitive reaches the expected stock accessor twice. Instruction-level stepping then fails to make progress through
an exclusive-operation loop in a runtime library, before returning to the caller that assembles the words.

Observer disturbance is the leading hypothesis: stopping between exclusive load and store may prevent completion.
The cause is not established by this run. Other threads remain untraced, and no uninterrupted comparison of this
atomic sequence was performed. Do not assign the retry loop to missing instrument behavior or supply further
register responses to address it.

The next bounded experiment should compare the same private exclusive-operation sequence under instruction
stepping and uninterrupted execution, with identical inputs, a finite retry bound and an explicit terminal stop.
If that isolates observer disturbance, evaluate an observation method that lets synchronization execute normally
and stops at the desired stock boundary. No mutex implementation, stock instruction or return value should be
changed merely to make the composition test advance.

This batch ends at the observer finding. It admits no additional guest run. An independent read-only review
checked the control results, retry sequence and distinction between observation and causal hypothesis.

## Evidence and verification

[profile-results.toml](../../experiments/xdma-two-word/profile-results.toml) pins the fixture/profile, source
snapshot, native observer, stock run evidence index, captured libc and disassembly, verification and teardown.
The post-run `two-word-budget` verifier mode explicitly checks this negative outcome, including event order,
instruction bytes, exact step count, repeated retry sequence, termination and absence of global-store evidence.
The ordinary `two-word` success mode rejects this capture. The runtime source snapshot predates the added
negative-outcome verifier mode and remains intact.

To check the preserved run without starting a guest:

```sh
kotlin tools/guest/VerifyPairControls.main.kts out/guest-admission/two-word-profile-01
kotlin tools/guest/VerifyNative.main.kts out/guest-admission/two-word-profile-01 two-word-budget
```
