# Decision: validate the complete SPU region

The [stock ADC result](stock-adc-region.md) validates all 452 predicted writes, their live
software inputs, and the next pending SPU reset store. This supports whole-subsystem
prediction followed by selective dynamic falsification. It does not establish device-side
effects. Retain the mapped-access observer and the two existing synthetic DNA reads.

The next region is the complete eight-write `DevAcquireSPU_Init`, with live selection
checks before its first accepted store. Its two independent software selectors are
`GetSampleMode(1)` for gain and `GetSampleMode(15)` for range. Static image data selects
domain 8, series 900, selection record 2, count 16, sample modes 1 and 4. Those inputs
reside in writable data; image defaults are a hypothesis to check, not runtime evidence.

Given those inputs, the predicted offset/value pairs are:

| Offset | Ordered operands |
| --- | --- |
| `0x1000` | `1, 0, 0, 0x10, 0` |
| `0x105c` | `0x55555555` |
| `0x1010` | `0x20000000` |
| `0x1014` | `0x00f00001` |

The captured control shadow of 1 is **after the first software bit-set**. It does not
distinguish an earlier control value of 0 from 1. Both produce this same subsequent
sequence. Gain, TX and ADC-control checkpoint shadows were zero. Require these values
again, the relevant function/shadow bindings, both selector globals, power-mode input,
all nine series records and selected sample records 0, 1 and 15. Repeat the selection
capture around the shadow block and reject any change. This is a bounded non-atomic
consistency check, not proof against an intervening change and restoration.

Derive and pin the candidate before execution. A different live selector is a negative
result and decision event; do not generate a new sequence during the run. Verify exact
thread, PC, instruction, width, offset, operand and order. Complete only the witnessed
stores, preserve stock code and all non-PC registers, and stop on divergence or the
first post-SPU mapped access. No additional returned read or device side effect is
admitted. Private controls must cover input mismatch and all existing observer guards.

## Following region

Static recovery places WPU software initialization next, then two SCU stores at
`0x4004`, board-power UART notification, a GD32 command on the false initialization
branch, and two LA reset stores at `0x7034`. The SCU sequence sets bit 31 in its first
operand, then clears **both bit 31 and bit 2** in its second. Its shadow is a separate
runtime input. UART open failure and command errors are ignored by `Dev_Init`; successful
transport is not established. The command path's cached descriptor and hardware-version
call remain separate dependencies. LA reset has another writable shadow and wrapper.

These paths are statically recoverable candidates for the following batch. Folding them
into this admission would conflate selector validation with unobserved transport behavior.
The next predicted mapped access is the first SCU store, but any earlier divergence is
the result. Subsequent version reads and DMA ownership remain hardware-returned and
asynchronous questions. Neither stock modules nor the public XDMA reference supplies
the FPGA behavior behind these interfaces.

## Bounded successor

1. Derive and independently check the SPU candidate, bindings and capture schema from
   the pinned ELF; publish a typed manifest and deterministic fixtures.
2. Extend and privately validate the observer's SPU region and negative controls.
3. Run one fresh stock validation through ADC and SPU; capture the next uncompleted access.
4. Evaluate the result and admit the next region or specific ambiguity.

Commit and push tasking before implementation, and each conclusion before dependent
execution. Preserve existing ADC fixtures and receipts. No kernel facade, higher native
substitution, or physical instrument access is needed to answer this question.
