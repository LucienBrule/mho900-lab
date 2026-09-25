# Initialization-tail control: inherited breakpoint state

`group-init-tail-01` ended with a valid private negative before completing its first
new read. All 59 earlier controls and 30 malformed-input checks passed with the new
executable. Arm 59 reached the entire 464-store prefix and ten transport checkpoints,
then rejected the initial breakpoint transition. Arms 60 through 74 did not execute.
Stock Sparrow remained absent.

At the first tail read (`R32 +0x4`), all sixteen bindings and eight live-state captures
matched the fixed candidate. The debug transition was:

| Operation | Slot 0 address | Slot 0 control | Result |
|---|---:|---:|---|
| GET, 264 bytes | `0` | `0x1e5` | expected inherited state |
| SET, 24 bytes | `0` | `0` | success |
| GET, 264 bytes | `0` | `0x1e5` | candidate expected `0x1e4` |

Info remained `0x0606`; unused slots remained empty. The observer rejected this
readback with `debug-initial`, before supplying a returned word or arming a new
checkpoint. It completed zero tail reads, writes and checkpoints. All three registered
fixture threads were quiesced and reaped, with final wait result `-10`.

The error was in the prediction of the inherited debug state. The pinned upstream
Linux v3.18 reference skips architecture validation for disabled attribute updates.
Reapplying a clear therefore leaves the cached architecture control unchanged. A fresh
slot's creation-time cached value had been `0x1e4`; the tail inherits the previous
region's disabled slot with cached value `0x1e5`. These are different starting states.
This reference explains a compatible mechanism; it is not established as the exact
guest kernel source. The captured guest readback is the observation.

The narrow continuation is to require the exact inherited address-zero/control-`0x1e5`
state, skip the redundant clear, and directly arm checkpoint zero. Require the same
specific target/control-`0x1e4` readback and full register preservation afterward.
Retain the previously tested clear/rearm sequence after delivered checkpoints. Do not
accept arbitrary disabled encodings or broaden the hardware fixture.

The [result manifest](../../experiments/init-tail/control-results.toml) pins the raw run,
frozen positive verifier, explicit negative adjudicator and independent review. The
positive verifier correctly rejected the incomplete region. The negative adjudicator
checks the actual failed transition without treating it as a private-suite pass.
All 549 indexed artifacts verified. The 67 recorded `system_server` samples remained
1050; enforcement, package absence and stock artifact hashes were preserved. A separate
post-teardown check found no listeners on the four dedicated experiment ports.

This closes the first private hypothesis only. It establishes neither the proposed
direct arm nor stock behavior through the version/DDR region. A separately admitted
private control must pass before the stock task can proceed.
