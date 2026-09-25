# One exact modeled store: private controls

Run `group-one-write-01` passed all five preceding controls and four new one-write arms using the same rebuilt
native executable. The two established synthetic reads remain unchanged.

| Arm | First store | Next boundary | Modeled writes |
| --- | --- | --- | ---: |
| 5 | `0x3000 = 0x05630000` | Main-thread store `0x3000 = 0x01630000` | 1 |
| 6 | `0x3000 = 0x05630000` | Existing worker read at `0x4040` | 1 |
| 7 | Changed value `0x05630001` | That store rejected | 0 |
| 8 | Changed offset `0x3004` | That store rejected | 0 |

Each accepted store is bound to the private exact instruction PC, opcode `0xb9000109`, main TID, offset and low
32-bit value. It is recorded in an observer-side ledger. The checker proves PC advanced by four while all 31
registers, SP and processor state remained unchanged. The backing mapping stays inaccessible; there is no
memory write, return-value substitution, new read value or modeled peripheral side effect. Each subsequent
access stops without completion. All four new arms retain composed output `0x0123456789abcdef`.

All nine arms require sibling progress, observe one runtime clone, inventory three terminal traced/stopped
members and reap all three with `ECHILD`. Changed-value and changed-offset arms leave the write ledger empty.
All nine executed binary copies match. The checker also replays the preceding continuation and stock capture.

`system_server` stayed PID 1109 across eleven samples; enforcement remained `Enforcing` in both samples.
Stock was absent, the raw index validates, and the guest was torn down. No physical access occurred.
The [results manifest](../../experiments/group-observer/one-write-results.toml) pins this evidence.

Proceed to the already admitted stock one-write experiment with this exact native binary. The model accepts
one observed transaction, not an arbitrary register stream or an ADC initialization sequence. Private tests
cover these operand and thread schedules; untested instruction widths, runtime races and other outcomes remain
subject to the exact guards and explicit negative handling.

```sh
tools/guest/build-group-observer.sh
tools/guest/run-admission.sh fresh-one-write-control writecontrol
kotlin tools/guest/VerifyGroupObserver.main.kts out/guest-admission/fresh-one-write-control
```
