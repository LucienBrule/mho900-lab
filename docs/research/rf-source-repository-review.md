# RF source repository and published stock-firmware review

2026-09-30. `TASK.rf.repository-contract` follows the inconclusive
[one-command trial](rf-source-point-trial.md). Four operator-supplied repositories
were pinned and inspected offline. No generator, programmer or scope was contacted.

The important new evidence is the original firmware image in
[`gamozolabs/max2871-siggen`][gamo]. Its actual receive and dispatch instructions
implement a different protocol from the HawkRAO candidate previously sent. A
bounded instruction control reproduces that distinction without hardware.
Equivalence between this public image and the delivered generator remains unknown.

## Source roles

Full commit IDs, reviewed paths and selected file hashes are recorded in
[the repository manifest](rf-source-repositories.toml). Acquired source trees,
binary bytes and the supplied review screenshot remain in ignored local evidence.

| Repository | Pinned revision | What the inspected implementation provides |
| --- | --- | --- |
| [gamozolabs/max2871-siggen][gamo] | `c6a1d18e0b37` | Published original 128 KiB firmware; board notes; a RAM-resident replacement controller; acquisition and restoration procedures. Closest relevant software evidence. |
| [gbonacini/sigenmax2870][gbon] | `3e208e616adf` | C++ host client: nine bytes, `55 55`, two big-endian frequency fields, power byte, `0D 0A`; fixed 9600 baud. Its units and power convention differ from the public touchscreen binary. |
| [brycecherry75/MAX2870][bryce] | `2773a4b03cc9` | Arduino synthesizer library and example controller. `WriteRegs()` writes registers 5 through 0 over SPI. Useful register calculations and an alternative MCU implementation, not this board's factory UART interface. |
| [nuclearrambo/MAX2870-PLL-board][nuclear] | `7665868deada` | Altium design and a three-page schematic: MAX2870, STM32F101CBT6, separate RF outputs, reference input and 12 V supply arrangement. No firmware or host serial parser in the pinned tree. |

The schematic's controller page labels PB12/PB13/PB15 as SS/SCK/MOSI and
PA9/PA10 as TX/RX. Similar pin choices are useful context, not proof that it is
the schematic for the delivered USB-powered touchscreen product.

The priority repository identifies its author's MCU as GD32F103CBT6 and RF IC as
MAX2871. The delivered board's photographed `2871E`, CH340N, XPT2046 and EEPROM
markings are consistent with this family. Its obscured MCU and firmware revision
remain unidentified. An Amazon review and a matching product appearance establish
a useful lead, not interchangeable firmware. Repository commentary is not vendor
documentation; no nominal output-power claim here is a measurement of our board.

## Published original firmware

File: `stock-firmware/stock_firmware.bin`, **131072 bytes**.

SHA-256:
`a3111637e7cab47fd5045a04c0521c3f525016f1f15d83174cc5f67be8b0b60f`.
This matches the repository's published digest. It identifies these bytes, not
their authenticity or equivalence to the delivered unit.

Addresses below use the image's flash base `0x08000000`.

| Boundary | Instruction evidence | Recovered behavior |
| --- | --- | --- |
| Main-loop UART setup | `0x080089dc` to `0x080089e0`; initializer `0x08009140` | Passes `115200` to USART1 initialization. Initializer sets 8-bit data, one stop bit, no parity and RX/TX, then enables receive interrupts. |
| USART1 vector | Vector index 53, image offset `0xd4` | Points to Thumb handler `0x080073b8`. Peripheral base is `0x40013800`. |
| Receive state | `0x080073ce` to `0x08007430` | State halfword at `0x20000110`; buffer at `0x2000132f`. `CR` sets bit 14; following `LF` sets bit 15. Other bytes accumulate; unexpected byte after CR resets the state. Completed input is held until dispatch. |
| Dispatch gate | `0x080075e4` to `0x080075ee` | Processes only a completed receive state. Main loop calls this dispatcher at `0x080089ea`. |
| Point selector | `0x080077fc` to `0x0800782a` | Buffer byte 1 equal to `0x55` selects point setting. Bytes 2–3 and 4–5 are big-endian words; byte 6 is passed as power bits. |
| Frequency composition | `0x0800782c` to `0x08007868` | Forms `whole + fraction / 100` as the MHz value at `0x20000080`. |
| Synthesizer call | `0x08007892` to `0x080078aa` | Multiplies the MHz value by 100 and converts to an integer before calling `0x08008a9c`; argument units are 10 kHz. |
| Display update | `0x080078ae` to `0x080078e0` | Updates the Point control, formats the frequency with `%.2f`, and passes its text to UI element 1. Physical rendering was not emulated. |
| Settings storage | `0x080078f0`, `0x080055a8` to `0x0800561a` | Serial point setting invokes the same save routine that constructs four frequency bytes and calls byte-write routine `0x0800219e` at addresses 1–4. |
| Storage transport | `0x0800219e` to `0x080021ec` | Sends an `0xa0`-based device byte, address and data through a software I2C sequence. This is consistent with the documented 24C02; the physical write and persistence are untested. |

The resulting **candidate for this published build**, at 115200/8N1, is:

```text
55 55  W_hi W_lo  F_hi F_lo  P  0D 0A
MHz = W + F / 100
P = raw two-bit output setting, use 0..3

100.00 MHz, setting 0: 55 55 00 64 00 00 00 0D 0A
100.25 MHz, setting 0: 55 55 00 64 00 19 00 0D 0A
```

