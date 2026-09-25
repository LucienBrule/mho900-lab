# Complete SPU initialization candidate

This is a conditional prediction from the unchanged stock `.26` native library. The
[ADC result](stock-adc-region.md) established the pending first SPU write and four
checkpoint shadows. The remaining SPU sequence has not yet been observed dynamically.

The [derivation tool](../../tools/research/DeriveSpuTranscript.main.kts) checks the pinned
ELF, eleven complete function ranges, instruction witnesses and fifteen function/shadow
bindings. It recovers the software configuration records and emits the fixed eight-write
candidate. A separate [verifier](../../tools/research/VerifySpuTranscript.main.kts) decodes
the fixture, resolves ELF relocations independently and checks its operands against the
reviewed formulas. Neither tool modifies the ELF or executes a guest.

## Software selection

`DevSystem_GetSeriesParam` scans nine 32-byte records for a matching domain and series.
Image defaults are domain 8 and series 900, selecting record 2. Its sample table has
16 records of 16 bytes. Gain selects sample record 1, whose mode is 1. Range selects
sample record 15, whose mode is 4. Record 0 is the bounds fallback. A zero sample count
would underflow the stock bounds calculation; this candidate requires exactly 16.

Each series record has two pointer fields: the sample table at `+8` uses a RELATIVE
relocation; the non-null configuration pointer at `+24` uses ABS64. The fixture stores
resolved ELF-relative targets. Live comparison must account for the loaded library base
for both fields. It must not compare raw file pointer placeholders to loaded memory.

All these records and the selection globals are writable. Require the fixed candidate's
globals, nine series records, three sample records and four checkpoint shadows before
accepting the first SPU store. Capture the software inputs twice and reject differences.
The repeated check is non-atomic and does not exclude a change followed by restoration.
The power-mode input is captured even though series 900 does not take the conditional
4000-to-2000 override.

## Operation classes

| Region | Class | Prediction |
| --- | --- | --- |
| Reset and TX reset | RUNTIME-SELECTED | Five `0x1000` writes from the checked control shadow: `1,0,0,0x10,0`. |
| ADC gain | RUNTIME-SELECTED | Sample mode 1 and gain argument 1 produce four `0x55` bytes at `0x105c`. |
| TX configuration | RUNTIME-SELECTED | Set bit 29 of the checked zero shadow; write `0x20000000` at `0x1010`. |
| ADC range | RUNTIME-SELECTED | Sample mode 4 and vector `0x01010101` produce `0x00f00001` at `0x1014`. |
| Operand construction after input checks | STATIC-DETERMINED | Exact offsets, masks, call order and eight operands; no returned device read in this selected routine. |
| Concurrent software updates | ASYNCHRONOUS | Traced thread attribution, repeated input capture and per-access comparison constrain observation; they do not prove global immutability. |
| Device acceptance and effects | UNKNOWN | Synthetic store acceptance supplies no readiness, timing, readback, interrupt or acquisition behavior. |

Control 1 is the checkpoint **after the first bit-set**, before its mapped store. Earlier
control 0 and 1 both yield this checkpoint; neither is uniquely established. Terminal
predictions for the four shadows are control 0, gain `0x55555555`, TX `0x20000000` and
ADC-control `0x00f00001`.

After its eighth mapped write, stock code also writes threshold halfwords `0x21b4` and
`0x21b7` in software memory. These are statically established but outside this fixture's
four-shadow capture. The function returns the saved status of its seventh write and
discards the other helper results. A matching transcript therefore cannot establish that
the underlying device accepted the configuration.

See the [wire and capture contract](spu-transcript-protocol.md) and
[decision](adc-region-decision.md). The next experiment retains the two existing DNA
responses and validated ADC prefix, accepts only this complete candidate, and leaves the
first subsequent access uncompleted. An unexpected live selector closes this hypothesis;
it does not cause the observer to choose a new sequence during execution.
