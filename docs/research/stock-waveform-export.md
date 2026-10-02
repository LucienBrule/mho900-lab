# Stock waveform export: recovered software contract

This bounded interface recovery describes the preserved stock Sparrow and
packaged Auklet implementation. It separates the software readout contract
from the physical acquisition behavior that remains unresolved. It is not a
specification of the FPGA or a claim of calibrated analog bandwidth.
The selected path is ordinary analog-channel RAW export, matching the CH1
diagnostic; other source types and acquisition modes are not generalized from it.

The input APK has SHA-256
`6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b`;
its packaged native library has SHA-256
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
Addresses below are ELF virtual addresses in that exact library, not runtime
addresses or promises about other builds.

| Boundary | Recovered implementation |
| --- | --- |
| RAW data selection | `CApiWave::getMemoryData`, `0x6314e8` |
| Export setup | `DrvWaveform_ExportInit`, `0x318b88` |
| Trace request | `CDrvScope::ExportData`, `0x2f0cb4` |
| Device read | `DevAnalyzeTrace_Read`, `0x270634` |
| WORD conversion | `CApiWave::toWord`, `0x631a7c` |
| ASCII conversion | `CApiWave::toAscii`, `0x631b80` |
| Preamble | `CApiWave::ApiWave_GetPreamble`, `0x632b1c` |

The RAW query is an active readout transaction rather than a demonstrated copy
from an immutable CPU acquisition cache. Export setup and its corresponding
restoration belong to the stock readout path. A stopped running flag does not,
by itself, establish a hardware buffer generation, ownership transfer or atomic
snapshot across the device and metadata.

The selected export branch sets SPU range and transmit parameters, requests a
normal trace, and reads the acquisition stream. The device read rejects a
positive short read, and the export caller rejects a nonpositive result. These
checks establish a software length boundary rather than hardware generation or
FPGA completion semantics. The bounded path does not expose a decoded frame
identifier to SCPI.
`RequestNormTrace` also calls the internal stop operation and then a device
operation named `SetRun` with selector five. This is distinct from an external
SCPI RUN command and does not, by its name alone, establish a new ADC acquisition.

Ordinary preamble count is a literal one, with a separate averaging-count path.
It is not a buffer-generation token. The native binary formatter contains
`#9%09lld`; the ASCII format branch skips that binary-header logic. WORD
conversion preserves the selected two-byte words without voltage arithmetic.
Vendor documentation and captured binary replies remain separate corroboration
boundaries for a future format comparison.

ASCII conversion loads an unsigned 16-bit word, subtracts the current 64-bit
ground value, converts the signed result to single precision, multiplies by the
single-precision gain, and promotes the result for decimal formatting. The
recovered format string is `%+06le`. Its rounding is part of stock export;
the public ASCII parser continues to consume the resulting volts directly.
No integer scaling should be applied a second time to those ASCII values.

For this analog RAW path, the WORD and ASCII preamble exposes the current vertical increment,
reference 32768, and a signed 32-bit origin derived from ground minus 32768.
When these attributes are coherent and in range, the algebraic relationship is
`(word - y_reference - y_origin) * y_increment`. Exact stock single-precision
rounding and decimal formatting are additional steps. Rounded preamble text
does not automatically preserve the exact internal float coefficient.

The native code obtains gain and ground separately, and the preamble queries
attributes at another time. This recovery does not establish an atomic binding
between those values and a device-buffer generation. That is an explicit
interface limit, not evidence that the attributes changed during an acquisition.

The Java/JNI boundary consists of generic query/post operations. Direct DEX
decoding finds 25 native declarations; the recovered JNI registration table
contains 24 entries. Neither boundary provides a waveform-specific generation
or ASCII-conversion implementation. Generic message posting can still reach
native waveform operations; absence of a named JNI method is not a whole-program
absence claim.

The [physical paired-export diagnostic](rf-linux-bench-migration.md) preserved
twenty fresh stopped acquisitions and forty ASCII replies. Both replies in
every pair are byte-identical, with matching preambles and geometry. RMS still
varies between acquisitions. This validates repeatability for those twenty
readout pairs and does not prove universal buffer lifetime, a physical source
cause, or an accepted replacement for the failed original A1 return control.

The next narrow bench question is whether WORD-before, ASCII and WORD-after
exports from a stopped record agree with the recovered conversion. Equal
bracketing WORD payloads would constrain repeat-read disagreement, while the
ASCII comparison would test the software scaling boundary. Separate readout
transactions and rounded metadata still limit what that result could establish.
Its binary framing, prediction bounds, preservation and restoration must be
prepared before execution; no such physical run is asserted here.

The [supplied-byte WORD/ASCII oracle](word-ascii-readout-oracle.md) now checks
the recovered conversion with independent host controls. It records the exact
binary receive and rounded-coefficient boundaries still required before that
bench question can be executed.


The bounded recovery is sealed in `out/rf/stock-raw-semantics-01.toml`
(`e9749822f4666bfa5e36817946a489c85ec1170ce384462ec2a2ac10f806a38f`).
Independent review is `out/rf/stock-raw-semantics-independent-01.toml`
(`a28df44be98239a3a32660978b07ba70f366e85fb4c02b22c610f9ff1dc297ef`),
with the separately attributed Java/JNI witness in
`out/rf/stock-raw-semantics-java-01.toml`
(`b1bcf50dfa61e15a753eaf510a72a8f00b22c12dda9b86d632ab72d3804b5572`).
The independent check binds selected original instruction encodings, relocated
calls and callback slots; authored controls and tool provenance remain preserved.
