# Bounded SPU transcript input

This versioned binary input carries one fixed static candidate for the eight mapped W32 operations in stock `.26` `DevAcquireSPU_Init`. It also carries the complete bounded software-memory schema needed to reject a different live series selection or shadow state. It models no FPGA side effect, readback, readiness, timing, DMA, interrupt, UART, or later `Dev_Init` behavior.

The candidate is deliberately non-adaptive: domain 8, selector 900, series record 2, sample count 16, `Mg=1`, `Mr=4`, and checkpoint shadows control 1, gain 0, TX 0, ADC-control 0. Any different live value is rejection evidence. Control 1 is the post-first-bitset state at the already pending first SPU store; it is not a unique pre-SPU `S` value.

All integers are unsigned little-endian. All addresses are stock-library-relative logical identifiers. Stock consumers add the validated load base; private consumers map the same identifiers to independently allocated objects. The input never authorizes arbitrary addresses.

## Version 1 layout

| Offset | Bytes | Field |
| --- | ---: | --- |
| 0 | 8 | ASCII magic `MHOSPUT1` |
| 8 | 4 | Version, exactly 1 |
| 12 | 4 | Header bytes, exactly 64 |
| 16 | 4 | Total bytes, exactly 1064 |
| 20 | 4 | Profile: 1 stock, 2 private |
| 24 | 4 | Write count, exactly 8 |
| 28 | 4 | Binding count, exactly 15 |
| 32 | 4 | Series-selection record count, exactly 9 |
| 36 | 4 | Selected sample record count, exactly 3 |
| 40 | 4 | Shadow count, exactly 4 |
| 44 | 4 | Write width, exactly 4 |
| 48 | 4 | Required capture repetitions, exactly 2 |
| 52 | 12 | Three reserved u32, all zero |
| 64 | 360 | Fifteen 24-byte binding records |
| 424 | 48 | Three 16-byte global records |
| 472 | 16 | Derived selection tuple |
| 488 | 288 | Nine normalized 32-byte series records |
| 776 | 96 | Three 32-byte sample records |
| 872 | 128 | Four 32-byte shadow records |
| 1000 | 64 | Eight offset/value pairs |

The consumer reads at most 1065 bytes and rejects truncation, trailing bytes, inconsistent counts, unknown profile, nonzero reserved fields, or any mismatch against its compiled allowlist before target creation or discovery. Stock and private fixtures differ only in the profile word.

## Bindings

Each binding is `kind:u32`, `reserved:u32=0`, `slot:u64`, `target:u64`. Kind 1 is function and kind 2 is data; relocation type is verified during derivation and is not encoded as semantic kind.

| Index | Symbol | Kind | Slot | Target | ELF relocation |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0 | `DevAcquireSPU_Init` | 1 | `b8cb50` | `272f40` | `401` |
| 1 | `DevAcquireSPU_Reset` | 1 | `b7ca38` | `272c8c` | `402` |
| 2 | `DevAcquireSPU_TxReset` | 1 | `b78630` | `272da8` | `402` |
| 3 | `DevAcquireSpuH12S4_SetAdcGain` | 1 | `b85af0` | `273018` | `402` |
| 4 | `DevAcquireSpu_SetAdcBitRange` | 1 | `b785a8` | `2732d0` | `402` |
| 5 | `chn2log` | 1 | `b820f8` | `274f04` | `402` |
| 6 | `DevSystem_ChnMode` | 1 | `b8ab80` | `27254c` | `402` |
| 7 | `DevSystem_GetSampleMode` | 1 | `b7a568` | `272490` | `402` |
| 8 | `DevSystem_GetSeriesParam` | 1 | `b7bb08` | `272244` | `402` |
| 9 | `DevAcquireSpu_WriteRegister` | 1 | `b86690` | `272c2c` | `402` |
| 10 | `Dev_WriteRegister` | 1 | `b79db8` | `2703c8` | `402` |
| 11 | control shadow | 2 | `b8d288` | `3cb44fc` | `401` |
| 12 | gain shadow | 2 | `b8bb48` | `3cb44a0` | `401` |
| 13 | TX shadow | 2 | `b8d060` | `3cb44f0` | `401` |
| 14 | ADC-control shadow | 2 | `b8be90` | `3cb44b0` | `401` |

