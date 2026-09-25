# Bounded thread-set discovery

Private run `thread-discovery-01` passed both discovery controls. The stable two-thread process converged in two
passes. In the second arm, a worker deliberately created another thread after the first enumeration and before
attachment began. The first pass contained two TIDs, the second found and attached the third, and the third
confirmed the complete stopped set. The late TID was absent from the first inventory and present in the final one.

The discovery routine receives only the process leader PID. Fixture thread IDs are recorded for independent
verification but do not drive attachment. Each pass enumerates `/proc/<pid>/task`, checks thread-group and tracer
identity, seizes new entries with clone reporting and exit cleanup, interrupts them, and accounts for wait events.
A later enumeration must contain exactly the live tracked set, with every TID already traced and stopped at its
start. Final status records independently confirm the same thread group, observer and tracing-stop state.

The implementation records pending clone and exit events and can recognize an automatically traced child before
its parent's clone record. Neither private discovery arm produced a ptrace clone event: the late worker was
created by an untraced thread before that thread was seized. These controls prove rescan discovery, not every
concurrent clone/exit branch. The earlier [worker controls](guest-thread-control.md) separately witnessed clone
reporting during continuous execution. Combining those mechanisms in stock execution remains a later question.

The stopped set was terminated and fully reaped: two threads in arm 0 and three in arm 1, followed by `ECHILD`.
No mapped device or synthetic response was involved. The checker verified event accounting, identities,
enumeration membership, convergence, binary copies and cleanup before allowing the next arm. Final verification
also checked the sealed raw index, absent stock package, stable system_server PID 1083 and two `Enforcing` samples.
The disposable guest shut down and experiment ports were free.

## Decision and remaining scope

The admitted stock coverage task is now ready. Use a fresh guest, byte-identical stock artifacts and the existing
narrow admission fixture. Keep `/dev/xdma0_bypass` absent, validate the stock snapshot, establish the same stopped
coverage boundary, then terminate and reap without supplying the device. The stock-mode helper is prepared but
was not executed in this private run.

This boundary briefly stops all discovered threads to make membership checkable. It does not justify leaving
siblings frozen during subsequent initialization, which may need their synchronization. It also does not prove
future signal handling, access ordering, or progress under a wider observer. A successful stock coverage run
would justify a bounded integration that repeats the existing post-store witness before following the next
unsatisfied dependency.

The [fixture and result manifest](../../experiments/guest-thread-discovery/results.toml) pin the source and raw
capture. Limits are 128 tracked TIDs, 16 passes, 256 setup wait events and a 10-second native deadline, with bounded
host commands and guest lifecycle as additional limits.

```sh
tools/guest/build-thread-coverage.sh
tools/guest/run-admission.sh fresh-discovery-run discovery
kotlin tools/guest/VerifyCoverage.main.kts out/guest-admission/fresh-discovery-run
```

Configure the compiler, linker and SDK through the documented environment variables. No physical instrument or
host policy change is involved.
