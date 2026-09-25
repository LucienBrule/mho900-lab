# Bounded ADC transcript input

This protocol carries a static prediction for the complete stock ADC initialization routine. It authorizes
only matching W32 operands at the already witnessed mapped store instruction. It does not implement ADC
behavior, register readback, readiness, timing or acquisition. The stock instruction stream remains unchanged.

The input is a binary tool boundary; its review manifest is TOML. All integers are unsigned little-endian.
No field contains a host path, string pointer or absolute guest address. Stock locations are relative to the
loaded library. Consumers must compare the complete location schedule with their compiled allowlist before
using it; the input is not an arbitrary memory-reading program.

## Layout, version 1

| Byte offset | Field | Required value |
| --- | --- | --- |
| 0 | Eight magic bytes | ASCII `MHOADCT1` |
| 8 | Version, u32 | 1 |
| 12 | Header bytes, u32 | 64 |
| 16 | Total bytes, u32 | Exact file length and calculated length |
| 20 | Profile, u32 | 1 stock or 2 private |
| 24 | Write count, u32 | 1 through 512; stock profile requires 452 |
| 28 | Words per table, u32 | 111 |
| 32 | Binding count, u32 | 11 |
| 36 | Shadow record count, u32 | 2 |
| 40 | Write offset, u32 | `0x3000` |
| 44 | Write width, u32 | 4 |
| 48 | Four reserved u32 words | All zero |
| 64 | Eleven binding records, 24 bytes each | Fixed ordered schedule |
| 328 | Address table, 111 u32 words | Complete `addrValue`, including unused entry 110 |
| 772 | Value table, 111 u32 words | Complete `regValue`, including unused entry 110 |
| 1216 | Four source u32 words | Initial index 9, initial index 8, mask index 9, mask index 8 |
| 1232 | Two shadow records, 32 bytes each | Index 9 pair, then index 8 |
| 1296 | Ordered writes, 8 bytes each | Offset u32 followed by value u32 |

The exact length is `1296 + 8 * write_count`, or **4,912 bytes** for the full prediction. The maximum is
5,392 bytes. A consumer reads at most the maximum plus one byte and rejects excess, truncation, trailing
bytes, inconsistent lengths/counts, unknown versions/profiles, nonzero reserved fields, and any location,
width or fixed metadata outside the allowlist **before creating or attaching to a target**. It must select
the profile explicitly, rather than trust a profile supplied by the file.

Each binding record contains `kind:u32`, `reserved:u32=0`, `slot_relative:u64` and `target_relative:u64`.
Kinds are 1 for a function and 2 for data; they do not encode the ELF relocation type. The fixed schedule is:

| Index | Kind | Symbol | Slot | Target |
| --- | --- | --- | --- | --- |
| 0 | 1 | `DevAcquireADC_Init` | `0xb8ddd0` | `0x27ed3c` |
| 1 | 1 | `DevAcquireADC_InitGlobalVariable` | `0xb78d30` | `0x27e9b0` |
| 2 | 1 | `Dev_AdcWrite` | `0xb82d20` | `0x2717c8` |
| 3 | 1 | `DevAcquireADC_SetADCReg` | `0xb88fd0` | `0x27e8a8` |
| 4 | 1 | `Dev_WriteRegister` | `0xb79db8` | `0x2703c8` |
| 5 | 2 | `addrValue` | `0xb8cfa0` | `0x994a5c` |
| 6 | 2 | `regValue` | `0xb8d0c8` | `0x994c18` |
| 7 | 2 | `regInitValue` | `0xb8e7a8` | `0x99471c` |
| 8 | 2 | `maskValue` | `0xb8eea8` | `0x9948bc` |
| 9 | 2 | Index-9 shadow | `0xb8cb08` | `0x3cb45bc` |
| 10 | 2 | Index-8 shadow | `0xb8d1b8` | `0x3cb45c8` |

A stock run checks all eleven live pointers against the expected library-relative
targets, both complete tables, and all four source words before completing its first modeled write.

Each shadow record contains `slot_relative:u64`, `object_relative:u64`, `width:u32`, `initial:u32`,
`final:u32`, and `reserved:u32=0`. Width is four for the index-9 pair and two for index 8. The first initial
value is `0x67216721`, representing two little-endian halfwords `0x6721`; its final value is `0x47215721`,
representing `0x5721` followed by `0x4721`. Index 8 changes from `0x000b` to zero. These are software shadows,
not device-returned values. Their initial values are required live conditions; final values are predictions
to compare at the terminal boundary. A first-write snapshot cannot exclude later concurrent shadow changes.

The private profile carries the same logical location schedule and data. Private fixture code maps that
schedule onto its own allocated objects; it never dereferences the stock-relative addresses. This permits
controlled good and mismatched binding/state tests. A private profile must never be accepted for stock
execution. The full private fixture uses the same 452 expected words, and a one-word fixture exercises
count exhaustion. Fixture inputs are immutable during each run.

## Runtime contract

Retain the two previously controlled synthetic reads and normal stock execution between accesses. For each
transcript entry, require the expected main thread, mapped address, W32 opcode, instruction PC and operand.
Record the fault registers, expected entry and accepted write, advance only the PC, and verify all other
registers are unchanged. Keep the mapping inaccessible. Stop on a mismatch, unexpected signal, other thread
access, exhausted count, or a thread/event/time bound. Do not append entries during execution.

After all 452 accepted writes, the next access remains unanswered. Static call order predicts an SPU write
at `0x1000`; a different access is valid evidence against that prediction. Quiesce the complete observed
thread group, capture ADC shadows and available SPU software inputs, then perform exact group cleanup.

The file hashes bind the complete input, including metadata. An independent evidence verifier must compare
the observed prefix to the input and the separately recovered sequence, rather than treating a consumer's
success message as proof. Derivation and private controls are committed and pushed before stock execution.
