# Stock state transition with thread coverage

Run `stock-group-post-store-01` reproduced the known stock two-read-to-`m_DNA` transition while all 22 discovered
Sparrow threads resumed under the integrated observer. The byte-identical observer had first passed the
[private positive and negative controls](guest-group-observer.md). Exactly two responses were supplied, both
to the guarded main-thread load at ELF `0x270604`: `0xe1234567` at offset `0x4048`, then `0x89abcdef` at `0x4044`.

The stock open and original 16 MiB shared read/write mmap request were captured before substitution with the
private inaccessible mapping. Continuous execution after the second response reached the hardware breakpoint
at ELF `0x42a8f0`, immediately after stock's store. The observed global value and `x8` were
`0x0123456789abcdef`; `x9` identified the stock `m_DNA` object at ELF `0xbbccf0`. The final quiesced read agreed.
The stock APK and native library retain their pinned bytes.

## Coverage and preservation

Two enumerations converged on 22 threads before the device path appeared. All were traced and stopped at that
boundary, then all resumed. There were no runtime clone or exit events in this stock interval and no worker
mapped fault. At the post-store boundary, all 21 siblings produced accounted-for interrupt stops. The terminal
inventory again contained 22 traced, stopped members. Exact cleanup reaped all 22 and ended in `ECHILD`.
This is observed coverage for this run; the private controls separately exercise worker faults and new threads.

The independent checker validates the original request, executed ELF, stock load/store/stop instruction binding,
all modeled register changes, hardware breakpoint setup and actual delivery, live-thread accounting, terminal
state, cleanup, raw evidence index and admission controls. The frozen snapshot checker verified 993 map rows and
all three individual snapshot commands. Both composite and individual commands returned zero.

`system_server` remained PID 1049 across outer and final helper samples. Final enforcement was `Enforcing`.
Normal admission instrumentation detachment and restoration checks passed. The emulator was torn down after
capture; no physical instrument was accessed. The [results manifest](../../experiments/group-observer/stock-results.toml)
pins the evidence and checker output.

## Decision

The broader observer preserves the known state transition. Continue with the same two synthetic responses and
normal execution beyond this already-proven store. Stop at the first unsupported mapped access on any covered
thread, or explicitly classify a different fault, signal, exit or exhausted observation bound. Supply no third
value in that experiment. Capture enough state to identify the next externally unsatisfied initialization dependency.

Do not spend another batch decoding the identity transform without a witnessed need. This fixture establishes
synthetic program state, not a physical instrument identity. No acquisition behavior, interrupt semantics,
register ordering or DMA contract has been established. Continuous execution and recorded stop order do not
constitute a global hardware-access ordering guarantee.

```sh
tools/guest/run-admission.sh fresh-stock-group groupmodel
kotlin tools/guest/VerifyGroupObserver.main.kts out/guest-admission/fresh-stock-group stock
```

Use the exact native binary pinned by the private-control results; a changed observer requires fresh controls.
