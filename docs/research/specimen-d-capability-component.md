# Entitlement-preserving capability comparison

This experiment compares unchanged specimen-identical software with one separately derived native library.
Both arms use the same validated synthetic FlexA key, license and private-state seed. The intended comparison
is MHO984 identity with bandwidth enum 17 versus the same identity with enum 18. It is a software-policy test;
no physical bandwidth, calibration or acquisition result is implied.

## Stock-control observer failure

Run `out/specimen-entitlement/capability-stock-01` ran from 2026-09-29 07:00:26 to 07:00:47 UTC. It retained all
355 journal events with matching delivery. The original parser returned the expected MHO984 record at
module offset `0x151b7a0` (event 349). The later helper check failed before the public capability queries.

The helper retained Frida's `onLeave` return object instead of copying its value. The
[Frida API contract](https://frida.re/docs/javascript-api/#interceptor) explicitly says that object is recycled;
it prescribes `ptr(retval.toString())` for a retained copy. The expected offset was observed inside the callback,
but the exact value at the later failed check was not logged. This is an observer lifetime defect, not evidence
that stock model selection chose a wrong record.

A separate static correction is also preserved: `SetModel` returns a C string from the selected record's
field at `+0x40`. It does not return the record itself. The observer therefore watches the original `ParseModel`
return within SetModel, then uses actual public getters for identity and bandwidth.

| Artifact, relative to the run | SHA-256 |
| --- | --- |
| `phases/capability/guest-events.jsonl` | `06b35f876e9f8ac02d5aa99aeba736fdab9c588bb68d085dd9dbcff30d993208` |
| `evidence-sha256.txt` | `cd886f67bdbc54fae36e76d89c836038e9fa6b3fa30e12aa3a344b1daea99b93` |

No installer, token generation, option query or ParseOption call occurred in this arm before the stop.
The stock control gate is unsatisfied, so no derived library was created or executed in this batch.
The bounded continuation is to copy the callback value, preserve the failed evidence, and admit a new control
and comparison batch. There is no physical dependency at this point.
