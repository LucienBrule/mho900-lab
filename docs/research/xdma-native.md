# External native first-access capture

Experiment 2 tests a native ptrace supervisor at the existing mapped-access
boundary. Experiment 1 established the stock failed-mmap error path independently;
see [the syscall control](xdma-syscall.md). The new supervisor does not inject into
Sparrow and leaves all stock executable instructions unchanged.

## Observed result

Fresh run `native-01` successfully captured the complete first mapped access:

| Field | Kernel-observed value |
| --- | --- |
| Stock request | 16 MiB, address/offset zero, RW, shared, bypass fd 44 |
| Transport substitution | Private anonymous, `PROT_NONE`, fd -1 |
| Signal | SIGSEGV, SEGV_ACCERR |
| Offset | `0x4048` |
| Instruction | `libscope-auklet.so+0x270604`, opcode `b9400109`, `ldr w9, [x8]` |
| Operation | 32-bit read; no read value supplied |

All four private controls (32/64-bit reads/writes) passed. The verifier decodes
captured opcodes and checks effective addresses against the kernel register dump.
For stock, it compares the instruction directly with the hash-verified ELF.
The supervisor also captures the actual mmap GOT value and syscall PC/LR. The
original request's LR matches the stock return site at `0x270284`.

The independent post-detach debuggerd stack corroborates offsets `0x270604`,
`0x2851d4`, `0x2853e0` and `0x2f191c`. Static symbols identify the chain as
`Dev_ReadRegister`, `DevSystemScu_ReadRegister`, `DevSystemSCU_GetFPGADNA`, and
`Drv_System_GetFPGADNA`. The routine first reads `0x4048`, then requests `0x4044`.
Only the first read has been observed live in this experiment. These are stock
consumer semantics; neither the public XDMA driver nor this capture establishes
physical register contents or the validity of any synthetic FPGA identity.

The first access was deliberately left incomplete. `system_server` remained PID
1068 across three samples; the app terminated through its ordinary fault path.
The crash buffer also contains an earlier root-owned Binder-thread crash from PID
2487 before the native probe; its tombstone is empty and its process identity was
not established. It is not evidence of a system_server restart or a second stock
MMIO fault. Both raw records are retained.

## Scope and decision

This is a successful first-access observation, not a register model. Only the
main thread is supervised, justified by the established startup path. It does not
claim complete concurrent MMIO coverage, device ordering, DMA, IRQs or physical
BAR semantics. The original requested protection/flags are preserved as evidence
but the backing differs deliberately. A ptrace timeout kills only the traced
process through EXITKILL; the guest remains disposable. SELinux stays enforcing,
with the earlier Frida admission policy changes still an explicit limitation.

Select a third experiment with one modeled 32-bit read completion, guarded by the
exact stock PC, opcode and offset. Compare two explicitly synthetic test words,
then stop at the next access without completing the FPGA identity. This tests
whether the captured consumer sequence and narrow load emulation are deterministic;
it does not propose a real device value or attempt to pass a later identity check.

## Inputs and reproduction

`experiments/xdma-native/inputs.toml` pins LLVM clang/LLD 23.1.1 build evidence,
the static guest ELF and Linux v3.18 ABI reference files. The latter document
ARM64 syscall-stop x7 entry/exit markers; they are not claimed to equal the guest's
3.18.91+ kernel source. Private controls validate this protocol in the actual guest.
C/assembly is confined to the native ABI boundary; verification is typed Kotlin.

```sh
# Configure NATIVE_CC, NATIVE_LD and ANDROID_SDK_ROOT locally.
tools/guest/build-native-probe.sh
tools/guest/run-admission.sh native-new native
kotlin tools/guest/VerifyNative.main.kts out/guest-admission/native-new
```

Results and hashes are in `experiments/xdma-native/results.toml`. Proprietary bytes,
native binaries and raw logs remain ignored. No physical instrument was accessed.
