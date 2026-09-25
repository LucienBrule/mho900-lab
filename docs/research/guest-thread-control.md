# Private multi-thread mapped-access controls

Run `thread-control-01` passed three private controls in the pinned API25 guest. They establish worker fault
attribution, a narrow read completion reaching shared fixture state, and automatic observation of a newly created
thread. They do not run Sparrow or establish arbitrary process-wide ordering.

| Arm | Existing worker | New worker | Responses | Reaped threads |
| --- | --- | --- | --- | --- |
| 0 | Read `0x4048`, shared output becomes `0x11223344` | Read `0x4044`, stopped | 1 | 3 |
| 1 | Unexpected read `0x4040`, stopped | Never created | 0 | 2 |
| 2 | Read `0x4048`, shared output becomes `0x11223344` | Write `0x4044`, stopped | 1 | 3 |

The initial leader and existing worker were seized with clone reporting and exit cleanup enabled, interrupted,
and observed in tracing stops before the private release gate opened. `/proc` records confirmed their common
thread group and supervisor. The modeled private read was guarded by TID, exact instruction PC/opcode and mapped
address. Register readback independently verified only `x9` and PC changed, with SP, PSTATE and all other general
registers preserved. The worker's normal following instructions stored the value and released its leader.

The leader then created a worker with a separate aligned stack in the same address space and thread group.
The supervisor obtained its TID from the kernel clone event and verified its initial tracing stop before resuming
it. Both successful arms delivered the clone event before the child stop. The implementation permits either order,
but the opposite order was not witnessed in this run. At the new worker's mapped fault, observation stopped without
another response. Unknown offsets and write direction were never completed.

Each terminal inventory matched the expected traced TIDs. Group termination produced one SIGKILL reap per traced
thread, followed by `ECHILD`; no fixture process remained. Native event count and monotonic deadline were bounded.
The host command and disposable guest lifecycle provide an additional wall-time bound. No stock application was
installed or launched. `system_server` remained PID 1053 across five samples, and both enforcement samples were
`Enforcing`.

## Reference and verification

The reference is upstream Linux revision `b2776bf7149bddd1f4161f14f79520f17fc1d71d`, acquired through Gitiles from
[kernel.googlesource.com](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/b2776bf7149bddd1f4161f14f79520f17fc1d71d/).
Pinned files cover generic ptrace requests/options/events, wait flags, thread clone flags, the generic clone syscall
definition and ARM64 syscall selection. They are reference ABI evidence, not a claim to possess the exact guest
kernel source. All three trailing clone arguments are zero in the fixture; no TLS or TID-pointer option is used.
The failed raw GitHub acquisition and byte-identical tag/revision wait-header comparison are recorded separately.

The typed Kotlin checker binds captured instructions to the executed ELF and verifies complete event ordering,
initial attachment, clone/new-thread identity, fault registers, response differences, shared output, terminal
inventories and cleanup. Per-arm verification ran before the next arm. The final checker also validated the raw
hash index, executed binary copies, absent stock package, stable framework PID and enforcement samples.
The [result manifest](../../experiments/guest-thread-control/results.toml) pins the source and captures.

## Remaining coverage question

The private fixture supplied its initial leader and worker identities. Sparrow requires bounded discovery of its
live thread set: enumeration and attachment can race with thread creation or exit. The next batch should establish
coverage while the device path is still unavailable, record repeated inventories and pending clone events, and
require convergence before permitting any modeled access. Briefly stopping all discovered threads during this
setup is distinct from leaving siblings frozen while stock initialization needs their synchronization.

Once that coverage gate is proved, retain the existing two responses and precise post-store stop while checking
that the wider observer preserves the stock witness. Only then advance to the next externally unsatisfied
initialization dependency. No new register value follows from these private controls.

## Reproduction

```sh
tools/guest/build-thread-control.sh
tools/guest/run-admission.sh fresh-thread-run threads
kotlin tools/guest/VerifyThreads.main.kts out/guest-admission/fresh-thread-run
```

Configure `NATIVE_CC`, `NATIVE_LD` and `ANDROID_SDK_ROOT` locally. Native C/assembly remains confined to the guest
ABI boundary; semantic verification is Kotlin. The common inventory helper now accepts an explicit stopping TID,
so a worker stop is not mislabeled as a leader stop; the earlier single-thread wrapper retains its behavior.
