# RF source internal-photo follow-up

2026-09-30. Operator-supplied internal photographs add component-marking evidence after the
[source-documentation checkpoint](rf-source-research.md). This is an offline inventory observation under
`TASK.rf.inventory`, not powered qualification or closure of source accession. The previous report and its
receipt retain their original hashes; their exterior-only uncertainty is narrowed by the evidence below.

## Observations and interpretations

The RF package is marked `2871E`, consistent with a MAX2871-family part rather than the MAX2870 named in the
supplied advertising and leaflet. The marking is legible. The exact silicon identity remains an inference:
no authenticated marking-code lookup or electrical identification was obtained.

[ADI's MAX2871 product description](https://www.analog.com/en/products/max2871.html) specifies the same
23.5 MHz to 6 GHz frequency span and pin/software compatibility with MAX2870. It also lists chip-level output
settings from -1 to +8 dBm. These facts make a compatible substitution plausible, while changing the component
documentation relevant to output-level assumptions. They do not establish the delivered module's level, loss,
spectral quality, calibration, firmware or host command protocol. In particular, do not add a fixed 3 dB correction
to a displayed MAX2870 power setting and call that a measurement.

Additional photographed markings support a conventional controller arrangement:

- `CH340N`: consistent with the SOP8 USB-UART bridge in the [WCH product table][wch]. This strengthens the case
  for eventual workstation control. The target has not been enumerated and its firmware protocol remains untested.
- `24C02N`: consistent with a small serial EEPROM. A [manufacturer 24C02-family reference][eeprom] describes
  2 Kbit I2C storage; it does not authenticate this chip's manufacturer or exact suffix. Settings or touch
  calibration storage is a hypothesis, not a recovered layout.
- `XPT2046`: matches the touchscreen-controller family described by [XPTEK][touch]. It is not the main MCU.
- Pads labeled `SWD`, `SWC`, `GND`, `3V3`, plus `BOOT0` and `Calibration` silkscreen, provide useful future
  board-inspection landmarks. Labels do not prove connectivity, MCU identity or the calibration procedure.

The main MCU marking is not legible in these views; the display flex obscures part of the board. Do not promote
the STM32/GD32 identities reported for other boards into an identification of this unit. The oscillator package
is visible, but its frequency marking was not confidently read. The delivered leaflet's 25 MHz output claim
therefore remains documentary rather than a measured clock fact.

## Effect on the first experiment

Retain the original clock and begin source qualification at fixed frequencies using the native controls under
the preparation/integration protocol. Treat the candidate as a MAX287x touchscreen module, with a MAX2871-like
RF marking, until stronger evidence resolves the exact part. A powered UI may still display MAX2870; such a label
would describe firmware presentation, not override a physical marking or independently authenticate silicon.

The board-family match remains useful. Serial-control readiness is stronger than it was from the exterior
alone, but it does not justify sending the published protocol without a bounded compatibility check. Neither
MCU programming, EEPROM access nor reference-clock modification is needed to answer the initial RF question.

## Preservation

Four original photographs, their exact markings, timestamped actor observations and attributed reference checks
are retained in ignored private evidence. The seal is
`c71e950ec458c8124d247006b265eb78241adf64177c2f3b387471a9eeda2bde` (SHA-256 of the artifact manifest).
Detailed board identifiers and images are not redistributed. Manufacturer web descriptions were consulted on
2026-09-30; their live pages are not represented as archived, byte-pinned source documents. WCH and XPTEK family
descriptions were available through indexed manufacturer results; direct page extraction was incomplete.

No hardware contact or change was performed by this review. Inventory, preparation and source qualification
remain open. The new photographs supplement the documentary checkpoint without rewriting its receipt.

[wch]: https://wch-ic.com/products/productsCenter/mcuInterface?categoryId=1&tName=USB+to+UART
[eeprom]: https://www.microchip.com/en-us/product/AT24C02C
[touch]: https://www.xptek.cn/cn/index.asp
