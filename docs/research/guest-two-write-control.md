# Exact two-store pair: private controls

Run `group-two-writes-01` passed all nine preceding controls and four new pair arms with one rebuilt executable.
The pair is exactly `0x3000 = 0x05630000`, then `0x3000 = 0x01630000`, after the unchanged two read responses.

| Arm | Outcome | Completed stores |
| --- | --- | ---: |
| 9 | Pair completes; following main-thread read at `0x4040` stops | 2 |
| 10 | Pair completes; following worker read at `0x4040` stops | 2 |
| 11 | Changed second value `0x01630001` rejected | 1 |
| 12 | Changed second offset `0x3004` rejected | 1 |

Independent verification binds each accepted store to the exact main TID, instruction PC/opcode, offset and
ordered value. Each completion advances PC by four and preserves all other registers, SP and processor state.
The ledger records both events and the last accepted word. The backing mapping remains inaccessible and no
terminal access is answered. All four pair arms retain composed global `0x0123456789abcdef`.

Every arm observes sibling acknowledgement and one new worker, then inventories three terminal traced/stopped
members and reaps all three followed by `ECHILD`. All thirteen executed binary copies match. Updated checker
replays of the prior one-write private and stock captures also pass. `system_server` remained PID1050 across
fifteen samples; both enforcement samples were `Enforcing`. Stock was absent and the guest was torn down.
No physical instrument access occurred. The [results manifest](../../experiments/group-observer/two-write-results.toml)
pins the full raw index, code and verification evidence.

The controls authorize the already admitted stock pair run with this identical executable. They establish no
ADC-ready, elapsed-delay, peripheral-effect or acquisition behavior. Unknown thread/event schedules and other
accesses remain explicit negatives; this is not a general write-acceptance policy.

```sh
tools/guest/build-group-observer.sh
tools/guest/run-admission.sh fresh-two-write-control paircontrol
kotlin tools/guest/VerifyGroupObserver.main.kts out/guest-admission/fresh-two-write-control
```
