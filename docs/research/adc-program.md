# Conditional stock ADC command program

Read-only analysis of the pinned stock `libscope-auklet.so` identifies a finite candidate write transcript for
the loop in `DevAcquireADC_Init`. This is a software prediction, not evidence of physical ADC behavior or a
completed initialization run.

`addrValue` at ELF `0x994a5c` and `regValue` at `0x994c18` are each 444-byte `.rodata` objects containing 111
32-bit entries. Relocations bind GOT slots `0xb8cfa0` and `0xb8d0c8` to those symbols. The loop compares its index
against `0x6e` and consumes entries 0 through 109. For each entry it calls `Dev_AdcWrite(reg, addr, 0)`, then
`Dev_AdcWrite(reg, addr, 1)`. Each call emits two stores at offset `0x3000`, for 440 predicted stores total.

For the low 16 bits of each source word, the decoded construction is:

```text
assert = 0x04000000 | (mode == 0 ? 0x01000000 : 0x02000000) | (addr << 16) | reg
clear  = assert & 0x03ffffff
```

The phase labels describe the software bit transition only. They do not establish a physical strobe or command
completion. The first entry is address `0x63`, value zero, predicting `05630000, 01630000, 06630000, 02630000`.
The next entry predicts `05600c08, 01600c08, 06600c08, 02600c08`. The last consumed entry is address `0x6e`, value
zero. An additional array entry is not consumed by this loop.

## Conditions and limits

The array symbols have global/default visibility and are accessed through dynamic GOT bindings; immutable ELF
bytes alone cannot establish runtime self-binding. The calls also use PLT resolution. A model using this
prediction must verify live table pointers and captured table contents against the pinned ELF, and bind actual
stores to the already witnessed stock instruction. A sequence match supports the observed write trace; it is
not, by itself, proof of a particular dynamic call stack.

After the loop, direct calls and operations using writable BSS produce further candidate commands. The static
review calculated a conditional 452-store full-function transcript, but those later operations add writable-state
assumptions. The proposed first model therefore stops after the 440-store immutable-table loop and leaves the
following access unsupported. No arbitrary offset-`0x3000` write acceptance is justified by this analysis.

The [analysis manifest](../../experiments/adc-program/analysis.toml) pins disassembly, symbol/relocation evidence
and derived candidate transcripts. The original static index included its own hash and therefore failed that
one line. Every substantive file matched. The original index and failure are preserved; a separate corrected
index excludes the self-reference and validates without changing raw files.

This analysis has not run the 440-store model. Its admission, independent transcript derivation, private controls,
live bindings and stock execution remain separate tasks. Orange-Rigol XDMA source provides mapping transport,
not these command semantics, physical reset values or ADC-ready evidence.
