# Complete ADC transcript derivation

The complete static ADC prediction is now a reproducible, bounded input: **452 ordered W32 operands**,
comprising 440 table writes, four constant tail writes and eight initialized-shadow writes. Every value
agrees with the previously recovered conditional transcript. This closes input derivation only; no guest
ran and no full-routine execution or ADC behavior is established by this result.

The [Kotlin generator](../../tools/research/DeriveAdcTranscript.main.kts) reads the pinned stock ELF without
changing it. It validates dynamic symbols and sizes, eleven relocations, five complete function byte ranges,
instruction witnesses, both 111-entry tables and the four initializer/mask words. It derives the shadow
transformations and compares all 452 values against the archived [independent reference](../../experiments/adc-transcript/reference.tsv).
That TSV preserves the earlier static evidence byte-for-byte; it is not a runtime trace.

The [versioned protocol](adc-transcript-protocol.md) binds the expected pointer schedule, tables, source words,
initial and final software shadows, and ordered writes. It has separate stock/private profiles and a private
one-write fixture for exhaustion controls. Inputs are capped at 512 writes and 5,392 bytes. Stock input is
exactly 452 writes and 4,912 bytes. The [derivation manifest](../../experiments/adc-transcript/derivation.toml)
records the generated hashes and layout.

## Verification and limits

Two fresh derivations produced identical files. A separate [wire verifier](../../tools/research/VerifyAdcTranscript.main.kts)
checked all three fixtures against the stock ELF, fixed location schedule and prior transcript. Fifteen damaged
inputs were rejected: magic, version, profile, count, reserved word, truncation, trailing data, oversize,
binding, table word, source word, shadow word, offset, operand and order. These are host verifier checks;
the future guest consumer still needs its own parser and runtime controls.

Initial index-9 state must be `0x6721/0x6721`, and index 8 must be `0x000b`. Predicted terminal values are
`0x5721/0x4721` and zero. They remain writable runtime conditions. Checking inputs before the first store
does not prove that another thread cannot change them later. Matching operands also does not prove the
internal call path or every ignored return value. Those limitations are separate from exact transcript
acceptance and recorded terminal state.

The earlier static index self-reference failure and initial heap-exhausted call index remain preserved at
their original evidence locations. They are not replaced by this successful derivation. Artifact hashes,
verification outputs and implementation-check history are pinned in the [result manifest](../../experiments/adc-transcript/results.toml).

## Reproduce

Set `STOCK_ELF` to the unchanged library extracted from the stock APK and use new output directories:

```sh
kotlin tools/research/DeriveAdcTranscript.main.kts "$STOCK_ELF" \
  experiments/adc-transcript/reference.tsv out/adc-transcript/reproduction
kotlin tools/research/VerifyAdcTranscript.main.kts "$STOCK_ELF" \
  experiments/adc-transcript/reference.tsv out/adc-transcript/reproduction/adc-stock.bin 1
kotlin tools/research/VerifyAdcTranscript.main.kts "$STOCK_ELF" \
  experiments/adc-transcript/reference.tsv out/adc-transcript/reproduction/adc-private.bin 2
kotlin tools/research/VerifyAdcTranscript.main.kts "$STOCK_ELF" \
  experiments/adc-transcript/reference.tsv out/adc-transcript/reproduction/adc-private-one.bin 2
```

The next task implements the consumer and validates it with private controls before the separately admitted
stock run. The stock run will answer whether this whole predicted region survives execution and what
environmental dependency follows it. It will not extend its own transcript.
