# Mode-zero ADC parameter software contract

The stock `SetADCParameter(0)` path can be recovered as a whole software
program. Under the previously captured zero ADC record it has three candidate
write counts, selected by live sample-rate state, and two hardware readbacks.
No guest was launched and no new device responses were introduced for this
recovery.

| Sample-rate branch | Mapped writes | Mapped reads | Requested delay |
| --- | ---: | ---: | ---: |
| At or below 500 MHz | 97 | 2 | 25,200 µs |
| Above 500 MHz, outside the supported branches | 100 | 2 | 45,200 µs |
| 1, 2, or 4 GHz | 244 | 2 | 45,200 µs |

These are conditional static predictions, not observed transcripts or measured
elapsed times. They assume the captured zero main record, a valid mapped base,
normal library returns, and valid runtime object inputs. Sample-rate comparisons
convert a signed 64-bit value to double; the precise conversion is part of the
contract. Neither completing the routine nor its zero return proves successful
FPGA configuration.

## Inputs and provenance

The authoritative consumer is the unchanged stock `libscope-auklet.so`, SHA-256
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
The disassembly input has SHA-256
`f9bd4a0b93b6037faa6f9d9d78d54543aeab50079c388a6e468641fa08810d09`.
The accepted [loader run](calibration-stock-loader-run02.md) stopped before the
call at library-relative PC `0x333ba8`. Its entry and terminal ADC captures were
both 1,936 zero bytes from `adc+0x8804`, SHA-256
`3fcb1e1041f63f752bdebe8f875700003bd95e3fc507c2143555443c145c9769`.
This fixes the 62 main record fields for that captured state. It does not fix
unobserved calibration data or live register shadows.

The [contract directory](../../experiments/adc-parameter-static/) separates:

- `main-grammar.toml`: ordered calls, field widths and signedness, loop bounds,
  argument mappings, normal return, and exceptional stack-check edge.
- `stary-grammar.toml` and `stary-refinements.toml`: sample-rate branches,
  matrix selection, lane permutation, delay arithmetic, and ADC state writes.
- `helper-grammar.toml` and `helper-refinements.toml`: register packing, masks,
  shadow updates, read protocol, relocation bindings, and transport behavior.
- `getter-inputs.toml`: object fields and runtime tables behind the selectors.
- `integer-refinements.toml`: primitive rate/impedance getters, signed probe
  delay addition, finite-width quantization, and selector-bound interpretation.
- `call-inventory.toml`: byte-bound control flow, calls, and tables for 35
  selected function ranges. The 17 getter ranges are bound separately; two
  overlap this inventory. The unnamed mapped-base leaf remains unnamed in the
  symbol inventory, with its load semantics described in the getter contract.
- `scope.toml`: classification, conditional counts, and unresolved inputs.

Refinement files qualify their base grammar explicitly. In particular,
`maskValue` is immutable source data, while the fifteen writable shadow objects
require live values. The read protocol has a hardware-dependent local branch;
its caller does not use that status to choose further initialization work.

## Recovered operation order

The main routine makes 35 normal call invocations at 13 call sites:

1. Two reference settings from signed 16-bit fields.
2. One fine-gain word assembled from sixteen unsigned fields.
3. Sixteen core-gain settings, grouped into four channel helper calls.
4. The complete `SetAdcStary` subgraph.
5. Sixteen core-offset settings.
6. Eight sample-clock settings in table order `[0, 2, 1, 3]` for each chip.
7. Two clock-delay settings, each followed by a register-1 readback.
8. One synchronization pulse sequence and the normal return.

Outside `SetAdcStary`, this expands to 96 mapped writes and two reads. ADC
programming uses a command write, a requested 100 µs delay, and a second write
clearing the command bit. The read protocol adds two such command writes,
two 100 µs delays, and one read at offset `0x3004`. Its bit 16 controls whether
the low sixteen bits are copied. The outer getter discards the protocol status;
the clock-delay caller logs the resulting value. There is no readiness poll in
this recovered path.

Core gain and offset shadows are shared selector arrays: the chip argument
selects the transport destination, not a second shadow-array dimension. The
clock-delay formula preserves the original OR behavior, including retained
coarse-delay bits. These details matter when deriving exact write operands.

`SetAdcStary` performs either one bypass write, four setup writes, or four setup
writes plus sixteen lanes of nine writes each. The supported branches select
matrix entries through recovered scale, impedance, delay, and lane formulas.
Its matrix window is `adc+[0x4eb4,0x5cf4)`, 3,648 bytes, entirely outside the
accepted record capture. It also writes the computed delay bucket at
`adc+0x4e94` and `adc+0x4e98`; a separate read at `adc+0x87f4` is diagnostic.

## What remains unknown

| Class | Recovered software rule | Remaining input or evidence |
| --- | --- | --- |
| STATIC-DETERMINED | Call order, loops, constants, immutable tables, masks, delays | Independent byte review and selective runtime falsification |
| RUNTIME-SELECTED | Matrix addressing, scale/rate/delay selection, shadow updates | Live matrix, object fields, series selection, and fifteen shadow objects |
| HARDWARE-RETURNED | Two `0x3004` reads and their local protocol branch | Register values, reset state, readiness timing, and physical meaning |
| ASYNCHRONOUS | No new asynchronous device operation is called here | Existing process threads and mutex behavior remain relevant |
| UNKNOWN | Software write operands can be predicted once inputs are bound | FPGA effects, conversion behavior, analog calibration, acquisition |

The getter closure reaches primitive channel, probe, trigger, series-table, and
sample-rate fields. It does not conceal another device read. Standard library
and Android logging implementations are external boundaries, not recovered
subsystems. A returned object pointer being valid is an explicit assumption.

The next useful input question is therefore a bulk observation at the existing
pre-call checkpoint: what matrix, selector, and shadow state does unchanged
stock execution carry? That can select and instantiate a complete candidate
sequence. It does not require discovering each deterministic write in a
separate guest run.

## Reproduction and limits

Run the extractor with an unused output directory:

```sh
kotlinc -script tools/research/RecoverAdcParameter.main.kts -- \
  local/reversing/firmware-extracted/stock-0.26/sparrow/base/lib/arm64-v8a/libscope-auklet.so \
  out/adc-parameter-reproduction

kotlinc -script tools/research/VerifyAdcParameter.main.kts -- \
  local/reversing/firmware-extracted/stock-0.26/sparrow/base/lib/arm64-v8a/libscope-auklet.so \
  experiments/adc-parameter-static
```

The extractor decodes control-flow and direct-call provenance from pinned ELF
bytes. Only three reviewed mode-zero selector branches are pruned; other
branches remain explicit. The checker binds ranges, symbols, relocations,
tables, and selected instruction witnesses. It does not automatically prove
all prose formulas or all possible runtime object states. Independent semantic
review is a separate task before admitting a runtime experiment.
