# Private ADC sequence attempt 02

The frozen private suite reached the guest, accepted arms 101–107, then stopped
at arm 108 because the per-arm verifier expected the wrong load opcode. Arms
109–112 were not executed. This is a partial private-control result, not stock
admission or a complete observer qualification.

Arm 101 completed all 99 predicted mapped accesses: 97 writes and two synthetic
reads. The private worker acknowledged progress; the final atomic loop completed
once; the two read responses decoded to `0x1234` and zero; all 33 final shadows
matched. The precise terminal instruction remained unexecuted. These are actual
private guest observations, not stock ADC execution or measured FPGA behavior.

Arms 102–107 passed the frozen negative checks for changed, reordered and omitted
operations, an unknown read, the wrong terminal PC and an entry configuration
mismatch.

For arm 108, the trace reports a worker-thread read at offset `0x3004`, PC
`0x238900`, opcode `0xb9400109`. The observer rejected that access for thread
mismatch before supplying a response or advancing the ADC sequence. All three
tracked threads were reaped. Independent disassembly of the pinned ELF identifies
that same instruction as `ldr w9, [x8]`, a 32-bit load. The frozen checker instead
expects `0xf9400109`, the 64-bit form. The trace and compiled instruction agree;
the width expectation in the checker is wrong. The original checker rejection
and run evidence remain unchanged.

The suite audit also rejects the incomplete run. All 492 indexed artifacts
independently match their recorded digests. `system_server` remained PID 1054
through all eight attempted arms and final health collection. Enforcing remained
active, Sparrow was absent, the final health commands succeeded, teardown
succeeded, and the four reserved local ports were idle afterward. The stock APK
and native library retain their expected hashes.

The next bounded question is a verifier correction against the already compiled
worker instruction, followed by a separately frozen private suite. It must retain
the native executable and modeled responses, test acceptance of the actual
worker record and rejection of a changed opcode, and preserve this failed suite.
The four remaining controls still require guest execution before stock admission.

Evidence hashes and the frozen run identity are recorded in
`experiments/adc-sequence/private-run-02-results.toml`.

Administrative note: the runner-isolation closure receipt's manually entered
`recorded_at` is later than the actual closure. The commit and run timestamps
establish ordering: the freeze and closure were pushed before this run started
at `2026-09-25T19:13:27Z`. The immutable receipt is retained as written.
