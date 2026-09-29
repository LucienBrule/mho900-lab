# Physical cached identity and acquired key-record coherence

Offline execution of the original stock ARM64 routines reproduces the physical cached file keys exactly.
Using those keys, the stock XXTEA routine and a separate word-level implementation decrypt the acquired
`Key.data` to identical bytes and re-encode the exact original ciphertext. No specimen connection occurred.

The record differs materially from the earlier synthetic fixture: it is 148 encrypted bytes and decodes to
146 printable bytes followed by two zero bytes. Its two semicolon-separated fields have lengths 15 and 130;
the second field consists entirely of ASCII hexadecimal characters. The synthetic fixture used a 32-byte
second field. This result does not establish how the consumer interprets the longer field.

## Inputs and execution boundary

The [physical observation](physical-apk-cached-identity.md) supplies two matching private samples. The
previously acquired `logical/rigol.tar` is verified against its original sealed SHA-256 index; the unique
regular member `rigol/data/Key.data` supplies the ciphertext. All unit-specific bytes stay in private evidence.
The native ELF remains pinned to
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.

Unicorn 2.1.4 executes only the bounded stock derivation, its two leaf helpers, XXTEA key setter,
encode/decode/btea routines and the original btea PLT stub. Unexpected instruction addresses fail.
Each invocation has a one-million-instruction and two-second limit. The retained trace contains PCs;
no stock instruction bytes are modified. Python is used for the Unicorn binding and independent word model.

The emulator maps the original ELF segments and supplies three explicitly reconstructed relocations:

| Relocation slot | Original symbol value | Purpose |
| --- | --- | --- |
| `0xb8d758` | `0xbbccf0` | cached DNA pointer |
| `0xb8cc20` | `0x151b350` | XXTEA key storage |
| `0xb78968` | `0x3be8bc` | stock btea jump slot |

These slots and symbol values were checked against the ELF relocation table. Stack, output buffers and
zero-initialized TLS/canary storage are modeled. During execution, writes are allowed only to stack,
scratch buffers and XXTEA key storage. No constructors, Android services, hardware functions or system calls
are invoked. This is bounded instruction execution, not a booted instrument environment.

## Derivation and controls

For a non-sentinel 64-bit DNA value `d`, the original routine produces these four little-endian words:

1. low 32 bits of `d`;
2. low 32 bits of `d XOR (d >> 1)`;
3. low 32 bits of `d`;
4. high 32 bits of `d`.

The all-ones DNA sentinel instead produces four all-ones words. Six declared synthetic inputs cover zero,
one, a 32-bit boundary, the high bit, a mixed value and the sentinel. Stock execution and the separate
model agree on all six, and both match the physical cached keys. The observed physical DNA is not the
failure sentinel and the observed file keys are not all ones.

A known synthetic plaintext exercises stock/reference XXTEA encode and decode before acquired material is
used. Physical ciphertext decoding then agrees byte-for-byte, and both encoders reproduce the ciphertext.
Flipping one key bit changes the decoded payload to non-printable data. Its accidental delimiter occurrence
also demonstrates why delimiter count alone is not validation. Re-encoding is a consistency check, not a
cryptographic authentication or proof of installed entitlement state.

## Conclusion and next question

Cached identity and the acquired encrypted record are coherent across physical observation, original ARM64
computation and an independent model. This closes the missing DNA/file-key question. It does not establish
that the two decoded fields mean what the synthetic fixture assumed, or recover private FRAM records.

The next bounded task should recover the stock consumer's exact treatment of the 130-character field and
construct a faithful disposable fixture only after that interpretation is supported. Do not truncate,
hex-decode, normalize or substitute the field merely to make a token path advance. Physical installation,
option-query state, reboot durability and feature operation remain untested by this batch.

## Evidence

Private run: `out/overnight/physical-identity-coherence-01`.
The frozen script, input hashes, raw decoded record, key-bit control classification, bounded PC trace and
per-call instruction counts are retained separately from this redacted report.

| Artifact | SHA-256 |
| --- | --- |
| `result.toml` | `f8b47160289dc0ee943912d0947ef3b235836d2a6c105c32c6253490e7cbd31d` |
| `inputs.toml` | `ca17fb958b860b46068e062a453edf7a5b7f61492a30d1ff59708d02b7785023` |
| `instruction-trace.txt` | `15ab9aff6d6cc7ec2c953470cc6230e139512cd14a653cb6ac0e73f719a51c6b` |
| `source.py` | `4e1201aa914f8ee679ec2a998fc65524e8954023782c048bafdd5a82bf530da6` |
| `tool-provenance.toml` | `1e35839041c8896ec5fb5ab6bd28fa6461efdbfbab041ed1c8c550164c252691` |
| `evidence-sha256.txt` | `65309deb3633dcc4f950587b07ffeed71630b77c9a6629199c1858363876159b` |
