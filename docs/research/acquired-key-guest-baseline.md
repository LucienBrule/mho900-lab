# Acquired-key guest baseline: preparation stop

The first specimen-derived fixture stopped before guest creation. The decoded
Key.data left field is **not equal** to the serial in the preserved physical
`*IDN?` response. The preparation required equality and rejected the input.
Neither field was rewritten to make that check pass.

This is a failed fixture assumption, not evidence that stock Sparrow rejects
its own key file. The [coherence result](physical-identity-coherence.md) still
shows that physically observed cached keys decode the acquired ciphertext
consistently in stock instructions and an independent model. The
[consumer recovery](acquired-key-field-consumer.md) establishes the right
field's AES input semantics but does not establish that the left field must
be the public serial.

Tasking was admitted and pushed in `94e9ffb`. Preparation used the sealed
coherence artifacts and sealed raw B1 response, comparing bytes locally.
An initial host-only preparation error expected the B1 hash index in the
wrong format; inspection corrected that to its existing TOML manifest before
the substantive equality check. No fixture directory existed after either
stop. The retained replay independently reproduces the equality rejection.

`out/overnight/acquired-key-baseline-preparation-01` retains source snapshots,
the failing invocation's stdout/stderr, a private comparison, result manifest
and sealed hash index. No unit values are published here. The prospective
guest baseline source and runner support are retained as **unexecuted** work;
syntax checking alone does not establish their runtime correctness.

No guest, installer, token producer or scope connection was started. There
is therefore no new guest option catalog, private-store delta or persistence
result. The physical APK/native originals and acquired key file remain
unchanged. No interpretation of current specimen option state follows.

The next question is exact: **does stock code use Key.data's left field as an
identity constraint, and if so, which identity and comparison?** Trace both
the startup verifier and ordinary install caller before revising the fixture.
Preserve the physical public serial and the acquired left field separately
unless stock code demonstrates a relationship. This can be resolved from
the preserved library before considering another bench observation.

## Separate-field baseline passed

The [left-field recovery](key-left-field-semantics.md) resolved the failed
assumption. Its conclusion was pushed in `325a064` before the corrected guest
run. Preparation schema 2 preserves physical public serial and key metadata
as separate values; it changes neither the acquired file nor the specimen.

Run `out/specimen-entitlement/acquired-key-baseline-02` completed on
2026-09-29 from 12:44:47 to 12:45:03 UTC. The original ART-loaded stock
component returned from License initialization. Its parser produced the exact
130-byte right field and original left field, and stock identity derivation
matched the captured 16 file-key bytes. The full 148-byte Key.data ciphertext
was unchanged before and after. No installer or token producer ran.

The initially empty modeled private store acquired exactly one record:
2337, containing the exact 148-byte ciphertext. The fourteen-entry option
catalog returned true only for EMBD, COMP and AUTO; the other eleven were
false. These are **fresh modeled-store results**, not the physical scope's
option state. No license file was created. Persistence has not yet been
tested with these acquired inputs.

All 467 guest journal records matched delivered host payloads and the durable
terminal acknowledgement. The pinned APK/native files round-tripped exactly.
The network isolation control passed, including inherited restrictions;
the dedicated emulator, instrumentation and ADB processes were stopped.
System-server identity stayed stable and SELinux remained enforcing.

An initial verifier incorrectly demanded identical pre/post guest-policy
bytes. Its source and failed replay are retained. The exact pair instead
matches the already documented [Frida fixture limitation](specimen-entitlement-baseline.md):
before `d42d4591e6a44551d969db387403b751aef0bb1bb0654f8e05ae7c9a10d224bc`,
after `9fc3a821a681116e425f87b9a4eeb73f62b1e299e025709e6f566236761b2181`.
The reconciled verifier requires those exact hashes, not arbitrary policy
changes. No guest rerun or experiment modification was used to obtain this
result. No host security policy was changed.

The independent verifier checks raw parser output inside the original init
call, acquired identity and key bytes, the private stream record contents,
catalog completeness, artifact pins, journal delivery and guest health.
It does not independently implement stock private-record CRC validation or
prove every absent operation from event absence alone; the frozen script
also installs stop observers at the installer and crypto-producer entries.

`sealed-evidence-sha256.txt` covers retained evidence and source/fixture
snapshots. Ephemeral guest disks, AVD runtime files and fresh ADB home state
are excluded; their pulled logical state and logs are the retained witnesses.
Private key fields, public unit serial and file-key bytes remain local.

## Decision

The acquired-input baseline is established. The next bounded question is one
ordinary FlexA installation in this disposable component, followed by a new
process and an actual guest reboot. Use the accepted baseline's exact key
file, separate identity fields and modeled private record as the seed.
Observe the original consumer's key bytes, decoded token blocks, validation,
catalog transition and saved license; reload without producing or installing
another token. Choose the padded token length from the actual private fixture,
not the shorter synthetic serial used by the earlier experiment.

This continuation needs no physical contact. It cannot establish physical
FRAM persistence or the existing specimen's option state. Any guest policy
pair beyond the exact established Frida pair, lost journal, changed stock
pin or new hardware call is a stop condition.
