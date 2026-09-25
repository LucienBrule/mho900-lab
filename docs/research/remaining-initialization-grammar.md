# Remaining initialization grammar

The [typed graph](../../experiments/remaining-init/grammar.toml) recovers the remaining
false-branch initialization region from the pinned stock `.26` library. It contains 27
nodes, 34 conditional edges and five conditional mapped-write candidates. It is a
reviewed static interpretation with byte checks, not a dynamic trace or FPGA model.
The earlier [stock result](stock-spu-region.md) has already confirmed ADC452 and SPU8;
its next pending access agrees with the first SCU candidate here.

| Region | Software prediction | Input or unresolved behavior |
| --- | --- | --- |
| SCU | `W4004:80000000,0` | Live SCU shadow and bindings |
| Board power | Open `/dev/ttyS0`; frame `fa050027af` | Open/write/close outcomes; nonpositive write exits |
| GD32 | Submit `*RST\n` on false branch | Cached descriptor; GPIO version; UART setup and I/O |
| LA | `W7034:1,0` | Transport returns; live LA shadow zero |
| Version | `R4`, `R0`, then `R401c` | Three returned mapped values; no values supplied here |
| DAC timing | `W1428:xxxx646e` | Live shadow supplies upper 16 bits |
| DDR | Selected configuration chooses next branch | Further recovery of polling/data semantics required |

The five writes are a conditional projection of the graph. They must not become a flat
transcript that silently supplies transport success or skips the version reads. Static
software operations, runtime selection, hardware-returned data and unknown regions have
separate classifications. No asynchronous FPGA semantics are inferred from these nodes.

## SCU, LA and writable state

SCU sets bit 31 in its software shadow at `0x3cb4620`, then clears both bits 31 and 2.
At the pending first store, checkpoint `0x80000000` predicts second operand zero. It
does not uniquely identify the earlier bit-31 state. The GOT binding is `0xb8cf08`.

LA has a separate shadow at `0x106d4d8`. Its exact clear mask is `0xfffffffe`; the
set phase ORs bit 0 back in. Wrapper selector `0x34` receives base `0x7000`. Zero
initial shadow therefore predicts `1,0`. The indirect LA binding at `0xb8d830` must
resolve to `0x294df8`. Its indeterminate returned stack local is ignored by `Dev_Init`.
Neither pair proves that a physical peripheral accepted or acted on the writes.

## Board-power and GD32 transport

`UART_OPen` hardcodes `/dev/ttyS0`, flags 1, regardless of its argument. Open failure
returns through board notification with `-1`, which `Dev_Init` ignores. On success,
stock CRC code computes `0x27` over payload `05 00`; the five-byte frame is
`fa 05 00 27 af`. `uartDataSeed` accepts any positive write result, including a short
write, but calls `exit(0)` after a nonpositive result. `Uart_Close` delegates to `close`.
The library does not configure this UART in the recovered notification path.

GD32 uses mutable `afg_uart_fd`, image-initialized to `-1`, through GOT `0xb8e020`.
A negative descriptor invokes reopen. Its GPIO version selects `/dev/uart_simulate`
for exactly 1 and `/dev/ttyS4` otherwise. Negative version returns `-7` before selecting
a path. Failed UART open returns `-3`; setup failure closes and returns `-1`.
`Dev_WriteCommand` stores even a negative reopen result globally and returns `-3`.
The parent reset routine reduces failure to `-1`, which `Dev_Init` ignores.

Version 0 or 1 skips setup. Version 2 and above calls `uartXSetup` with the mutable
16-byte `stUartXInfo` object, image values `115200,8,'N',1`. Setup ignores the initial
`tcgetattr` result and both speed-setter results. It calls `tcsetattr` twice, with each
nonzero result causing failure, and ignores the intervening `tcflush` result. Even with
fixed configuration inputs, inherited termios state is a runtime input. Failed
`tcgetattr` may leave parts of that state undefined. These are imported libc calls;
the stock library alone does not establish their eventual ioctl layouts or outcomes.

A command write failure returns `-4`; nonnegative short or zero writes are accepted.
After such a write, a second GPIO version query selects a requested sleep of 1000 µs
for version at least 2, otherwise 220000 µs, including negative version errors. This
is a requested delay, not evidence of peripheral readiness or elapsed hardware time.

## Correction: GPIO count is one byte

