# ADC parameter contract review

Independent byte review accepts the bounded mode-zero software contract in
[the static recovery](adc-parameter-static.md). The candidate counts remain
97, 100, or 244 writes and two reads. Live inputs and FPGA effects remain
unobserved; no guest was run in this review.

The reviews crossed component ownership: the helper/getter recovery was checked
by the Stary reviewer, while the helper/getter reviewer checked Stary and the
root-authored integer refinements. Main call order, fields, and count arithmetic
were also checked against the stock disassembly. The selected inventory plus
getter closure contains no unexplained defined direct-call target. Two unnamed
inventory targets both reach the byte-bound mapped-base accessor at `0x271ec4`.
External library implementations remain outside this claim.

Two details were reconciled explicitly:

- The bucket calculation's second multiply consumes a 32-bit operand. Across
  all unsigned 32-bit input delays, the largest intermediate is 4,414,967, so
  this truncation does not change the earlier formula. The fully specified
  finite-width formula and bound are now recorded.
- The series-row field at `+0x10` bounds mask-table entries. It does not establish
  a physical channel count. A future capture should normalize the mask as stock
  does, validate the pointer and an independent safety bound, then read the
  selected mode word. The provisional whole-prefix capture formula is superseded.

[Review refinements](../../experiments/adc-parameter-static/review-refinements.toml)
record both conclusions. The original component reports remain preserved.

The checker now independently walks the selected control-flow ranges from ELF
instructions. It checks complete reachable call and branch sets, decoded branch
successors, resolved call targets, and table values, in addition to range hashes,
relocations, and selected field/loop witnesses. A positive contract passed;
thirteen independently copied altered contracts were rejected for missing
nodes/calls/branches, signedness, field base, loop bound, table operand, relocation,
range hash, successor, target, or integer opcode changes. The checks do not
turn prose formulas into an automatic semantic proof.

Reproduce the controls with a new output directory:

```sh
sh tools/research/test-adc-parameter-contract.sh \
  local/reversing/firmware-extracted/stock-0.26/sparrow/base/lib/arm64-v8a/libscope-auklet.so \
  experiments/adc-parameter-static \
  out/adc-parameter-review-controls-reproduction
```

The next decision can now address a single useful ambiguity: the live matrix,
shadow, and selector inputs at the already established pre-call checkpoint.
It need not add a new hardware response or advance stock execution past that
checkpoint to obtain those inputs.
