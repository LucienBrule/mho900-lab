# Profiled post-atomic breakpoint delivery

Both matching breakpoint controls fired at the intended post-sequence PC after first-attempt exclusive-store
success. Continuous and deliberately nonmatching controls reached the fallback software trap, also after
first-attempt success. This establishes a synchronization-compatible private observation boundary in this guest.

This successor preserves the [setup-negative capture](guest-execution-stop.md) and changes one expectation:
readback control `0x1e4` is recognized under an explicit profile after requesting `0x1e5`. The address, metadata,
control type/length/privilege and unused slots remain checked. No repeated programming is used to seek a different
readback. Actual delivery, not successful setup, is the required witness.

The same five-arm design runs continuous, matching, nonmatching, matching, continuous controls in a fresh pinned
guest. The breakpoint remains after the entire bounded exclusive sequence. Every arm uses one compiled ELF,
fresh private child state, eight-attempt limit and continuous resume. The parent observes one terminal stop,
captures registers and memory, and terminates/reaps the child. There is no stock execution or device response.

The fixture builds with `EXECUTION_PROFILE=cached-enable`, which selects a separate local binary directory and
records the compile-time profile. The [profile manifest](../../experiments/guest-execution-stop/profile.toml)
identifies the original capture and expected semantics. The original strict mode remains available.

## Observed result

Run `execution-profile-01` completed on 2026-09-25 UTC in one fresh guest. All five arms used the same 10,872-byte
ELF. Each stored 0 over initial word 1 on its first attempt; all remaining status-log entries retained their sentinel.

| Arm | Mode | Stop code | Stopped PC | Store status | Attempts |
| --- | --- | ---: | --- | ---: | ---: |
| 0 | Continuous | 1 | `0x21109c` | 0 | 1 |
| 1 | Matching breakpoint | 4 | `0x21109c` | 0 | 1 |
| 2 | Nonmatching breakpoint at `0x2110a0` | 1 | `0x21109c` | 0 | 1 |
| 3 | Matching breakpoint | 4 | `0x21109c` | 0 | 1 |
| 4 | Continuous | 1 | `0x21109c` | 0 | 1 |

Every stop was signal 5 with signal address equal to PC. Breakpoint arms requested control `0x1e5` and read back
`0x1e4` with the intended address, metadata `0x0606` and zero unused slots. Each supervisor exited 0 after
terminating/reaping its child with status 9. No setup retry or additional guest run was performed.

The typed Kotlin verifier checked the complete event sequences, ELF loop bytes, exact target and signal class,
debug state, relevant terminal registers, status-log and memory agreement, all executable hashes and guest checks.
Its source matched the pre-run snapshot. Strict mode rejected the profiled capture, so the new expectation is not
silently applied to old experiments. `system_server` retained PID 1036 across root-adbd restart and all arms;
both enforcement samples were `Enforcing`. Stock hashes remained unchanged. Cleanup acknowledged shutdown and
the four reserved ports were free. The [results manifest](../../experiments/guest-execution-stop/profile-results.toml)
pins source and evidence.

## Decision

Use this observation primitive for a bounded stock two-word continuation. A tighter target than the earlier
pre-converter boundary is ELF PC `0x42a8f0`, immediately after `str x8, [x9]` at `0x42a8ec`. At that stop, capture
the source register, destination register, relocated global pointer and stored value. The expected composition
from the already selected two words remains `0x0123456789abcdef`. This asks whether stock code delivers the
synthetic input into application state without inspecting the later transform.

The private result does not establish stock delivery, multithread coverage or physical instrument behavior.
The proposed stock batch must preserve the two existing response guards and stop at any other observed access.
It must inventory threads before and at the boundary, record each thread's supervision status, and explicitly
limit any ordering claim to the traced thread. A separate coverage decision is required before growing the
device model beyond those two reads. Do not freeze sibling threads merely to simplify evidence; that could
introduce another synchronization disturbance.

## Reproduction

Configure `NATIVE_CC`, `NATIVE_LD` and `ANDROID_SDK_ROOT`, then run:

```sh
EXECUTION_PROFILE=cached-enable tools/guest/build-execution-stop.sh
EXECUTION_PROFILE=cached-enable tools/guest/run-admission.sh fresh-run-id execution
kotlin tools/guest/VerifyExecutionStop.main.kts out/guest-admission/fresh-run-id cached-enable
```
