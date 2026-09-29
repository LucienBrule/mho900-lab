# Acquired key-field consumer

The ordinary option verifier uses the first 32 **raw string bytes** of the
Key.data right field as its AES-256 key. It does not hex-decode that field.
The acquired field's 130 printable hexadecimal characters therefore do not
imply a 65-byte cryptographic input to this consumer.

This conclusion applies to specimen-identical Auklet SHA-256
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
It follows the [physical identity coherence result](physical-identity-coherence.md).
All analysis here used preserved files; no instrument contact occurred.

## Static dataflow

Addresses below are ELF virtual addresses before relocation.

| Boundary | Recovered behavior |
| --- | --- |
| `getLicenseKey`, `0x436c20` | Initializes both output strings empty, reads Key.data, and calls `decLicenseKey`. |
| `decLicenseKey`, `0x437e5c` | Requires byte count divisible by four; installs the supplied XXTEA key and accepts a zero return from stock decode. This is not authentication. |
| `0x436ec4`–`0x436f98` | Constructs an RString from the byte array, splits on semicolon, requires exactly two fields, assigns field zero to argument two and field one to argument one, then trims argument one. |
| `RString::trimmed`, `0x42eecc` | Removes trailing space (`0x20`) and NUL bytes until another byte is reached. It does not perform general whitespace trimming or hex decoding. |
| `verifyLicense`, `0x435e24`–`0x435f10` | Loads the right field into the license object's string at `+0x188`; requires both outputs nonempty; passes the cached right field to `verifyOption` as argument two. |
| Installer `0x433958`; `activeOpt`, `0x438a94`–`0x438aa8` | Ordinary installation reaches the same verifier with the cached string at `+0x188`. |
| `verifyOption`, `0x4373c8`–`0x4373fc` | Checks half the **option token string** length against 32 or 48, not the Key.data field length. The arithmetic alone does not require even input length. |
| `0x4375bc`–`0x4375d0` | Copies and decodes the **option token** using `API_SetStr2Hex`; the earlier low-nibble-first token evidence remains applicable. |
| `0x4375e0`–`0x4375f4` | Obtains the key string's raw data pointer through helper `0x235978`, supplies width 256, and calls `AES_set_decrypt_key`. No key-field hex conversion occurs along this dataflow. |
| `0x437608`–`0x437668` | Decrypts the token in 16-byte blocks with that schedule. |

The RByteArray constructor preserves an explicit byte count (`0x42ee74`), so
the acquired plaintext's two trailing NUL bytes must not be silently treated
as absent at construction. Stock trimming explains their removal from the
right field. The private fixture must preserve the entire original ciphertext.

The raw-pointer helper checks the libc++ representation flag: short strings
return object plus one; long strings return the pointer at object plus 16.
No transformation is performed there. AES setup consumes eight 32-bit input
words for width 256; its key schedule has 14 rounds.

Failure to open the file, empty input, failed decode or a field count other
than two leaves the initialized outputs empty. `verifyLicense` then skips
normal validation. The ordinary verifier has no independent minimum key-string
length check at its AES call, and it ignores AES setup's return value. That is
a consumer limitation, not permission to supply short or malformed fixtures.
AES itself returns -1 for null pointers and -2 for unsupported key widths.

Key loading can also change private state: `0x436fc0` compares stored length,
`0x436fd0` removes a mismatched record, and `0x4370d4` saves the original
ciphertext. A full successful save reaches `API_Save2Fram` at `0x4370f4`.
Thus even a guest baseline must declare its private-store model and capture
initialization deltas. We did not call these routines on the specimen.

## Original-instruction control

`tools/research/key-field-consumer-control.py` executes the pinned pointer
helper and AES setup in Unicorn 2.1.4. It supplies modeled libc++ objects,
stack/TLS and the stock AES import relocation, with bounded instruction/time
budgets and an execution allowlist. Original instructions are unchanged.
No constructors, Android services, installer or hardware routines execute.

Four synthetic fields passed: 32 bytes; the same prefix plus 98 `a` bytes;
the same prefix plus 98 `b` bytes; and a changed first byte. Every AES call
read exactly input offsets 0 through 31. The first three schedules matched;
changing the prefix changed the schedule. Short/long pointer controls and
the two error controls also passed. These are synthetic instruction controls,
not full-application or physical validation.

Private disassembly: `out/overnight/acquired-key-consumer-01`.
Control: `out/overnight/acquired-key-consumer-control-01`.
Both retain sealed hash indexes, and the latter retains tool source snapshots
and the execution trace. Acquired plaintext, unit identity and key bytes are
not included in source or this report.

## Fixture impact

The previous synthetic 32-character field was sufficient for this AES input
path. Its successful catalog results remain scoped to that synthetic
personality. They did not establish the acquired file's parsing, longer-string
storage, padding, exact identity, or private-record length behavior.

The next useful experiment is a fresh stock component guest using the exact
acquired Key.data and observed cached DNA, with an explicitly empty modeled
private store. First prove stock key parsing and baseline reload behavior;
do not infer the specimen's installed options from that empty store. Preserve
the complete long field and ciphertext rather than shortening the fixture
merely because AES consumes a prefix. Subsequent ordinary installation can
then be evaluated against a demonstrated specimen-derived baseline.
