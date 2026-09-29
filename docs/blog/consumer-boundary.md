# The roundtrip that proved the wrong thing

Draft, 2026-09-29. Based on the [synthetic entitlement trials](../research/synthetic-entitlement-trial.md).

The token decrypted perfectly. The application still rejected it.

In a disposable Android guest, the original oscilloscope library was running its own license parser. The
fixture had a coherent synthetic identity, a declared key and an encrypted token. A producer-side roundtrip
returned the expected plaintext. That looked reassuring until the stock consumer said no.

The roundtrip had answered a smaller question than intended: could the producer undo its own transformation?
It had not shown that the producer's text representation meant the same thing to the application.

The decisive observation was at the consumer boundary. The application's text decoder interpreted each byte
with its low nibble first. Conventional hexadecimal text was therefore not interchangeable with its wire
format. A byte represented conventionally as `29` needed the reversed nibble order for this decoder. The
cipher could be correct while the bytes presented to it were wrong.

Once the fixture matched that representation, the original consumer recovered the intended plaintext and
accepted the positive case. A wrong-name fixture traversed the same decoder and cipher path and was rejected.
That negative control mattered: simply seeing execution advance would have left open whether the harness
had accidentally skipped validation.

There were several distinct observations to keep separate:

- The outer native call returned zero.
- The producer could roundtrip its own bytes.
- The consumer decoded the intended ciphertext and plaintext.
- The original validator accepted the option.
- A later process loaded the saved license and queried it as valid.

Only the later observations answered the installation question. None established operation of the physical
feature named by the option.

The corrected experiment eventually extended across ten individual options, fresh-process reloads and a
real guest reboot. Its [catalog result](../research/individual-option-catalog.md) is useful because the
failed producer assumption remains visible beside the successful consumer evidence.

The general lesson is practical: when a roundtrip passes but a real consumer rejects the output, inspect the
representation crossing the boundary. Two routines agreeing with each other can still agree on the wrong
contract. Preserve the failed fixture, observe what the consumer actually receives, and use a negative
case that reaches the same path.
