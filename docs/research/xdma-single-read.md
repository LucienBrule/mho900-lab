# Synthetic single-read experiment: paused checkpoint

The operator requested a break after the zero-response arm completed. No further
run was started. This is a partial experiment, not the paired comparison's final
conclusion. Taskctl is the source of task lifecycle and contract state.

## Completed work

Experiments 1 and 2 are closed and pushed:

- [Native syscall control](xdma-syscall.md): real mmap failure explains the stock
  application's low-address fault.
- [External mapped-register capture](xdma-native.md): the first observed access
  is a 32-bit read at offset `0x4048` in `DevSystemSCU_GetFPGADNA`.

Experiment 3 was separately planned, admitted, committed and pushed before its
implementation. It compares exactly one synthetic read response, zero versus
`0x11223344`, and stops at the next mapped-register access. The stock APK and
native-library bytes are preserved. No complete FPGA identity is supplied.

Fresh run `single-read-zero` completed and passed Kotlin verification:

1. Four private 32/64-bit mapped-access controls passed.
2. A separate private control verified a synthetic 32-bit load, zero extension,
   and storage of the full 64-bit destination register into ordinary memory.
3. Stock Sparrow reached read32 at offset `0x4048`, PC `0x270604`, opcode `b9400109`.
4. The supervisor supplied zero to W9 and advanced PC by four bytes exactly once.
   A kernel register readback checked the requested register state, including
   preservation of all other general registers, SP and processor flags.
5. Stock instructions stored that zero into the original caller's output location.
6. The next observed read was at offset `0x4044`, at the same stock accessor PC.
   This second read was left incomplete and its ordinary signal was delivered.

The low 32 bits of the captured caller output are zero. The upper 32 bits belong
to adjacent stack storage and are not part of that output value. The private
control uses an actual 64-bit store to verify W-register zero extension separately.
`system_server` remained PID 1053 across all three samples. APK/native hashes,
shared UID, signers, process label and admission controls passed verification.
The guest is shut down; the isolated experiment ports have no listeners.

These are observations of stock application behavior under an explicitly
synthetic device response. They do not establish a physical register value,
complete identity, later initialization result, or useful UI. The public XDMA
reference still supplies transport semantics rather than Rigol register contents.

## Pending work and resume procedure

Ledger revision at the break:
`sha256:fe12af235822c60d88dbfcc39506f47d4d4b7982d9bb8ad253e69acf31fb0068`.

- `TASK.hardware.single-read` remains open/current: zero arm verified; the fresh
  `0x11223344` arm has **not** run.
- `TASK.hardware.single-read-decision` remains open/current and awaits that task.
- Do not close either task or claim the paired result from the zero arm alone.

On resumption, read the actual ledger and contracts first:

```sh
./taskctl doctor
./taskctl context
./taskctl frontier
./taskctl show TASK.hardware.single-read
./taskctl show TASK.hardware.single-read-decision
```

Then inspect `.agents/checkpoints/xdma-single-read.yaml`, this report, and the
pinned manifest. Compare the current helper sources/binary with the zero arm's
snapshots before proceeding. The planned second arm uses the same implementation
with `NATIVE_TEST_WORD=11223344`; it requires a fresh run identifier. No additional
register response or access completion belongs to this experiment. After comparing
both arms, verify and close against the current ledger revision, commit and push
the conclusion, then stop at the three-experiment checkpoint.

The observer remains main-thread-only and uses inaccessible anonymous backing.
It does not reproduce physical mapping attributes, ordering, DMA, IRQs or other
threads' mapped accesses. Guest instrumentation used for APK admission remains
disclosed; SELinux stayed enforcing. No physical instrument was accessed or
modified, and no host security policy was changed.

Raw evidence, the built native helper and source snapshots remain in ignored
output directories. `experiments/xdma-single-read/checkpoint.toml` pins their hashes.
The tracked checkpoint is sufficient to locate the evidence and outstanding task
without reconstructing the conversation.
