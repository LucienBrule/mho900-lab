# Stock stopped-thread coverage

Run `stock-thread-coverage-01` established a converged snapshot of all 21 currently live Sparrow threads. The
observer discovered the set from the stock PID, seized and interrupted each member, then confirmed the same
live set on a second enumeration. Every final status record had the stock thread group, this observer as tracer,
and tracing-stop state. All 21 threads were then terminated and reaped, followed by `ECHILD`.

The device path remained absent before and after observation. No modeled mapping or register response was supplied,
and the observer never resumed the converged stock set. This proves a coverage establishment boundary, not stock
initialization progress under the wider observer. The earlier [stock state witness](xdma-post-store-witness.md)
remains the evidence for the two mapped responses reaching `m_DNA`.

## Evidence

The observer is byte-identical to the executable used for the preceding [private discovery controls](guest-thread-discovery.md).
The original composite and three individual process-snapshot commands returned zero; 988 map rows and the stock
name/label were independently validated before attachment. No clone event or exit race occurred during the stock
setup. The final checker validated thread membership, identities, stop accounting, executed ELF, exact cleanup,
raw evidence index, admission controls, stored certificates and stock artifact preservation.

`system_server` remained PID 1081 across all outer and final helper samples. Final enforcement was `Enforcing`,
normal instrumentation detachment completed, and the emulator shut down with experiment ports free. The stock APK
and embedded native library retain their pinned hashes. No physical instrument was accessed.

The [results manifest](../../experiments/guest-thread-discovery/stock-results.toml) pins the capture and review.
The bounded read-only code review found no false-positive convergence path for the successful stable-set case.
That review is an actor assertion, not another runtime witness. It identified conservative failure paths around
short-lived clone/exit races and noted that only successful cleanup proves exact reaping.

## Decision and limits

The current-live stopped-set claim is supported. It cannot exclude a thread that appeared and exited entirely
between enumerations, establish earlier device-access history, or prove future signal handling and ordering.
The earlier run had 22 threads; this run's count of 21 is observed process state, not a fixed fixture requirement.

Admit a bounded integration that reuses the same two guarded stock responses and post-store hardware stop, while
all discovered threads resume normally under observation. Worker mapped faults and new-thread events must be
accounted for or cause an explicit stop; siblings must not remain frozen while initialization needs them.
Verify that the known `m_DNA` state witness still holds with the wider observer before following the next
externally unsatisfied initialization dependency. No additional register value is justified by this coverage run.

```sh
tools/guest/build-thread-coverage.sh
tools/guest/run-admission.sh fresh-stock-coverage coverage
kotlin tools/guest/VerifyCoverage.main.kts out/guest-admission/fresh-stock-coverage stock
```

Compiler, linker and SDK locations are local configuration. The existing narrow admission fixture and its
restoration checks remain part of the research environment.
