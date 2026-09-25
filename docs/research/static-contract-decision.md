# Decision: validate the complete ADC region

Static recovery supports a change in research method: predict complete software regions, validate the inputs
and sequence once, and spend subsequent runs on divergences or new environmental dependencies. Preserve the
existing mapped-access observer and stock instructions. No kernel facade or broader device model is justified
by the current evidence.

The [userspace contract](static-initialization-contract.md) predicts 452 ADC stores and an additional eight SPU
stores. The [kernel contract](kernel-abi-contract.md) corroborates XDMA character-device plumbing while leaving
FPGA behavior and the separate `dma_auklet` provider unresolved.

## Ranked ambiguity boundaries

| Priority | Question | Evidence needed |
| --- | --- | --- |
| 1 | Does the live ADC routine use the recovered tables, bindings and initialized shadows? | Capture and compare those inputs before accepting its first store. |
| 2 | Does the complete 452-store prediction survive normal stock execution? | One finite ordered transcript; stop on any divergence or next access. |
| 3 | Which SPU shadow values and sample-mode records are selected? | Capture four shadows and separate gain/range configuration selections. |
| 4 | What values and status relationships do later SCU/ADC/DDR reads require? | Recover the consuming branch, then admit explicit synthetic hypotheses. |
| 5 | What owns `dma_auklet` buffers and completion? | Identify its provider and correlate ioctl/data behavior; XDMA is insufficient. |

The first two questions form one bounded validation region. The next unsupported access is predicted to be
the SPU reset store at `0x1000`, but that remains a falsifiable prediction. Preserve an earlier mismatch,
unexpected thread, signal or timeout as the result. Do not grow the transcript during the run.

## Selected boundary and alternatives

Use a finite sequence of expected stock W32 operands, executed by completing only the exact witnessed store
instruction. Normal stock execution between accesses remains uninterrupted. The mapping stays inaccessible;
each accepted store updates an evidence ledger and advances the PC. This is explicitly synthetic write
acceptance, with no readback, register side effect, device-ready transition or sample-data claim.

Validate live table pointers and all 111 words in both tables. Validate relevant stock function and shadow
bindings, and capture index-9/index-8 shadows before the first write and at the terminal boundary. Require the
initialized values used by the prediction. Check every expected operand; do not accept arbitrary writes merely
because their offset is `0x3000`. Preserve thread attribution and stop on a worker attempting even the expected
store. All paths remain bounded by input size, operation count, thread count, events and wall time.

The writable tail is included because its complete transformation is known and its initial state can be
checked. SPU remains the next region because it adds four writable inputs and two potentially different
configuration records. Their static sequence is already recovered; future work should validate the region
as a unit. A successful ADC result must therefore lead to SPU input capture/selection, not eight separate
write-discovery experiments.

A guest character-device backend would reproduce plumbing that is already well constrained while leaving
register behavior equally unknown. Emulator-side observation is a fallback if mapped-access exceptions or
thread scheduling prevent faithful region validation. Higher native-function substitution would discard the
stock command construction and failure-handling evidence we are trying to preserve. None is needed merely to
skip known writes faster.

## Successor task batch

Revise the existing deferred batch, retaining its task identities and immutable history:

1. `TASK.hardware.adc-transcript`: derive and pin the full 452-word program and a bounded versioned input
   protocol, including table/binding validation data and private fixtures. Compare all words independently.
2. `TASK.guest.transcript-control`: validate the consumer with private full-sequence and negative controls,
   including wrong operand/order/offset/width/thread, malformed input, exhaustion and live-input mismatch.
3. `TASK.hardware.adc-table-loop`: despite its historical identifier, test the complete ADC routine using the
   revised contract. Keep exactly two existing synthetic reads, accept only the prescribed writes, and stop
   at divergence or the next access. Capture software state and group cleanup.
4. `TASK.hardware.adc-loop-decision`: evaluate the region and select the next ambiguity from the graph.

Plan and inspect each contract revision, record explicit semantic reconciliation, then commit and push the
revised batch before implementation. Commit and push the input derivation and private-control conclusions
before their dependent execution tasks. The original 440-store-only scope is superseded, not silently resumed.
