# Stock continues from the command pair to the next mode

Run `stock-two-writes-01` completed exactly the two observed synthetic stores at `0x3000`, words `0x05630000`
and `0x01630000`, after the unchanged two read responses. Stock then attempted another main-thread store at the
same ELF PC `0x27043c`, opcode `0xb9000109`, with word `0x06630000`. That third store was captured before completion
and received no response. Terminal `m_DNA` remained `0x0123456789abcdef`.

The next word matches the mode-one first command predicted by the [stock table analysis](adc-program.md). It is
now directly observed. The trace establishes the completed modeled prefix and the following attempted store,
not physical ADC initialization or a proven runtime call stack.

The frozen verifier passes all response, instruction, ordered-write, PC-only register-change, thread, cleanup,
admission and raw-hash checks. Coverage began with 23 threads and added one traced clone. All 24 terminal threads
were stopped, inventoried and exactly reaped with `ECHILD`. Stock artifacts and the private-controlled observer
are unchanged. `system_server` stayed PID1055 and final enforcement was `Enforcing`; the guest was torn down.
No physical instrument access occurred.

The composite process-snapshot command returned255 again, while the three individual snapshot commands succeeded
and passed the existing independent snapshot gate. This recurrence is preserved; its cause remains unresolved.
The experiment relies on the validated individual captures, not on interpreting the composite status as success.
The [results manifest](../../experiments/group-observer/two-write-stock-results.toml) pins both evidence and checks.

## Decision

The observed three-word prefix agrees with the stock loop's predicted ordering. Admit a bounded finite-transcript
batch for the 440 stores derived from its first110 table entries and both modes. First derive the transcript
independently from the pinned ELF and validate the loop/opcode/relocation assumptions. Then test a strict guest
transcript consumer with private positive, mismatch, count-limit, thread and input-format controls.

Stock execution must verify live GOT targets and table contents, retain the existing read pair, accept only exact
ordered main-thread writes at the known instruction and offset, and stop immediately on any mismatch or next
access after the finite program. Preserve all pre/post register and thread evidence. Do not accept arbitrary
writes or include the later writable-state operations. A mismatch is a valid negative, not permission to grow the
allowlist during the run. No new read response, peripheral-ready state, DMA or acquisition behavior is proposed.

```sh
tools/guest/run-admission.sh fresh-stock-two-writes pairmodel
kotlin tools/guest/VerifyGroupObserver.main.kts out/guest-admission/fresh-stock-two-writes pair-stock
```
