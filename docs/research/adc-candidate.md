# Whole ADC programming candidate

The reviewed stopped snapshot supplies enough software state to predict the
complete `SetADCParameter(0)` register sequence. The candidate contains 97
32-bit writes, two hardware-returned words, and 51 requested sleeps totaling
25,200 microseconds. These are static predictions, not newly observed accesses.

The original stock capture remains rejected by its frozen full verifier at the
final index-coverage check. The separate [offline completeness review](adc-input-evidence-review.md)
verified its 325 indexed artifacts and eight separately pinned static contracts.
This derivation uses that reviewed snapshot without modifying or reclassifying it.

## Inputs and selected branch

The decoded calibration record has 62 zero-valued fields, with signed 16-bit
reference/gain/offset/delay fields and unsigned 32-bit fine-gain words. The
captured live shadows are not all zero. In particular, the reference shadows
are `0x5721` and `0x4721`, the shared gain/delay selectors are initially two,
and the two sample-clock register-4 shadows are `0x8000`. Their preserved bits
matter when constructing the actual command words.

Selectors `(8, 900)` choose row two with a mask-table bound of 16. That bound
is not an inferred physical channel count. The observed mask is zero, sample
mode is one, and the signed 64-bit sample rate is zero. The master index is
zero; the configuration delay and point time are both 250000. Signed division
truncates all four derived channel-delay outputs to zero for this snapshot.
The channel-zero scale is 50000000, impedance is zero, and scale bucket is three.

The signed sample rate selects the Stary bypass branch. It writes the existing
adjustment-control shadow with bit zero set and requests a 20 ms sleep. The
captured correction matrix does not contribute register values on this path.
No FPGA readiness, reset state, calibration validity, or acquisition behavior
is established by that software choice.

| Phase | Writes | Reads | Requested delay, µs |
| --- | ---: | ---: | ---: |
| Reference | 4 | 0 | 200 |
| Fine gain | 1 | 0 | 0 |
| Core gain | 32 | 0 | 1600 |
| Stary bypass | 1 | 0 | 20000 |
| Core offset | 32 | 0 | 1600 |
| Sample-clock delay | 16 | 0 | 800 |
| Clock delay and readback | 8 | 2 | 600 |
| Synchronization | 3 | 0 | 400 |

The [candidate manifest](../../experiments/adc-candidate/candidate.toml)
contains ordered operations, all 49 shadow transitions, decoded field locations
and widths, mask words, input hashes, and the predicted final shadows. The
[TSV sequence](../../experiments/adc-candidate/sequence.tsv) is a compact view
of the same operations. Timing describes requested sleeps, not measured latency.

## Remaining unknowns and stop boundary

Both reads are at `0x3004`, after chip-specific register-one read commands.
Bit 16 selects either the low 16 returned bits or an initialized zero value.
The getter XORs that result with `maskValue[1]`, which is zero. The enclosing
clock-delay helper logs the value and discards the child status. No subsequent
branch in this routine depends on either word. The manifest represents these
words as unknown; it supplies no synthetic response.

The stock call instruction is at `0x333ba8`. The normal routine return instruction
is `RET` at `0x33fc78`, with zero return status after its stack check. The caller
resumes at `0x333bac`, whose stock opcode is `0x5285070a`. A future experiment can
use that post-return boundary and stop before executing the next caller instruction.
Successful return would establish stock software progress under the chosen fixture,
not successful hardware programming: the main routine discards helper statuses.

The prediction assumes the captured inputs still apply at entry, a present mapped
base, and ordinary completion of mutex, logging and library calls. A dynamic
successor must check entry state again and observe all threads that can access the
mapping. It must stop on an unexpected access or unsupported thread transition,
without silently inventing another response.

## Independent checks and reproduction

`InstantiateAdcCandidate.main.kts` builds typed write/read/delay operations from
captured fields and shadow mutations. It verifies all 333 reviewed source hashes,
the stock ELF, mask table, mode-zero table entries and return-boundary opcodes.
Its signed arithmetic controls cover negative fields, negative rates, signed
truncation and the 32-bit shifted quantum.

`VerifyAdcCandidate.main.kts` does not import the generator. Its snapshot-specific
oracle inversely decodes command pairs into chip/register/payload transactions,
checks an explicit call-order table, fixed expected shadows and mask words, and
verifies agreement between the TOML and TSV views. This is a separate software
check grounded in the same reviewed grammar; it is not a hardware oracle or a
second execution of the stock instructions.

The host controls accept the complete candidate and reject twelve corruptions:
changed operands in both views, missing operations, ordering disagreement, wrong
signed field type, wrong runtime width, an invented read value, wrong sleep,
wrong final shadow, stale input pin, wrong return boundary, wrong mask and a broken shadow
transition. All controls use fresh independent files; original evidence is read-only.

```sh
kotlinc -script tools/research/InstantiateAdcCandidate.main.kts -- --self-test
kotlinc -script tools/research/InstantiateAdcCandidate.main.kts -- \
  out/guest-admission/stock-adc-input-capture-01 \
  local/reversing/firmware-extracted/stock-0.26/sparrow/base/lib/arm64-v8a/libscope-auklet.so \
  out/adc-candidate/reproduction
kotlinc -script tools/research/VerifyAdcCandidate.main.kts -- \
  out/adc-candidate/reproduction
kotlinc -script tools/research/test-adc-candidate.main.kts -- \
  out/adc-candidate/reproduction out/adc-candidate/reproduction-controls
```

Use fresh output directories. No guest, device response, disk archival action,
stock-artifact modification or physical instrument access occurred in this task.