## Selection and sample records

Each global record is `address:u64,value:u32,reserved:u32=0`, ordered domain `b8f4e4=8`, selector `b8f4e8=900`, and power-mode `be1134=0`. Power-mode zero is captured even though it is irrelevant when selector is 900; it only changes selector 4000 to effective selector 2000. The derived tuple is `effective_selector:u32=900`, `selected_record:u32=2`, `Mg:u32=1`, `Mr:u32=4`.

The nine 32-byte selection records are normalized link-time values. Their pointer at `+8` is covered by `R_AARCH64_RELATIVE`. Records 0 through 5 also have an `R_AARCH64_ABS64` configuration pointer at `+24`; the fixture stores the relative symbol target there. Records 6 through 8 require zero at `+24`. A live stock comparison rebases every nonzero pointer field. It must not byte-compare loader-mutated pointer bytes to relative fixture bytes.

The three sample records are ordered requested indices 0, 1, 15. Each contains `index:u32`, `reserved:u32=0`, `record_address:u64`, then the complete 16-byte sample record. The selected table pointer must be `b8f808`, count must be 16, record 1 supplies `Mg`, and record 15 supplies `Mr`. Record 0 is retained because `DevSystem_GetSampleMode` falls back to it for an out-of-range selector. A zero count is rejected because the stock unsigned `count-1` check underflows.

## Shadows and writes

Each shadow record is `slot:u64`, `object:u64`, `width:u32=4`, `checkpoint:u32`, `terminal:u32`, `reserved:u32=0`. The order is control `(1 -> 0)`, gain `(0 -> 55555555)`, TX `(0 -> 20000000)`, ADC-control `(0 -> 00f00001)`.

The derivation computes rather than copies those results: clear control bit 0; clear/set/clear bits 0 and 4; compute gain byte `(1 mod 4)*85` and replicate it for `Mg=1`; OR TX bit 29; combine the four low bits of input bytes `01 01 01 01` for `Mr=4`, set ADC-control bit 0, and replace bits 20 through 23.

Each write is `offset:u32,value:u32`:

| Index | Offset | Value |
| ---: | ---: | ---: |
| 0 | `1000` | `00000001` |
| 1 | `1000` | `00000000` |
| 2 | `1000` | `00000000` |
| 3 | `1000` | `00000010` |
| 4 | `1000` | `00000000` |
| 5 | `105c` | `55555555` |
| 6 | `1010` | `20000000` |
| 7 | `1014` | `00f00001` |

## Runtime capture boundary

At the pending first SPU write, while the main thread is stopped, capture globals, all nine normalized selection records, the selected sample records 0/1/15, bindings, and four shadows. Repeat the globals, selection records, sample records, and shadows around the capture block and require exact equality. Check every stock pointer against the fixed rebased allowlist. A private fixture uses independent allocated objects and the same logical values.

Only then may the current exact W32 and the remaining seven ordered main-thread W32 accesses be accepted at the already validated `Dev_WriteRegister` PC/opcode. Advance only PC and verify all other registers remain identical. Stop without responding at the next access. Bounds cover exactly eight writes, two capture passes, fifteen bindings, nine selection records, three sample records, four shadows, known TID, event count, and wall time.

The threshold object written after the eighth access is deliberately outside version 1: it produces no mapped write and is neither a binding nor a captured shadow here. Adjacent WPU, SCU, UART, GD32, JESD, and LA paths are also excluded.

The capture is non-atomic with respect to untraced external writers. Two equal snapshots narrow but cannot eliminate that limitation. Matching the candidate proves a stock instruction prefix under the declared software inputs. It does not prove peripheral acceptance or physical behavior.
