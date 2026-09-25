# Static initialization contract

The next useful unit of work is a complete software initialization region, with runtime checks for its actual
bindings and inputs. The ADC initializer predicts **452 mapped stores without a device-read decision**. Its first
444 stores depend on code and read-only tables; its last eight also depend on writable software shadows. This
replaces the previous proposal to stop at the end of the 440-store table loop.

These are predictions for the pinned stock `.26` library, SHA-256
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`. The current dynamic evidence remains two
synthetic DNA reads, two completed synthetic ADC stores and the third attempted store. Neither the full ADC
routine nor the downstream initialization path has run under this model.

## Recovered software order

`CApiFactory::Api_Init` calls `Dev_PCIeInit` at `0x239110`, vendor initialization at `0x239114`, application
initialization dispatch loops, then `Drv_Init(false)` at `0x2392dc`. `Drv_Init` calls `InitDrvFEM`, then `Dev_Init`
at `0x2e5268`, followed by SCU version reads and configuration-dependent DDR work.

Within `Dev_Init`, the decoded order is:

1. Four `DevInOutAFE_Init` calls, selected by indices 0 through 3.
2. ADC initialization through GOT `0xb8ddd0`, call `0x2728ac`, static target `0x27ed3c`.
3. SPU initialization through GOT `0xb8cb50`, call `0x2728b8`, target `0x272f40`.
4. WPU software-global initialization through GOT `0xb8d8a8`, call `0x2728c4`, target `0x28f844`.
5. SCU initialization, board-power notification, a bool-selected reset sequence, and LA accumulator reset.

ADC, SPU and WPU are sibling calls from `Dev_Init`; ADC does not call SPU. A direct-BL-only search misses these
GOT-mediated edges. The static relocations identify candidates; they do not establish the loaded process's
symbol bindings. The API initialization entry passes false; low-power reinitialization can pass true and reach
a different reset sequence. Application dispatch, thread scheduling and unreviewed callees prevent treating
this list as a complete global device-access order.

## Complete ADC initialization grammar

| Region | Predicted mapped operations | Conditions |
| --- | --- | --- |
| Software global initialization | None | Copies and transforms `regInitValue` into writable shadows. |
| Table loop | 110 entries × 2 modes × 2 W32 = 440 | Live tables and function bindings match the stock ELF. |
| Constant tail | 4 W32 | Calls `(value,address,mode)=(13,0,0)` and `(5,0,1)`. |
| Shadow-derived tail | 8 W32 | Shadow values remain consistent with initialization and masks. |

Every mapped store in this routine goes through the witnessed `str w9,[x8]` at `0x27043c`, offset `0x3000`.
`Dev_AdcWrite` truncates its value and address arguments to 16 bits, selects mode 0 or 1, constructs
`0x04000000 | ((mode+1)<<24) | (address<<16) | value`, writes it, requests `usleep(100)`, and writes the word
with bits above bit 25 cleared. Invalid modes return `-1` without writes. The delay is a requested software
sleep, not evidence of an endpoint completion time.

The tables contain 111 words each, but the loop uses only indices 0 through 109. The independent indexer agrees
numerically with every one of the earlier 440 predicted words. The four constant tail words are
`0500000d, 0100000d, 06000005, 02000005`.

The initializer copies `regInitValue+0x24 = 0x6721` into both index-9 shadows and `+0x20 = 0x000b` into the
index-8 shadow. The tail transforms those to `0x5721`, `0x4721` and zero. `SetADCReg` XORs with
`maskValue[9]=0x2720` or `maskValue[8]=0`, producing:

```text
05097001 01097001 06096001 02096001
05080000 01080000 06080000 02080000
```

These shadow loads are **software-state reads**, not MMIO reads. They need live validation because the objects
are writable and globally visible. A matching transcript supports the predicted operations; it does not by
itself prove a particular dynamic caller or absence of concurrent shadow writes.

The whole ADC initializer, `SetADCReg`, and valid-mode `Dev_AdcWrite` discard lower-level failure statuses.
Returning zero therefore does not demonstrate successful I/O. `Dev_WriteRegister` itself returns zero after a
mapped store, or `-1` when its mapped-base helper returns null; it does not read endpoint status.

## Actual hardware-returned decisions

`Dev_AdcRead` supplies a useful contrast. It emits a two-write command at `0x3000`, with a 100-microsecond sleep
between writes and another before `R32(0x3004)`. Returned bit 16 determines whether it copies the low 16 bits
to its output or returns `-1`. It does not poll. `GetADCReg` then discards that error, XORs its initially-zero
local output with a mask and returns zero. A caller can consequently receive software-derived data after a
failed lower-level response.

The separate `GetOtpAll` path accepts 13 values only when returned bit 4 is clear. Its attempt index increases
even for rejected values, and no fixed attempt limit is visible. That is a liveness dependency deserving a
behavioral model if reached. Neither this OTP protocol nor ADC self-test is called by `DevAcquireADC_Init`.

Immediately after ADC initialization, SPU reset helpers manipulate a software shadow and emit writes at
`0x1000`: bit 0 set/clear, then bit 4 clear/set/clear. Later SPU initialization uses channel-mode selection and
more shadows, including a write at `0x1010`. A load through GOT `0xb8d060` is a software-shadow load; it must
not be misclassified as a hardware-returned read. WPU initialization here only sets software globals. SCU
initialization writes the `0x4004` shadow twice; later version reads and DDR selection remain separate questions.

The complete selected SPU path has eight writes and no device read. Let `S`, `G`, `T` and `A` be the initial
control, gain, TX and ADC-control software shadows. `Mg=GetSampleMode(1)` selects gain behavior;
`Mr=GetSampleMode(15)` selects ADC bit-range behavior. These can select different configuration records.

| Order | Offset | Predicted value |
| --- | --- | --- |
| 1–5 | `0x1000` | `S\|1`, `S&~1`, `S&~0x11`, `(S&~0x11)\|0x10`, `S&~0x11` |
| 6 | `0x105c` | Mg=1: `55555555`; Mg=2: `(G&ffff0000)\|5555`; otherwise `(G&ffffff00)\|55`. |
| 7 | `0x1010` | `T\|0x20000000` |
| 8 | `0x1014` | `((A\|1)&~0x00f00000)\|(L<<20)`, where L=0 for Mr=1/2 and 15 otherwise. |

SPU initialization returns only the saved result of write 7 and discards the other helper results. It finally
sets two software threshold halfwords to `0x21b4` and `0x21b7`. This region is already recoverable as a single
candidate sequence, but its four mutable shadows and two software selections make it a separate runtime-validation
question from the ADC program. There is no need to discover these eight writes individually.

Board-power notification opens a UART and sends a five-byte frame (`fa 05 00 CRC af`), or returns `-1` if the
open fails. `Dev_Init` ignores that result. Its false reset branch calls `Dev_SetGD32Reset`, which uses the
separate `Dev_WriteCommand` helper rather than a mapped register. The final LA accumulator reset sets and
clears bit 0 of software word `0x106d4d8`, writing each value at mapped offset `0x7034`. These paths are decoded
software plumbing; their physical effects and serial helper responses remain unmodeled.

## Typed graph and coverage

The [operation graph](../../experiments/static-contract/initialization-graph.toml) uses the five requested
classifications. Its node relationships describe decomposition and dependencies, not unconditional execution.
The [call inventory](../../experiments/static-contract/hardware-callers.toml) is a syntactic index of register
wrappers, DMA-named calls, and POSIX primitives; ordinary file users are intentionally not silently relabeled
as devices. The [mapped wrapper inventory](../../experiments/static-contract/mapped-wrappers.toml) records
actual access widths, including the 64-bit AFG store and the wave-data-named wrapper with no mapped store in
its decoded body.

The Kotlin indexer checks 1,988,337 decoded instruction words against the stock ELF, records 19 named register
read call sites and 95 write call sites, and resolves 23 narrow adjacent ADRP/LDR/BLR-or-BR relocation patterns.
It retains 3,466 unresolved indirect sites and 68,256 unnamed direct call targets. Indirect sites include jump
tables and virtual dispatch; they are not all hardware calls. Nearest preceding LLVM labels are explicitly
not proven function extents. Branches to labels are candidates, not automatically tail calls. The manually
reviewed initialization routines are bounded separately by their exported symbols and instructions.

This is whole-routine ADC recovery plus a broader call/ABI inventory. It is not complete semantic recovery of
every ADC setter, AFE path, later SPU selector, serial helper, DDR calibration routine, JNI registration,
or acquisition state machine. Those gaps remain visible in the graph. Static confidence applies to each
decoded region, not to every unresolved edge elsewhere in the library.

## Reproduction and evidence

Generate a fresh LLVM disassembly from the pinned ELF, or use the preserved full capture, then run:

```sh
kotlin -J-Xmx2g tools/research/IndexAuklet.main.kts \
  local/reversing/firmware-extracted/stock-0.26/sparrow/base/lib/arm64-v8a/libscope-auklet.so \
  out/group-observer/next-write-static/full-disassembly.txt \
  out/static-contract/reproduction
```

The output directory must be new. The tool generates a complete syntactic call index, selected ADC disassembly,
the table-loop prediction, typed semantic annotations and coverage counts. Semantic annotations are reviewed
interpretations bound to the stock hash and instruction witnesses; the tool is not a general symbolic executor.

The first indexing attempt exhausted its JVM heap during whole-file hashing after writing partial outputs.
Streaming hashing and an explicit heap budget produced a complete run; the partial output remains separate.
Independent review confirmed the table predictions and GOT arithmetic, and exposed label-attribution and
wrapper-inventory limits that are now explicit. No guest or physical instrument was used in this batch.

The [kernel ABI report](kernel-abi-contract.md) independently establishes substantial agreement between the
exact stock XDMA module and the pinned public implementation. It also keeps `/dev/dma_auklet` unresolved.
Neither source establishes FPGA reset values, readiness, completion, interrupts or sample data.
