# WORD and ASCII: supplied-byte readout oracle

The [stock waveform recovery](stock-waveform-export.md) identifies a useful
representation question: do WORD and ASCII exports agree under the recovered
stock conversion? This preparation makes that question testable with supplied
bytes. It does not implement a physical binary collector or establish a new RF
measurement result.

The original stock A1 return control remains failed. The later diagnostic
preserved twenty separate RUN-to-STOP acquisition positions, each with two
byte-identical ASCII exports. Those forty replies do not constitute forty acquisitions,
an accepted replacement A1, or any of the fifty missing B/A2 comparison slots.

## Framing evidence

The preserved official MHO900 Programming Guide has SHA-256
`a671c065bd04a85d05e9d4cef732df3ba4884c2218054f64d1a83fb5a43cffd5`.
PDF pages 491 and 494, printed pages 467 and 470, describe a definite-length
binary header and two bytes per WORD point. The reviewed sections mention an
end identifier without specifying its exact bytes. They do not specify WORD
byte order. Complete relevant pages were rendered and independently inspected.

| Boundary | Evidence | Prepared behavior |
| --- | --- | --- |
| Payload extent | Vendor guide: byte count; two bytes per WORD | Require twice the supplied point count |
| Header profile | Recovered stock literal `#9%09lld` | Accept `#9` and nine decimal length digits |
| Byte order | Recovered AArch64 unsigned halfword handling | Explicit little-endian implementation profile |
| Binary suffix | Exact device suffix remains unresolved | Require a supplied policy; preserve original trailing bytes |
| Delimiters inside payload | Arbitrary binary sample bytes | Preserve LF, CR and NUL as data |

The decoder retains the complete response, header, payload, suffix, unsigned
words and hashes. Named outcomes reject malformed headers, odd or truncated
payloads, point-count mismatches and unexpected suffix bytes. Supporting a
supplied no-suffix, LF or CRLF fixture is not evidence that the instrument emits
that suffix. The existing line-based SCPI reader is unsuitable for WORD data.

## Conversion evidence and controls

The oracle takes exact supplied binary32 gain bits and a signed 64-bit ground
value. It follows the recovered unsigned-word load, modular 64-bit subtraction,
signed conversion to binary32, binary32 multiplication, widening to binary64,
and `%+06le` decimal formatting. Original sample bytes, binary32 result bits,
widened volts and decimal tokens remain separate outputs.

The arithmetic profile declares nearest-even rounding and C-locale formatting.
It does not establish the physical process's floating-point control state,
locale, or coherence of its separately read attributes. Nonfinite coefficients
and finite-result overflow have explicit rejection outcomes. Negative zero and
subnormal results are preserved. Within this integer-word domain, a nonzero
integer stage has magnitude at least one, so a nonzero binary32 gain cannot
produce a nonzero product smaller than the minimum binary32 subnormal.

Meaningful controls cover binary delimiters, byte order, framing and count
boundaries, forged retained values, signed-reference wrap, direct integer
rounding, decimal tokens, negative zero, subnormals and overflow. An independent
compiled C implementation checks both result bits and decimal strings under
its declared host rounding and locale. Host agreement validates the supplied
model; it is not stock execution.

The observed preamble gain `6.6667E-06` is rounded text. It must not be promoted
to the exact hidden binary32 coefficient. A physical prediction needs either
an independently justified formatter interval or separately observed exact
attributes, with coherence stated explicitly. No fitted gain, RMS correction,
record exclusion or change to the public ASCII parser is part of this work.

## Next bench question

The proposed distinct diagnostic is one stopped record exported as
WORD-before, ASCII, WORD-after. Preserve the original ordinary and export
settings; hold the electrical path, channel, memory extent, rate and scale.
Capture every complete response and adjacent preamble. Do not issue RUN or
change a setting during any export. Change format only after a complete
transaction, recording format values 1, 2, 1. Compare all other geometry and
attribute observations separately from that intentional format difference.
Restore the original export, ordinary and run state after the test.

Unequal WORD brackets would establish stopped-byte disagreement for that
record. Equal WORD brackets permit a conditional conversion comparison; an
ASCII result outside a justified prediction would falsify the declared coherent
conversion model for that record. Matching results would establish agreement
under those assumptions. Neither outcome independently identifies a hardware
generation, proves unchanged hidden attributes, assigns a source-versus-ADC
cause, or establishes calibrated analog bandwidth.

Physical execution remains blocked by the missing length-framed receive path,
unresolved actual binary suffix and exact-gain prediction boundary. The pure
oracle allocates no physical comparison slots and admits no native transition.
The preparation and decision tasks preserve those limits as an explicit next
boundary rather than substituting synthetic assumptions for a bench witness.

The supplied oracle is sealed in `out/rf/raw-format-oracle-01.toml`
(`421e579dee44f15eef0392b38ba35b06feab7c730c3dcaf0c66a3525a7542f75`).
Independent compiled-C review is
`out/rf/raw-format-oracle-independent-01.toml`
(`2f0b2251b2523639993ebe0f7b17acbeed919753b6f219347805ba60e9a82c30`).
The separately attributed primary-guide review is
`out/rf/raw-format-protocol-review-01.toml`
(`7e3e4de27409352c16393c5414361e1dc2f1e04d8291e6745ada33d84cae0a05`).
These inventories preserve original inputs, code, commands, runtime provenance,
controls and negative outcomes. They were verified against their exact contents.

A bounded precision follow-up confirms a candidate `%.4E` formatter in the
preserved stock bytes. Its selection for PRE output remains unresolved; matching
the observed token is insufficient to infer that selection or a gain interval.
The independent candidate review is
`out/rf/raw-format-precision-independent-01.toml`
(`ae612fab7e2dfb775245b759ffa1c0e4689291df7e609e45ce03ed5d8741984d`).
