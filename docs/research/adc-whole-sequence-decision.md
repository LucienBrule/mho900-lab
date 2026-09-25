# Whole-sequence ADC decision

The static candidate is complete for the captured entry state: 97 writes, two
logging-only readbacks and 25,200 microseconds of requested delay. The independent
host oracle and twelve corruption controls passed. This supports validating the
whole predicted routine with a stop at its return, while retaining mapped-access
observation and ordinary instruction execution between accesses.

The next batch builds and tests that observer with private controls before
admitting a stock continuation. Chip zero will receive the explicit synthetic
word `0x00011234`; chip one will receive `0x00000000`. These exercise both branches
of the known local read protocol. They are not proposed physical register values.
The model must reject every unsupported access and stop at caller PC `0x333bac`
without executing that instruction. It supplies no next-subsystem response.

Entry checking must compare relevant typed values and normalized relocation
bindings, not raw pointer bytes from the old process. Thread coverage is also a
first-class control: the suite must demonstrate ordinary worker progress, atomic
completion before the breakpoint, detection of another thread's device access,
and explicit handling or rejection of clones. Freezing a required worker is not
an acceptable way to obtain a successful sequence.

The selected boundary still exposes the stock program's actual mapped loads and
stores. No current finding justifies replacing the kernel device layer or native
calibration function. If private controls expose a synchronization or coverage
limitation, that result becomes a decision event before any stock run.

## Capacity and preservation

A separate task will losslessly archive the two finalized raw backings identified
in the [capacity review](adc-guest-capacity-review.md). Each compressed image must
be restored to a fresh independent file and checked byte-for-byte before its
redundant original is removed. Dependent overlays, original evidence indexes and
all indexed artifacts remain unchanged. Actual reclaimed capacity is measured;
the unchanged 2 GiB preboot gate remains mandatory. No archival action occurred
in the completed review or candidate derivation.

Available capacity fluctuated back above 2 GiB during the offline work, without
project deletion. That narrow margin does not establish enough headroom through
another suite. The separately admitted archival task provides a reproducible
preservation and restoration path rather than assuming reported blocks are
uniquely reclaimable.

The immutable capacity-review closure receipt has an erroneous manually entered
`recorded_at` of `2026-09-25T15:45:00Z`. Its closure commit `128711a` was recorded at
`2026-09-25T15:33:44Z`. Use the Git/taskctl transaction chronology for ordering;
the original receipt remains intact. Subsequent receipt timestamps are generated
from the clock.

The original stock capture's frozen full-verifier rejection remains unchanged.
The separate offline review and the new candidate do not turn it into an accepted
original experiment. No physical instrument access or stock artifact modification
is part of the successor batch.
