# Decision: validate the recovered tail in stock Sparrow

The [complete private pass](init-tail-handoff-controls.md) supports one stock
validation of the fixed [candidate](../../experiments/init-tail/candidate.toml).
Use exactly the executable pinned in
[stock-gate.toml](../../experiments/init-tail/stock-gate.toml), with byte-identical
stock inputs. The earlier redundant-clear negative remains a separate result.

Private evidence now establishes direct initial arming, later rotation, atomic
progress before checkpoint delivery, rejection behavior and thread cleanup on
this guest. Reference-kernel code explains the observed cached-control behavior;
it is not claimed as the exact guest implementation. The ten synthetic register
values remain hypotheses, not measurements of an instrument.

The next run tests the whole recovered region: the validated 464-store prefix,
ten read responses, two software-determined writes, three checkpoints and their
stock parent outputs. Stop before instruction `0x2e57f8`, which begins the path to
calibration. Do not adjust values, guards or device nodes on divergence. Preserve
the first unexpected outcome and evaluate it separately.

This is selective dynamic falsification of the static grammar. A successful
stock run would establish software propagation under this fixture, not physical
DDR calibration, clock behavior or acquisition. Main-thread checkpoints do not
constitute a simultaneous snapshot of all threads. Thread inventories, unexpected
mapped-access rejection and exact group cleanup remain required.

After the result is committed and pushed, recover the next subsystem statically
before introducing further responses. On divergence, first identify whether the
static candidate, runtime selector or observer assumption failed.
