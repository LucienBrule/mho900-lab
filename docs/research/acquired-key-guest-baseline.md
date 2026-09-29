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
