# SPU observer control result

The private suite passed all fifteen new SPU controls, all twenty-five existing observer
controls, seventeen malformed SPU inputs and thirteen malformed ADC inputs. This validates
the observation machinery and fixed candidate enforcement; stock SPU execution remains
the next experiment.

Run `group-spu-region-01` used native executable SHA-256
`ac86c83927a0bba752491c388e371d811d7bce9013007a51d2568837659311ae`.
Its frozen independent verifier accepted the complete evidence index and every runtime
arm. The compiled SPU reference is byte-identical to the independently checked stock
fixture. Current sources match the frozen run sources.

Each new runtime control executed the complete 452-write ADC prefix and two existing
synthetic reads. Three controls completed all eight SPU writes: the subsequent main-thread
SCU-shaped write, worker read, and extra recognized SPU write were all left uncompleted.
Two controls accepted one SPU write before rejecting the next operand or offset. The
remaining controls accepted no SPU write after deliberate order, thread, width, binding,
global, pointer, count, sample-mode, shadow or repeated-capture mismatch. Across these
fifteen controls, 6,806 writes were accepted, including 26 SPU writes.

The main thread ran normally between mapped-access stops. Every accepted write changed
only PC, and all other captured registers matched. Private function/object addresses were
checked independently against the executed ELF and compile-time-checked shared layout.
Each control began with two threads, observed one clone, and quiesced and exactly reaped
all three terminal threads. No stock application was installed during this run.

All 45 recorded `system_server` samples across the old and new phases were PID 1065.
Both phases began and ended with enforcement enabled. Dedicated emulator, ADB and
instrumentation listeners were absent after teardown. Stock APK and native library inputs
were not modified.

## Verification limits and corrections

The private program derives SPU operands from its own software state; the observer checks
the separately pinned candidate. Deliberately changed live state is rejected before
accepting the first SPU store. The repeated-capture control records its private-only
mutation explicitly. It does not introduce an unrecorded stock memory modification.

Pre-run review corrected private gain/range formulas, isolated the wrong-order control
from shadow mismatch, and made failure diagnostics identify the actual differing field.
These corrections preceded the single private guest run. An independent review initially
misread a transcript index as a register increment; direct fixture decoding disproved
that finding, which is retained as a corrected review observation.

Two intentionally corrupted evidence copies were rejected: a false sample-mode value and
a changed non-PC register after a modeled store. The first attempt at the corruption
helper failed to parse a hexadecimal prefix before producing either copy; its original
script and error are retained. The corrected helper used a new output directory. Neither
attempt changed the original capture or required another guest run.

Two equal software snapshots are not atomic and cannot exclude change followed by
restoration. Initial function bindings are not continuously revalidated. Terminal shadow
expectations describe the pending access phase, which can already include software stores
preceding an uncompleted mapped write. No register side effects, device readiness, physical
timing, transport success, acquisition or useful UI is established by these controls.

See [control definitions](../../experiments/spu-transcript/controls.toml),
[result manifest](../../experiments/spu-transcript/control-results.toml), and the
[SPU candidate](spu-transcript.md).
