# Independent stock mmap failure control

Experiment 1 of the three-experiment exploration used the guest's native strace
4.11, with no injection into Sparrow. The public XDMA comparison and prior
negative adapter results remain in [the boundary report](xdma-boundary.md).

The hypothesis was that a real failed mmap could explain the earlier `0x4047`
fault. A disposable `/dev/xdma0_bypass` symlink to `/dev/null` admits the stock
open but supplies no BAR or register values. Before creating the alias, strace
attached to the already waiting stock process. A separate `cat /dev/null` control
verified tracing and successful ordinary file access.

## Observed result

In fresh run `syscall-01`, the native trace records this sequence on the main
thread (PID 2521):

1. Repeated bypass `openat` calls return `ENOENT` before the alias exists.
2. `openat(AT_FDCWD, "/dev/xdma0_bypass", O_RDWR|O_SYNC)` returns fd 44.
3. `mmap(NULL, 16777216, PROT_READ|PROT_WRITE, MAP_SHARED, 44, 0)` returns `ENODEV`.
4. `SIGSEGV`, `SEGV_MAPERR`, address `0x4047`, occurs at stock ELF offset `0x270604`.

The last PC is the 32-bit load in `Dev_ReadRegister`. Because Android maps the
stored ELF directly from the APK, the verifier derives its ZIP data offset from
the central directory before resolving the captured process map and PC.

Independent stock disassembly shows `Dev_PCIeInit` stores mmap's return at
`0x27028c`, then compares it against zero at `0x270298`. It does not compare against
`MAP_FAILED` (`-1`). Consequently, a failed mapping can reach the register accessor;
`-1 + 0x4048` gives the observed `0x4047`. This is a corroborated error-path
explanation, not a register specification or proof of why the earlier hook missed
mmap. No register name or value is inferred.

The installed APK retains its original SHA-256; the verifier checks its packaged
native ELF hash too. `system_server` remained PID 1057 across three samples.
Sparrow had no Frida mapping, SELinux stayed enforcing, and the alias was removed
before full guest teardown. The existing PMS admission/label fixture still uses
Frida and changes guest policy; this is not an unmodified Android environment.
No instrument or host security policy was touched.

## Decision and next experiment

The kernel observer works in this guest and resolves the low-address ambiguity.
Select a native syscall supervisor for the second experiment: alter only the
exact stock mmap request into an inaccessible anonymous mapping, then capture
first-fault siginfo, registers and instruction from outside the process. Validate
it first on known private read/write controls. No instruction completion or
hardware response is authorized by that experiment's hypothesis.

This replaces the failed callback transport within the already selected mapped
access boundary. It does not change the intended hardware contract. Its native
C/assembly boundary is a necessary exception to Kotlin-first tooling: the helper
must run under this Android kernel and use ptrace; evidence verification remains
Kotlin. The implementation receives separate task admission before execution.

## Reproduction

With the pinned baseline and admission inputs and `ANDROID_SDK_ROOT` set locally:

```sh
tools/guest/run-admission.sh syscall-new syscall
kotlin tools/guest/VerifySyscall.main.kts out/guest-admission/syscall-new
```

`experiments/xdma-syscall/results.toml` pins the guest strace binary, source and raw
artifacts. Raw evidence remains ignored. No external strace binary was installed.
The verifier accepts explicit observer-unavailable/attach-failure profiles as
negative outcomes; this run instead satisfies the concrete syscall/fault sequence.
