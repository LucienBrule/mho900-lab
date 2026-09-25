# Recover the ADC parameter subsystem before adding responses

The accepted stock loader run supplies a real pre-call record: 1,936 zero
bytes at ADC object offsets `0x8804..0x8f93`. Stock execution is stopped before
`SetADCParameter(0)` at relative PC `0x333ba8`. This makes the complete mode-zero
software path the next bounded question.

Recover the routine through its return, including `SetAdcStary` and the
transitive helpers needed to explain every hardware-facing operation. Record
field addresses, signedness, immutable tables, loop bounds, arithmetic, masks,
shifts, delays, call bindings, branches, and error propagation. Keep runtime
shadows and unobserved globals symbolic. The observed zero record alone is
not sufficient to invent those inputs or FPGA responses.

The deliverable is a typed TOML operation graph checked against pinned stock
bytes, followed by independent review and an explicit decision task. Classify
operations as static-determined, runtime-selected, hardware-returned,
asynchronous, or unknown. A complete software formula and an unknown hardware
effect can coexist at one operation; neither should hide the other.

There is no guest run or observer expansion in this batch. The decision task
will choose selective runtime falsification of a complete predicted sequence
or a bounded capture at the first unresolved input. The current mapped-access
observer remains the preferred boundary: this run validated stock code,
whole-buffer state, and coverage of all observed threads without replacing
native functions. Escalating to a guest driver or emulator-side model needs a
concrete limitation this layer cannot address.
