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
