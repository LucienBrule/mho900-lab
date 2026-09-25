# Integrated thread-aware observer controls

Run `group-observer-01` passed three private controls before any stock execution with the integrated observer.
The fixture requires an existing sibling to acknowledge progress and then creates another worker under observation.
Both the sibling acknowledgement and one runtime clone were independently verified in every arm.

| Arm | Witnessed behavior | Responses | Terminal result |
| --- | --- | ---: | --- |
| Positive | Main-thread reads at `0x4048`, then `0x4044` | 2 | Composed value `0x0123456789abcdef` stored; precise post-store stop |
| Wrong second offset | Main-thread second read at `0x4040` | 1 | Guard rejection; output remains all ones |
| Worker access | Existing worker reads `0x4040` after the first main read | 1 | Worker attributed and rejected; output remains all ones |

The positive arm uses continuous execution after the second response and the previously established hardware
breakpoint profile. The verifier binds the actual load/store/stop instructions to the executed ELF, compares
all response registers, and checks the delivered stop. No response is supplied to either unsupported access.

All arms converge on two initially stopped threads, resume both, observe a third thread's creation, and
quiesce all three at the terminal boundary. Every terminal inventory reports the expected tracer and tracing-stop
state. Exact group cleanup reaps all three members and ends in `ECHILD`. The worker-negative arm includes a
pending main-thread syscall stop during quiescence; it is recorded and checked rather than discarded.

`system_server` remained PID 1052 across five samples. Both enforcement samples were `Enforcing`; stock Sparrow
was absent. The compiled observer and all three executed copies are byte-identical. Raw evidence hashes and
captured sources were validated. The emulator was torn down. No physical instrument was accessed.

The [results manifest](../../experiments/group-observer/results.toml) pins the implementation, capture and checker.
A read-only code review found no path supplying a third or worker response, or knowingly inspecting terminal
state with a tracked thread still running. This is a review assertion, separate from the runtime evidence.

## Scope and continuation

These controls establish this private protocol, not all possible thread schedules. Discovery and execution share
a ten-second deadline. Unknown signals, events, identities and exhausted bounds stop the experiment. Short-lived
clone races, leader exit and TID reuse remain conservative failure cases. The independent verifier currently
accepts the stable two-pass setup observed here; setup churn requires separate adjudication.

Proceed to the already admitted stock integration with the identical native executable, exactly the existing two
synthetic words, and the known stock post-store boundary. Observe worker accesses without answering them. No third
register value or physical identity claim follows from these controls.

```sh
tools/guest/build-group-observer.sh
tools/guest/run-admission.sh fresh-group-controls groupcontrol
kotlin tools/guest/VerifyGroupObserver.main.kts out/guest-admission/fresh-group-controls
```
