# Offline Android debug-bridge evidence

This component is being developed for retained transport evidence. It does not
run an ADB executable, create a connection, authenticate a client, select an
endpoint or request an instrument action.

## Reference provenance and checksum profile

The reference is AOSP `platform/system/core`, tag `android-7.1.2_r39`, commit
`da6c753a2bbc2b2e5a8809250a38f3fc2019d365`:

| Reference file | SHA-256 |
| --- | --- |
| `adb/protocol.txt` | `46bd59db2d39747e21bedfce5a9fce3e90e53c0a18e118ab4d12f8ce8f7c9873` |
| `adb/adb.cpp` | `1db544c670b47def44146768ba3df828c2c5cd231087b74642db539db95cc0d9` |
| `adb/adb.h` | `1c4109b5167d2263cd2adce60ab37e4cfa573b86a2f98fe70a7ff4c669457c84` |
| `adb/transport.cpp` | `e74dd8b93e4b5653bfb960d145ace51887905bef9355991e16c5ff8a8efc647a` |

The [protocol text](https://android.googlesource.com/platform/system/core/+/da6c753a2bbc2b2e5a8809250a38f3fc2019d365/adb/protocol.txt)
describes six little-endian 32-bit header words followed by a declared payload.
Its historical checksum label says CRC32. The pinned
[implementation](https://android.googlesource.com/platform/system/core/+/da6c753a2bbc2b2e5a8809250a38f3fc2019d365/adb/transport.cpp)
in `send_packet` and `check_data` instead sums unsigned payload bytes modulo
2^32 and requires equality with the checksum word. The first decoder profile
follows that implementation-derived rule. A zero checksum is accepted only when
it is the actual additive sum; it is not treated as an omission escape.

This is an explicit reference profile, not proof that the specimen runs these
exact AOSP source bytes. Protocol version negotiation, checksum-omission profiles
and encrypted transports require separate evidence. A captured stream outside
this profile must remain a recorded rejection rather than silently weakening it.

The reference [OPEN/READY implementation](https://android.googlesource.com/platform/system/core/+/da6c753a2bbc2b2e5a8809250a38f3fc2019d365/adb/adb.cpp)
associates an OPEN local identifier with a READY reply's remote identifier. READY
is encoded as `OKAY` on the wire. Such a matching reply concerns the logical
stream. It does not prove a requested reboot finished, a shell operation succeeded,
or any later instrument state became durable. Two separately retained directional
byte streams also do not establish a total ordering of events between directions.

## Public operations

`mho_adb.decode` accepts retained bytes and explicit `DecodeLimits`. Its result
is `DecodeAccepted` or `DecodeRejected`; failures retain the valid frame prefix
and failing byte offset. The six frame variants have named fields, immutable raw
wire/payload bytes, and hidden payload representations. Default bounds are 64 MiB
per direction, 100,000 frames and 1 MiB per payload. Oversized inputs are rejected
before hashing. Wrong Python API types raise a constant, payload-free `TypeError`.

The decoder checks declared extents, command complement, additive checksum and
command-specific identifiers/body requirements. It does not validate a connection
state machine or negotiate protocol versions. A successfully decoded byte string
can still be an incomplete retained prefix of a larger connection.

`match_open(MatchOpenRequest(client, server, expected_payload_sha256))` returns
`StreamReadyMatched`, `StreamReadyMissing` or `StreamReadyRejected`. The selector
is the digest of the exact OPEN payload, including any NUL terminator. It requires
one selected OPEN and an unreused client identifier. Server OKAY frames must map
that identifier to one consistent server identifier; repeated compatible replies
are retained. Ambiguous reuse or disagreement is rejected. The matcher revalidates
its supplied decoded records against their bounded raw bytes.

The command adapter accepts only pinned local files:

```sh
uv run --locked mho-lab adb inspect retained-client.bin --expected-sha256 "$CLIENT_SHA256"
uv run --locked mho-lab adb match-open \
  --client retained-client.bin --client-sha256 "$CLIENT_SHA256" \
  --server retained-server.bin --server-sha256 "$SERVER_SHA256" \
  --payload-sha256 "$OPEN_PAYLOAD_SHA256"
```

Reports contain hashes, counts, numeric stream identifiers and explicit limitations.
They omit banners, service payloads and local input paths. A payload digest is a
selector, not encryption or proof that its content is secret. Missing and rejected
matches exit nonzero. No command creates a connection or invokes an ADB executable.

## Retained-evidence comparison

An offline comparison of a previously sealed acquisition decoded 481 client and
497 server frames under this profile. One selected OPEN had one matching OKAY.
The directional bytes were derived as consistent captured prefixes, not as a
complete TCP transcript: the server direction lacked a FIN witness. Therefore the
result establishes only the matching protocol observation in the retained data.
It does not establish total ordering between directions, TCP delivery, successful
reboot, later persistence, or physical origin from bytes alone.
