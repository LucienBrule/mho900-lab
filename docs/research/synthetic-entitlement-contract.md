# Coherent synthetic entitlement fixture

Static recovery now supports a bounded ordinary-installer experiment using the unchanged specimen software
and wholly synthetic identity/key material. It does not establish the physical unit's entitlement state.
The original [candidate](../../experiments/specimen-entitlement/synthetic-fixture.toml) was rejected in both
arms because its producer omitted the stock wire-codec convention. The [trial report](synthetic-entitlement-trial.md)
preserves those results and the bounded correction. The corrected wire fixture subsequently passed ordinary FlexA installation, process reload and guest reboot;
see the same trial report for the exact persistence boundary and evidence. This contract includes the correction.

The active specimen Auklet hash is
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`. Addresses below refer to that library.
Real ART/JNI loading and construction of all 49 services are already validated. No further ADC work is needed
for this component boundary.

## Identity and key coherence

Use stock `SetModel(const RString&)` at `0x429d48` and `SetSerial(RString)` at `0x4244fc`, with real
stock-constructed RStrings. SetModel returns a model-record string pointer, not an integer status. Verify
MHO984 identity and bandwidth enum 17 rather than accepting any nonnull fallback. SetSerial's nontrivial
by-value argument is passed by pointer to a caller-owned temporary.

Supply one declared synthetic output at `Drv_System_GetFPGADNA(uint64_t&)`, then call unchanged
`ApiUtility_GetDNA()` and `ConvertDNA2Key(fileKeys)`. GetDNA returns void and updates `m_DNA`; key derivation
writes four words. License initialization copies those words into its own object, so derivation must precede
initialization. Use stock `CApiCore::getExecutor(36)` to resolve the complete License object rather than manually
adjusting its secondary base pointer.

Generate the synthetic `Key.data` using stock XXTEA primitives and the derived words. Its decrypted form has
two semicolon-separated fields; the right field supplies the 32-byte AES key. Do not reuse acquired Key.data,
vendor.bin or calibration material with this synthetic DNA. Stock semantic setters avoid an unnecessary
vendor-file reconstruction branch.

## Ordinary token and controls

The validator at `0x437384` accepts 32 or 48 bytes of encoded ciphertext, decrypts independent AES-256 blocks,
and parses six `#`-separated fields. The third field must contain the selected option's stock name. The first
characters of fields five and six select license type and time. Type 0 with time 0 follows the stock permanent
validity path. These are implementation-derived semantics, not vendor documentation or physical validation.

The candidate selects FlexA, type 5, avoiding bundle file deletion and the built-in validity special cases for
EMBD, COMP and AUTO. Produce the candidate ciphertext using unchanged `AES_set_encrypt_key` and `AES_encrypt`;
require stock encrypt/decrypt and XXTEA encode/decode roundtrips before relying on the generated inputs.
The token text is **low-nibble-first lowercase hex**, not conventional hex: byte `0x29` is represented as `92`.
Stock `API_SetStr2Hex` at `0x242fe8` decodes this convention; `API_SetHex2Str` at `0x242dd4` is its inverse.
Require a roundtrip through the actual wire decoder in addition to crypto roundtrips. Then submit
`MHO900-FlexA@<stock-wire-hex>` through the actual ordinary installer at `0x4332fc`.

The negative control differs only in the decrypted option-name field: `Wrong` instead of `FlexA`. It is a
well-formed token only after its stock wire decoding and consumer plaintext are verified. Use a clean baseline for
the positive case because rejected attempts can update private counters. Record activeOpt's actual result,
notifications, native validity queries and file deltas. Outer installer return zero is not acceptance evidence.

`syncError(24531)` is the successful-install notification, despite the function name. Observe it rather than
blanket-failing every call. Stock `JNI_SetErrCode` returns before Java presentation when `API_GetStarted()` is
false. Record the actual component lifecycle state and retain that stock behavior; do not force started state
or replace notification callbacks to obtain a result.

## Persistence contract

The private store is a naturally initialized 32-byte MemFile object at `0x151b3f0`; do not reconstruct or
zero-fill its C++ containers. New synthetic state can use stock `formatPrivateSetup()`. Reloads must not format.

`service * 64` yields logical record IDs, not physical FRAM byte offsets. Important records include 2337 for the
encrypted key backup, 2336 for the all-license counter, and 16192 for saved system time. The serialized private
blob occupies the physical FRAM region starting at `0x100`; stock saveSession requires its length below `0x700`.

Use stock `getSize`, `serialOut` and `serialIn` for the smallest first persistence experiment. The outer header
contains total length and its negation. Each record has a 20-byte header containing ID, negated ID, payload
length, negated length and CRC. Because serialIn has no capacity argument, accept only stock-generated,
hash-preserved blobs after checking every length and record boundary. Require exact serialization count and
byte-identical reload/reserialization before License initialization.

Persist those bytes to a disposable guest file with an explicit flush/fsync. This is **harness-directed private
persistence**. It does not prove automatic instrument FRAM persistence: `API_Save2Fram` queues service work,
and timer scheduling depends on started state. The stock `.lic` writer, decoder, validator and private-record
operations remain intact. A separate fuller model could retain stock CFram caching and replace its positional
read/write boundary, but full saveSession also consumes session/configuration state beyond the first question.

## Bounded runtime protocol

1. Fresh guest: real ART/API/factory, coherent synthetic identity and encrypted key file, empty stock private
   store, actual License initialization. Query the full active catalog and establish FlexA false.
2. Negative arm: call the ordinary installer with the wrong-name token. Require rejection, false query and no
   FlexA file. Preserve actual private deltas and close this arm before the positive experiment.
3. Independently clean positive arm: install the matching token. Require actual validation, success notification,
   true query and the stock-written `.lic` file. Preserve file/private-store hashes and serialize private state.
4. Fresh process on the same guest storage: restore the exact private serialization before License.init and
   query again without invoking the installer or regenerating key/license files.
5. Reboot the disposable guest, prove a changed boot identity, retain storage, and repeat the read/reload/query
   phase. Report separately whether acceptance, process persistence and reboot persistence passed.

Any failed prerequisite closes its actual question; do not change token fields or return values merely to make
it pass. No physical access is needed for this synthetic experiment. Exact unit parity still needs later,
separately authorized observation of the specimen's FPGA DNA and external FRAM contents. The captured SD image
and logical files do not establish those inputs. The D-capability experiment remains separate.
