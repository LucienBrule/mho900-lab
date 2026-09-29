# Acquired-input capability comparison

This separates ordinary FlexA acceptance from a deliberate capability-record
transformation. Both guest arms reload the exact key file, saved FlexA license,
candidate witness and modeled private stream from
[acquired-option-03](acquired-option-persistence.md). No installation or token
generation is part of either arm.

## Frozen preparation

The source seal is
`42edff12ab565ba4b57bb8ec30fb39b3c308472b414a0ff24b0e68e14b888b41`.
Preparation verifies every sealed member and repeats all three source phase
verifiers before copying the four persistent inputs.

The stock arm requires MHO984 identity, selected row `0x151b7a0`, and raw and
effective bandwidth enum 17. The derived arm requires the same public identity,
row `0x151b850` (MHO984D), and enum 18. Both query before and after the original
ParseOption routine and retain the same fourteen-entry option catalog.
Only EMBD, COMP, AUTO and FlexA should be true.

Stock native SHA-256:
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
Derived native SHA-256:
`09689a442e8d285775b37089a8d631e1e445fe03d3499e830cdcc8f32439504e`.
The transformation changes 27 bytes within the previously admitted 32-byte
span at offset `0x42949c`; exact full-file comparison rejects other changes.
Stock ancestor and APK remain preserved.

The stock arm must pass before the derived arm runs. The derived arm then
repeats observations in a fresh component process and after the same guest
reboots. Original license decoder/AES/validator witnesses, byte-identical
persistent inputs, complete journals, exact native pins and the established
guest policy pair remain required. Host network confinement is unchanged.

Preparation passed both fixture checks, six negative controls (physical-contact
flag, wrong bandwidth and wrong native hash for each arm), three prior-phase
verifier regressions, JavaScript syntax and shell syntax. Private preparation
seal: `c6baf8ef05bfd79b972cb98963d42d2dd5dee47e427c7ff72f54a94f5cc82f20`.

Fixtures reside under `out/overnight/fixture-acquired-capability-*-01`;
unit identity, key and token material remain private. These are preparation
checks, not execution evidence. No physical instrument contact is admitted.
Software enum 18 does not establish measured 1 GHz analog performance,
automatic physical FRAM persistence or a vendor entitlement for that bandwidth.

## Stock control passed

Run `acquired-capability-stock-01` completed from 13:16:12 to 13:16:29 UTC.
The original model parser selected MHO984 at `0x151b7a0`; public identity
remained MHO984 and raw/effective bandwidth were 17 before and after ParseOption.
All fourteen catalog values matched the accepted seed, including FlexA true.

The original consumer validated the saved FlexA license. No installer or
producer ran, and all four persistent inputs remained byte-identical.
The unchanged native file was pulled back and verified. Guest health and the
exact known Frida policy pair passed. All 640 journal records matched
delivery with terminal acknowledgment. Independent post-run verification and
original evidence-index verification passed.

Private run seal: `cd666845fecd04e5c6c88933c5e90b9ee2cce21079d57d251774782c8a5b8c25`.
The seal retains inputs, source, phase evidence and logical outputs, excluding
ephemeral emulator disks and ADB runtime directories. This stock result
satisfies the gate for the derived guest arm; no physical contact occurred.

## Derived comparison and reboot passed

Run `acquired-capability-derived-01` completed from 13:17:37 to 13:18:31 UTC.
Initial reload, fresh-process reload and same-guest reboot reload all passed
the frozen verifier. Each retained 640 matching journal records with terminal
acknowledgment. No installer or token producer ran.

| Observation | Stock arm | Derived arm, all three checkpoints |
| --- | --- | --- |
| Public model identity | MHO984 | MHO984 |
| Selected capability record | MHO984 | MHO984D |
| Selected record offset | 0x151b7a0 | 0x151b850 |
| Raw bandwidth enum | 17 | 18 |
| Effective enum before/after ParseOption | 17 / 17 | 18 / 18 |
| Enabled catalog entries | EMBD, COMP, AUTO, FlexA | Same |
| Other ten catalog entries | false | false |
| Installer calls | 0 | 0 |

All four persistent files matched the stock control and the original acquired
installation byte-for-byte. The original stock license consumer accepted the
saved FlexA input at each checkpoint. All fourteen catalog values were equal
across arms. Private bytes were unchanged.

The boot identity changed before the last checkpoint. Each phase retained the
exact derived native digest; independent comparison confirmed only 27 bytes
changed within the admitted 32-byte extent. Stock ancestor and APK remained
unchanged. Guest health, Enforcing state and the exact known Frida policy pair
passed. Post-run verification repeated all phase checks, checked the original
evidence index, compared all seeds and catalogs across arms, and verified the
native transformation. Emulator and dedicated ADB cleanup completed; experiment
ports were clear.

Private derived-run seal:
`2fe45cb66ee864cb65fc61544f6a81f45f573a03e055d0f4feadeddae8a5ab37`.
The same seal scope and runtime-disk exclusions as the stock control apply.

## Decision

The acquired-input result reproduces the earlier synthetic comparison:
ordinary FlexA acceptance survives selection of the MHO984D software capability
record, while public model identity remains MHO984. The two mechanisms remain
separate: the earlier unchanged consumer installed FlexA; this experiment
deliberately transformed capability selection in a disposable native copy.

More repetitions of this same guest identity/license/capability combination
have low information value. The next useful parity question is the untouched
specimen's complete native option and capability baseline, before any persistent
change. A bounded read-only observation should establish the fourteen native
validity results plus actual model/raw/effective capability and reconcile them
with the acquired files. Missing license files alone cannot answer that question.

This decision does not admit that physical observation or any deployment.
Physical install/reboot persistence, automatic FRAM scheduling, full Sparrow UI,
combined all-options/D behavior and RF transfer function remain unproven.
The current demonstrated D result includes FlexA and the three built-ins only.
