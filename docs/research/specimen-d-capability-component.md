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

## Corrected stock control passed

Run `out/specimen-entitlement/capability-stock-02` completed from 07:05:08 to 07:05:29 UTC with 588 retained
and matching delivered events. Copying the parser return preserved the expected record offset across later
calls. The actual selected row was MHO984 at `0x151b7a0`, with four channels, domain 8 and series 900.

Public stock getters returned MHO984 identity, raw bandwidth enum 17 and effective enum 17, both before
and after original `ParseOption`. All returned status zero. The entire 14-entry option catalog and the
key/license/private seed hashes matched the validated FlexA persistence run. No installation or regeneration
occurred. The guest library was pulled back and matched the unchanged stock input byte-for-byte.

| Artifact, relative to the corrected control | SHA-256 |
| --- | --- |
| `phases/capability/guest-events.jsonl` | `e76e88e59149ce511fd0bf433cd6c6a0d4e2daee4781142ade180f6cf75fa95d` |
| `evidence-sha256.txt` | `c53513b44529b3c7159eaf0fba9d9034012368d22090a910939649af934a7914` |
| `result.toml` | `3baf99124b0faaea5cf9e291d1e1d7ee496adac50ccced31903f98ca4c9f586c` |

## Derived capability comparison passed

Run `out/specimen-entitlement/capability-derived-01` completed from 07:06:43 to 07:07:34 UTC. The separately
derived library has SHA-256 `09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e`.
Exactly 27 bytes differ within the admitted 32-byte replacement span at file/ELF offset `0x42949c`; no bytes
outside that span differ. The original native library and APK remain unchanged.

The same observation code and synthetic persistence seed were used for both arms.

| Observation | Stock control | Derived copy, all three phases |
| --- | --- | --- |
| Public model identity | MHO984 | MHO984 |
| Selected model record | MHO984, `0x151b7a0` | MHO984D, `0x151b850` |
| Raw bandwidth enum | 17 | 18 |
| Effective enum before/after stock ParseOption | 17 / 17 | 18 / 18 |
| FlexA query | true | true |
| Entire option catalog | Seed state | Identical seed state |
| Installer calls | 0 | 0 |

The Java bandwidth enum labels 17 as BW_800M and 18 as BW_1G. These observations establish selection of
software capability policy, not a measured transfer function or a discovered ordinary 1 GHz entitlement.

Fresh-process and same-guest reboot phases reproduced the same identity and enum-18 results. The boot
identity changed, every phase retained 588 matching journal events, and each phase independently pulled
back a native file with the exact derived hash. Key, license, private stream and crypto-witness hashes
remained identical to the original validated synthetic seed. No token was regenerated or reinstalled.

| Artifact, relative to the derived run | SHA-256 |
| --- | --- |
| `phases/capability/guest-events.jsonl` | `148613b4e7d6b645524d33bf097fb4cb8c8ef3e9095dad090b2448b22f2d72ad` |
| `phases/process-reload/guest-events.jsonl` | `b352bf2e9a0b098ce423cfc5c40db688e9f2a8652fa2ea1faff556480311b824` |
| `phases/reboot-reload/guest-events.jsonl` | `ac2fb4081bacfa22661091b5711eb3bd448f5a7414e8ea9e86c48c2b4ef01b27` |
| `evidence-sha256.txt` | `a958643b7166929c79b3d29fa4df0a9476d02184ebdb1d569226e633713a50b5` |
| `result.toml` | `d1b7bb01ea2213a719d3e408bb92b4f2e2a1be48ea9c86ad81e515e04a6bba0c` |

No FPGA or AFE programming, acquisition, calibration, physical deployment or instrument contact occurred.
A separate static observation remains open: API_GetBandValue maps explicit enum 17 to its 100 MHz default,
while enum 18 has a 1 GHz branch. That helper was not invoked in these runs and is not used as a bandwidth
witness; the actual model/raw/effective getters above are the comparison authority.

## Decision and next boundary

The unchanged library has now accepted a coherent synthetic FlexA entitlement and reloaded it across a fresh
process and a real guest reboot. The separate derived library preserves the public MHO984 identity and that
license state while selecting the MHO984D capability record and bandwidth enum 18. An independent audit
confirmed the exact 27 changed bytes within the admitted 32-byte span, the unchanged stock ancestor and APK,
and identical seed files and option catalogs across the derived phases.

These are distinct software results: ordinary token acceptance, harness-directed private-store durability,
and capability-record selection. They do not establish physical entitlement parity, autonomous FRAM writes,
a working full application UI, or analog bandwidth. The initial capability observer failure was a retained
Frida return-value wrapper; copying the returned pointer at the callback boundary resolved that observer
lifetime issue without changing native behavior.

The next bounded batch covers the nine remaining individual option names. It starts with the untested
48-byte consumer path and then checks cumulative installation and combined restart/reboot persistence.
Built-in options, the bundle option, trial expiration, alternative model personalities and physical feature
operation are outside that batch. Each candidate will be sealed and committed before the next begins.

The smallest eventual physical parity question is whether already initialized application memory contains
the identity-derived file keys predicted by the offline corpus. Any such observation needs renewed operator
authorization and a separately reviewed read-only method. No specimen contact is part of this decision.