The early decision review described a four-byte GPIO read. Direct register-argument
inspection corrects that: at `0x2ad5ec`, `__read_chk` receives count **1** in `x2`
and buffer capacity **4** in `x3`. The destination is a zero-initialized four-byte
integer. The graph pins the count instruction and argument loads explicitly.

The argument order is independently supported by the
[Android 7.1.1 Bionic implementation][bionic].
A local source copy has SHA-256
`cb16372979a1873d12a94ea3d34e01bf1c217d515e21d86f7cbc6daaa1e800f1`.
The stock call opens `/dev/hdcode_gpio` with flags `0x802`; open failure returns `-3`,
negative read returns `-5`, and an ordinary one-byte result yields `0..255`. A zero-byte
read leaves zero. This is separate from the mapped hardware-version read at `0x401c`.
The original decision receipt retains its historical source hash; this correction
supersedes its read-count interpretation and is applied before any runtime fixture.

## Version consumers and the next static boundary

`DevSystemSCU_GetVersion` reads offset 4 and then 0, without adding `0x4000`, and packs
`((R4 & 0xffffff) << 8) | (R0 & 0xff)`. The second status replaces the first. The packed
result and the later `R401c` result occupy separate `Drv_Init` stack slots and are
passed to logging. Their immediate consumer does not branch on either value or status.
This does not establish every consumer of these registers elsewhere in the program.

Next, `SetDacPolling(5000000000,5500000000)` divides both arguments by 50000000,
producing 100 and 110. It replaces the low halfword of `gInt32DevAcquireDacTime` with
`0x646e` and writes its whole u32 to offset `0x1428`; the upper halfword remains live
software state. `DevConfig_GetDdrCalSkip` then reads the selected series configuration
at offset `0x68`. `MHO900Conf` has image value 1, but it is writable. Nonzero selects
`GetDdrSkipTap` and `SetMemReset` before `SelfTest`; zero skips that first block. The
DDR body remains an explicit recovery boundary, not a claimed acquisition model.

## Observation choices

The next runtime question is which recovered transport branch the disposable guest
actually takes. Two observation methods could answer it:

- Syscall entry/exit observation exposes requests directly, but introduces stops inside
  libc and unrelated logging paths. It needs a separate syscall-phase, descriptor and
  signal state machine, including possible synchronization effects.
- Rotating native hardware breakpoints at pinned call sites and their return PCs expose
  exact arguments and results while allowing libc to run continuously. The recovered
  call sites are outside exclusive load/store sequences. This keeps kernel syscall
  internals outside the immediate question, but requires tested rearming and explicit
  coverage limits for other threads.

Prefer the native checkpoints for a first bounded missing-device branch hypothesis.
Observe both device opens. Continue only on their actual negative results, with the
false initialization branch and negative cached descriptor checked. A successful open
is a terminal result before any device read or write. Otherwise require the propagated
failure statuses, both LA writes and the next uncompleted mapped read at offset 4.
This tests the whole four-write region and real guest failure handling without creating
another hardware-returned value. It does not assert that device absence is a faithful
instrument environment; it identifies whether stock initialization tolerates it.

Before stock execution, private controls must prove breakpoint rotation and register
preservation, normal completion of an atomic sequence between checkpoints, expected
negative-open propagation, successful-open stops, missing/reordered checkpoints,
changed selectors or shadows, unexpected mapped accesses, worker access, bounded
blocking and complete thread cleanup. Main-thread checkpoints alone do not observe
other threads' UART operations; mapped-access coverage remains group-wide. Record that
limit instead of implying process-wide transport tracing.

## Reproduction and scope

Run `tools/research/RecoverRemainingInit.main.kts STOCK_ELF NEW_OUTPUT_DIRECTORY` with
Kotlin, then `tools/research/VerifyRemainingInit.main.kts STOCK_ELF GRAMMAR`.
The producer checks the stock hash, instruction anchors, data literals, BSS placement,
relocations and software-derived operands. The independent verifier checks graph
integrity and its declared byte evidence; neither mechanically proves prose semantics.
Two final derivations must match, and mutation controls must reject corrupted evidence.
No guest run, stock modification, new response or physical instrument access occurs in
this batch. Raw drafts, failed checks and corrected derivations remain in `out/remaining-init`.

[bionic]: https://android.googlesource.com/platform/bionic/+/android-7.1.1_r1/libc/bionic/__read_chk.cpp
