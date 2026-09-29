# Synthetic ordinary entitlement trial

The first disposable guest arm stopped before option installation. It established identity and crypto
prerequisites, then exposed a harness filesystem error. This is not an entitlement rejection.

## First prerequisite result

Run `out/specimen-entitlement/synthetic-negative-01` used unchanged specimen-identical APK and Auklet inputs,
real ART/JNI, the stock 49-service factory and only synthetic identity/key material. It ran from
2026-09-29 06:38:20 to 06:38:41 UTC.

Observed before the stop:

- The real model/serial setters produced the declared synthetic MHO984 identity; both bandwidth enums were 17.
- The modeled DNA response propagated through stock DNA-to-key conversion.
- Stock XXTEA and AES primitives completed exact encryption/decryption roundtrips.
- Stock private-store format produced an empty eight-byte stream.
- Actual License initialization returned and produced a 68-byte private stream.
- The harness serialized that stream and wrote its files, then directory open failed with `EINVAL` (22).

The ordinary installer was never called, and no before/after option catalog was reached. Positive acceptance,
process reload and guest reboot persistence remain untested. The failed directory operation is in the harness;
it must not be attributed to stock license behavior.

All 467 journal events matched delivered controller payloads, including the acknowledged failure. Guest
SELinux remained enforcing and the system server survived. The run used the existing loopback-only process
policy and made no physical contact.

| Artifact, relative to the run | SHA-256 |
| --- | --- |
| `phases/negative/guest-events.jsonl` | `42b19320782cbec503fb3ada617a26ffc5c11b0c36bb33be93dce95c4718be28` |
| `evidence-sha256.txt` | `88d702103d27d03a6bec1d6be5bc704d07f7289d1c8ab52c33413b0fd82944d2` |
| `result.toml` | `0bcff7afa202950c5f23fe2fc71e3358ada150b313f2298b2febc4c613be8be1` |

## Bounded continuation

Resolve the guest directory-open flag ABI and validate directory open/fsync/close before the next stock
factory call. Also retain the observed Frida representation of a native false boolean (`0`) in the host
verifier. Reattempt the unchanged negative and positive hypotheses only through successor task admission.
Persistence remains explicitly harness-directed stock serialization; this does not establish timer-driven
FRAM persistence on an instrument.

The correction is supported by the [Android 7.1.2 ARM64 UAPI header](https://github.com/aosp-mirror/platform_bionic/blob/android-7.1.2_r39/libc/kernel/uapi/asm-arm64/asm/fcntl.h):
`O_DIRECTORY` is octal `040000` (`0x4000`); the harness supplied `0x10000`, which is `O_DIRECT`.
This is architecture-specific implementation evidence, not a license or filesystem restriction.

## Wrong-name control passed

The corrected run `out/specimen-entitlement/synthetic-negative-02` completed from 06:41:39 to 06:42:00 UTC.
Directory open/fsync/close passed before the factory. All 555 journal events matched their delivered payloads;
the independent host verifier accepted the native observations and retained files.

Exactly one ordinary installer call submitted the synthetic wrong-name token. The stock validator returned
false, `activeOpt` and the original result notification reported `24527`, and FlexA remained false. No
`FlexA.lic` was created. The outer installer returned zero despite rejection.

The full 14-entry catalog was unchanged: EMBD, COMP and AUTO queried true through stock built-in policy;
all other entries queried false. Private state grew from 68 to 120 bytes: the key backup remained, and stock
added system-time record 16192 and option-specific record 2309. Global install-counter record 2336 remained
absent. A failed attempt therefore is not a no-op even when no license file is written.

| Artifact, relative to the corrected run | SHA-256 |
| --- | --- |
| `phases/negative/guest-events.jsonl` | `a877bb6a36131bd21e6dcb6b3019e5fe6bd63b672b5016d2453aedfe262fc734` |
| `evidence-sha256.txt` | `bad86646402a5e51f47c3ec54f32532c004fbf3a63b2331545fcf57648519e23` |
| `result.toml` | `8515f8fb81192809bcc7ed545b6f3771e6efd16f96684570ce8707ca30fc2908` |

This conclusion is committed before starting the independently clean positive arm. The next arm changes
only the declared candidate plaintext from the wrong option name to FlexA; stock validation remains intact.

## Positive candidate rejected

The independent fresh run `out/specimen-entitlement/synthetic-positive-01` ran from 06:42:48 to 06:43:13 UTC.
Its candidate changed the option-name field to FlexA while preserving the fixture's other fields and stock
program bytes. Directory persistence, identity, crypto roundtrips and the full catalog baseline all passed.
Exactly one ordinary installer call reached stock validation, which returned false; `activeOpt` and the
original notification again reported `24527`. FlexA stayed disabled and no license file appeared.

All 555 journal events were retained and matched delivered payloads. The before/after catalog stayed
unchanged. Process reload and reboot were correctly gated off because acceptance failed. This falsifies
the proposed positive fixture; it does not show that the ordinary installer cannot work in a guest.
The producer's own crypto roundtrip does not independently prove the consumer used the same key or grammar.

The paired runs establish rejection, not a successful install/persistence result. Preserve both fixtures
and trace the original consumer's key decode and token interpretation before choosing a revised input.
Do not replace validator returns or reinterpret outer return zero as acceptance.

| Artifact, relative to the positive run | SHA-256 |
| --- | --- |
| `phases/install/guest-events.jsonl` | `ecfd7a99ef544ea35b126ba84a5faa3c860111150293fd952f5711ee66c4803e` |
| `evidence-sha256.txt` | `69421db279fbd91e299597e8471099a390803717d22f843c180cf97c1442879a` |
| `result.toml` | `e52932588b916a310d4790dabbeea1b34eb45e5cedf183017f2bad45854f3a53` |

Independent review of the negative arm confirms the false result occurred inside the installer call,
not merely during baseline License initialization. Its option record `2309` changed from absent to
`70 08 00 01`: stock unpacking gives default runtime 2160, installation byte zero and rejected-attempt
count one. That count explains `24528 - 1 = 24527`. Record `2336`, the separate global install counter,
remained absent. No restart persistence was tested for the rejected arm.

## Wire-codec reconciliation

Static recovery of `API_SetStr2Hex` at ELF offset `0x242fe8` identifies a concrete mismatch: the first
character supplies the low nibble and the second character supplies the high nibble. The producer used
conventional high-nibble-first hex. Thus the stock consumer was predicted to decrypt nibble-swapped bytes,
even though the producer's own AES roundtrip passed. The ordinary key-file decode and AES-256 block
processing otherwise match the recovered implementation.

The admitted next batch will exercise both encodings through the real stock decoder before another
installation, then observe the actual consumer's decoded bytes, key and plaintext. A corrected wire
representation is a new fixture hypothesis; earlier rejection runs remain immutable.
