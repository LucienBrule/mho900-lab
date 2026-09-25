# Synthetic single-read comparison

The third experiment is complete. Both fresh stock runs consumed exactly one
synthetic 32-bit response at offset `0x4048`, stored the supplied word through
ordinary stock instructions, and reached the next read at `0x4044`. The second
read was left incomplete. No complete FPGA identity was supplied.

This is a disposable Android guest running stock oscilloscope software. The
experiment tests mapped-register observation and one deterministic load completion.
The APK and native-library bytes remain unchanged. No physical instrument was
accessed or modified.

## Paired observations

| Run | Synthetic response | Stock caller output, low 32 bits | Next access | Completed reads |
| --- | --- | --- | --- | --- |
| `single-read-zero` | `0x00000000` | `0x00000000` | read32 at `0x4044` | 1 |
| `single-read-pattern` | `0x11223344` | `0x11223344` | read32 at `0x4044` | 1 |

Both first and second accesses execute the same stock accessor instruction:
`libscope-auklet.so+0x270604`, opcode `b9400109`, `ldr w9, [x8]`.
The first effective address is mapping base plus `0x4048`; the second is base plus
`0x4044`. The original mapping request remains 16 MiB, RW, shared, offset zero.
The observer substitutes inaccessible anonymous backing so that each attempted
mapped access produces a recorded fault.

For the first read only, the supervisor sets W9 to the configured synthetic word
and advances PC by four bytes. The native helper reads the register state back
from the kernel and checks all general registers, SP and processor flags against
the intended state. It changes no stock instruction bytes. Stock instructions
then store the supplied word into the caller's original output location. At the
second fault, the observer reads that location and delivers the ordinary signal
without completing the access.

The captured output is an eight-byte observation of a four-byte stock output.
Only its low 32 bits belong to the result; the upper bits are adjacent stack data.
A separate private control starts X9 with all bits set, supplies the 32-bit test
word, and executes a full 64-bit store. Both runs verify zero extension independently
of the stock caller's four-byte store. Four other controls cover 32/64-bit reads
and writes without supplying a response.

The runtime helper sources and native ELF are byte-identical between arms. The
sole configured response change is zero versus `0x11223344`; fresh guest state,
process IDs and mapping addresses differ. Independent Kotlin verification checks
raw hashes, original APK/native bytes, admission controls, process label, signers,
shared UID, both fault records, opcode/effective-address consistency, the supplied
word, caller output and the one-read completion limit.

`system_server` remained PID 1053 across three samples in the zero arm, and PID
1063 in the patterned arm. Both guests are shut down and the isolated experiment
ports have no listeners. SELinux remained enforcing. Guest instrumentation used
for APK admission still changes guest policy and remains an explicit limitation;
Sparrow itself has no injected Frida mapping in these runs.

## Conclusion across the three experiments

1. [Native syscall control](xdma-syscall.md) explains the low-address fault: stock
   mmap returned `ENODEV`, and the stock null-only check admitted `MAP_FAILED`.
2. [External mapped-register capture](xdma-native.md) establishes the real first
   access: read32 at `0x4048` in the stock `DevSystemSCU_GetFPGADNA` call chain.
3. This paired experiment validates one narrowly scoped synthetic load completion
   and observes the next read at `0x4044` for both tested values.

The smallest demonstrated implementation is therefore a main-thread syscall
supervisor, protected mapping, exact instruction decoder, one explicit response,
and a stop at the next unsupported access. It is a tested device-model primitive,
not a complete XDMA model or a physical register specification. The public XDMA
reference supplies transport semantics; the stock program supplies the observed
request sequence. Synthetic response values remain identified as test inputs.

Both tested words produce the same immediate next read. This does not establish
value independence for every possible word, later initialization behavior, a
physical FPGA identity, acquisition behavior, or useful UI. The observer does not
cover all threads or reproduce physical mapping attributes, memory ordering, DMA,
IRQs, timing or side effects.

The next proposed question is how stock code assembles and consumes the two words,
and where the first value-dependent decision occurs. That should be established
before selecting a coherent identity fixture. No fourth experiment is admitted
or executed in this exploration, and no further register response was supplied.

## Evidence and task state

`TASK.hardware.single-read` and `TASK.hardware.single-read-decision` conclude this
three-experiment exploration. Read current taskctl state rather than inferring
readiness from these notes:

```sh
./taskctl doctor
./taskctl context
./taskctl frontier
```

The zero arm was preserved at an operator-requested break in commit `a0561a6`.
`experiments/xdma-single-read/checkpoint.toml` retains that historical checkpoint.
On resumption, taskctl contracts, source snapshots and binary hashes were checked
before the patterned arm started. `experiments/xdma-single-read/results.toml`
pins both runs and final verification evidence; raw logs and native binaries remain
in ignored output directories.

To verify the existing captured runs without starting a guest:

```sh
kotlin tools/guest/VerifyNative.main.kts out/guest-admission/single-read-zero single-read
kotlin tools/guest/VerifyNative.main.kts out/guest-admission/single-read-pattern single-read
```
