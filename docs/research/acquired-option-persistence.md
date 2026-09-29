# Acquired-input FlexA persistence experiment

This experiment follows the successful
[separate-field guest baseline](acquired-key-guest-baseline.md). It tests one
ordinary FlexA installation with the preserved specimen's exact Key.data,
cached DNA and independently recorded public identity. The left key-file
field remains separate from the public serial. Private storage is the
accepted baseline's **modeled** stock MemFile stream, not acquired FRAM.

## Frozen preparation

The baseline seal is
`26e48de28bb1829c99ab82e768f7f05bb42d0b36ad87bef600573cedc87a83f6`.
Every member is checked before preparing the new fixture. Its only seed data
files are unchanged Key.data and the canonical private stream containing
record 2337. The fourteen-entry baseline has only EMBD, COMP and AUTO true.

The ordinary candidate is FlexA, native type 5, ordinary license type/time
zero. The actual private fixture requires 48 padded bytes, including room
for NUL termination. The first 32 raw bytes of the preserved right field
supply AES input, as recovered from stock code. The full acquired field and
ciphertext remain intact. No token has been produced during preparation.

The unchanged native pin is
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`;
the APK pin is
`6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b`.
The new acquired-input script, consumer observer and verifier are separate
from the frozen synthetic implementation. Shared runner additions select the
new mode explicitly; they do not relax existing synthetic input checks.

The consumer observer retains original arguments and return values and
records the original hex decoder, AES key setup and all three decrypt blocks
inside the validator invocation. Frida instruments function entries in guest
memory; stock files remain byte-identical. A positive result requires stock
validation, activation result 24531, one exact catalog transition and a
stock-written license file. Subsequent process and same-guest reboot phases
must reload without another installer, token producer or private-store format.

The host-loopback child confinement and inherited-network controls remain
required. Guest health must remain enforcing with a stable system server
within each boot. Only the exact previously established Frida policy pair
is allowed; the reboot must change the boot identity. Any other policy,
stock-pin, journal, hardware-call or health discrepancy stops the run.

Preparation is private under `out/overnight/fixture-acquired-option-01`.
The preparation evidence directory is
`out/overnight/acquired-option-preparation-01`, with source snapshots and
fixture inventory digest
`d655434917276895c08064681bd03fca4069868b7ae220528c3d135402789f3e`.
Fixture validation passed, as did three negative controls for a physical
contact flag, a wrong AES prefix and a wrong option type. The prior synthetic
catalog fixture still passes its unchanged verifier. JavaScript/shell syntax
and Python compilation checks passed. These checks are preparation evidence,
not a successful installation claim.

No physical scope access is part of this batch. Even a successful guest
result will not prove physical private-storage scheduling, current physical
options, FlexRay operation or any RF capability change. Unit identity, key
material and resulting tokens remain outside tracked source.
