# Stock emits the predicted second command word

Run `stock-one-write-01` completed exactly one modeled store after the established two reads. Stock then reached
the predicted second store, which remained unsupported and uncompleted:

| Transaction | Offset | Word | Disposition |
| --- | --- | --- | --- |
| First write | `0x3000` | `0x05630000` | Recorded in the model ledger; PC advanced by four |
| Next write | `0x3000` | `0x01630000` | Captured before completion; no response |

Both use main-thread stock ELF PC `0x27043c`, opcode `0xb9000109`, `str w9, [x8]`. The checker verifies the accepted
store's exact tuple and proves all registers, SP and processor state were preserved except PC. The backing
mapping remained inaccessible, so normal stock execution returned to an observed boundary. The model did not
change the stock routine's return value or supply another read. Terminal `m_DNA` stayed `0x0123456789abcdef`.

This agrees with the [static `Dev_AdcWrite` candidate](stock-next-mapped-access.md): the command's bit 26 is
cleared before the second write. It establishes the two observed operands and their order in this run. It does
not prove the dynamic caller, elapsed 100-microsecond delay, ADC completion or physical register semantics.
The second word was a prediction before this capture and is now a directly observed, still uncompleted store.

Initial coverage contained 21 threads; one main-thread clone added a 22nd. All terminal members were traced,
stopped and exactly reaped with `ECHILD`. The private-controlled native binary is unchanged. The frozen checker
passes without an override, including the explicit native78/helper0 admission outcome, raw index and stock
artifact preservation. Snapshot validation accepted 988 map rows. `system_server` stayed PID1045, final enforcement
was `Enforcing`, and the guest was torn down. No physical instrument access occurred.

The [results manifest](../../experiments/group-observer/one-write-stock-results.toml) pins this evidence.

## Decision

Admit exactly the two now-observed stores in order, with the existing two read responses and a stop at the next
access. Private controls must prove the two-write bound and rejection of altered second operands. Keep the
mapped-access observer; this result identifies no deficiency that calls for a kernel or emulator device.

Do not expand immediately to arbitrary writes at `0x3000`. A broader capture policy could be described honestly
as synthetic acceptance of software write intent, but it would enlarge the successful device surface. First
recover enough stock initialization data to predict a finite sequence or explain why that is impossible. Static
table investigation is decision evidence, not authorization to complete its predicted writes. No readback,
ADC-ready state, device effects or timing behavior follows from this one-write result.

```sh
tools/guest/run-admission.sh fresh-stock-one-write writemodel
kotlin tools/guest/VerifyGroupObserver.main.kts out/guest-admission/fresh-stock-one-write write-stock
```