These are offline vectors, not commands sent to the source. The recovered point
branch checks byte 1, not both leading bytes, and has no explicit frame-length or
checksum validation. It passes power directly into register-4 construction at
`0x08008dfe` to `0x08008e08`; the caller must constrain the value to its field.
No device acknowledgement is required by this recovered branch. This is not a
whole-image proof that UART transmission never occurs.

There are two important protocol limitations:

- `0x0d` is treated as framing wherever it appears. A binary payload containing
  that byte can disrupt reception; this is not a transparent arbitrary-byte
  transport. A general sweep controller must account for it.
- Unterminated input remains buffered. The earlier eleven-byte `AD ... 3D` frame
  leaves count 11 with no completion flag in this image. Appending a new point
  frame immediately does not repair it: dispatch still sees the old selector.

The `gbonacini` client therefore cannot simply be run unchanged. It uses 9600
baud, splits kHz into integer MHz plus a remainder in thousandths, and admits
power values 1–4. The touchscreen image uses 115200, hundredths and a raw bit
field. Integer-frequency examples can conceal the unit difference. Its `send()`
also verifies only the host write count; the port is opened write-only.

## Bounded offline instruction control

Capstone 5.0.7 supplied the annotated listings. Unicorn 2.1.4 executed the exact
published ISR and dispatcher instructions, including the software floating-point
arithmetic and frequency-save preparation. Each call had a 50000-instruction
limit and an asserted return. RAM was synthetic and initially zero; UART status
and data registers were supplied by the control. UI/formatting, PLL programming
and EEPROM byte-write callees were recorded and returned without physical effects.
No upstream loader or controller script was executed.

| Case | Result in the bounded control |
| --- | --- |
| Original eleven-byte trial frame | State `0x000b`; no dispatch, PLL or storage call. |
| Original frame followed by CR LF | Completed unknown command; state cleared; no PLL or storage call. |
| Candidate 100.00 MHz | PLL arguments `(10000, 0)`; MHz state 100.0; UI element 1 update requested; storage addresses 1–4 received `00 64 00 00`. |
| Candidate 100.25 MHz | PLL arguments `(10025, 0)`; MHz state 100.25; storage bytes `00 64 00 19`. |
| Candidate missing LF | State `0x4007`; no point action. |
| Unknown selector | State cleared; no point action. |
| Embedded CR in frequency payload | Framing disrupted; no point action in the specified vector. |
| Original frame immediately followed by candidate | Old prefix retained until completion; no point action. |
| Original frame, CR LF, dispatch, then candidate | Candidate reaches the 100 MHz point path. |

All nine assertions passed. The control establishes instruction behavior under
its declared conditions. It does not establish our unit's bytes, actual baud,
receiver timing, rendered pixels, PLL lock, output amplitude, RF frequency or
successful EEPROM persistence. In particular, there was no physical measurement.

## What the replacement and acquisition code actually do

The replacement's assembly and Python client use their own binary protocol:
`0x10`–`0x15` plus a little-endian 32-bit word write synthesizer registers;
separate command bytes operate timer and RF-on/off register state. These commands
belong to the replacement only. `sram.ld` places it at `0x20001000`; the loader
resets and halts the MCU, loads RAM, changes PC and resumes. The assembly changes
the vector-table base, GPIO, UART, SPI, timer and synthesizer state. It is not a
transparent serial adapter for a still-running stock UI.

There is also an integration issue to fix before reuse: `set_rf_freq()` computes
and writes a new register 4 but does not update the Python object's `reg4_on` and
`reg4_off`. Later `rf_on()` or `set_power()` can restore a stale output-divider
field. The code is a useful reference, not a qualified unattended controller.

The separate acquisition loader also resets/halts, writes a RAM program, changes
SP/PC/xPSR, then resumes and disconnects its debugger. That program disables
interrupts, configures GPIO/UART and feeds the watchdog while transmitting flash.
Its inspected code contains no flash erase/program or option-byte write. It still
replaces the running execution state. The author's read-protection behavior is
specific reported evidence, not an established property of the delivered MCU.

The restoration instructions are different: they explicitly unlock, erase and
program flash. They must not be mistaken for acquisition instructions. The public
image is not an established restoration image for this unit. A unit backup would
also need to distinguish MCU flash from the separate EEPROM, option bytes and
other unit-specific state; the supplied 128 KiB image does not contain all of that.

ST-Link and J-Link are available future tools. The current useful result requires
neither. No probe was attached, no LCD cable moved, no serial retry made, and no
firmware or host policy changed during this review.

## Preservation and handoff

The private evidence manifest, source pins, control output and hashes are indexed
by [the repository manifest](rf-source-repositories.toml). Original single-command
evidence and previous task receipts remain unchanged. The
[bounded decision](rf-source-repository-decision.md) selects the next step from
these findings; RF qualification and the broader response milestone remain open.

[gamo]: https://github.com/gamozolabs/max2871-siggen/tree/c6a1d18e0b37e130dae2d5af9fae582cb3b4861b
[gbon]: https://github.com/gbonacini/sigenmax2870/tree/3e208e616adf37a46c6e7a7eb196e4ac414d6ba2
[bryce]: https://github.com/brycecherry75/MAX2870/tree/2773a4b03cc9e6f232d0251ae1a3bf89f9a92f91
[nuclear]: https://github.com/nuclearrambo/MAX2870-PLL-board/tree/7665868deada863bdfadb1029499872bfef6fae6
