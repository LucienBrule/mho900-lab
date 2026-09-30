# Typed SCPI observations and supplied streams

`mho-scpi` provides a deliberately small read-only profile: `*IDN?` and
`:SYSTem:OPTion:STATus?` for the eleven selectors preserved in the existing
[option-status research](../research/physical-option-status.md). It does not expose
an arbitrary command string, an installer, endpoint discovery or a connection factory.

The vendor programming guide establishes identity and option-status semantics.
The [identity accession](../research/physical-stage-two-b1-identity.md) and preserved
query transcripts establish what one specimen returned. Synthetic fixtures test
this library; they do not establish instrument behavior beyond those observations.

## Offline interpretation

```sh
uv run --locked mho-lab scpi inspect \
  --requests out/example/requests.bin --replies out/example/replies.bin
```

The input files contain concatenated complete request and reply lines, respectively.
The profile requires canonical query spelling, LF or CRLF termination and exact
one-to-one line counts. It rejects abbreviations, compound commands, whitespace
normalization, unknown selectors, non-printable ASCII, and option replies other
than exactly `0` or `1`. Rejection means outside this profile, not necessarily
invalid SCPI in general. Defaults bound each line to 4096 bytes, the exchange to
128 queries and the combined streams to 1 MiB.

Identity is four opaque, nonempty strings. A returned `00.01.00` stays that string;
it is not expanded into a firmware suffix. The CLI hides all four identity fields
unless `--show-identity` is explicit. Structural errors do not echo private payloads
or paths. Output includes stream hashes, query count and typed observations as TOML.
Raw requests and responses remain available in library outcomes, including rejection.

The delegate reads regular files with explicit bounds, rejects final symlinks and
observable changes, and calls the codec. It creates no network connection. The
codec is independent of Click, filesystem paths and process exit codes.

## Supplied-stream execution

A library caller constructs `IdentityQuery` or `OptionStatusQuery` alternatives in
a `SessionRequest`, then calls `execute(stream, request)`. `ByteStream` has bounded
`write` and `read` operations; `SocketStream` adapts an already-connected socket
provided by its owner. It never creates, resolves, connects, discovers or closes
an endpoint. There is intentionally no active SCPI CLI command.

The caller must exclusively own a clean stream with no stale queued replies.
Execution sends each query once, completes short writes, then reads one bounded
reply without prefetching. A single monotonic deadline covers the whole plan.
A backend must honor its operation timeout; Python cannot force an arbitrary
noncooperating implementation to return. Exceptions stop the plan rather than
silently retrying a query.

`SessionComplete` contains exact per-query request/reply evidence.
`SessionIncomplete` retains completed observations and the current submitted-byte
count, response prefix, any unknown I/O progress, and timeout-restoration failure.
The socket adapter restores the previous timeout after each operation. A restoration
failure retains progress that the socket operation already returned.

Local write progress is not proof of peer delivery or device execution. A valid
reply does not prove causal attribution to the latest query. Completion also does
not establish stream exhaustion: surplus bytes remain unread. These limits matter
when composing an eventual bench procedure; it must own endpoint selection,
authorization, capture, connection lifetime, and reconciliation separately.

Controls use in-memory streams and owned Unix socket pairs. Installed-wheel checks
exercise the codec, executor and redacted CLI outside the source checkout. None of
these controls contact a physical instrument.

Public query and limit models are revalidated from their primitive fields at use.
This includes instances created through unchecked construction or modified outside
Pydantic's normal frozen-model contract. Encoding accepts the exact supported query
classes and an actual `OptionSelector`; malformed inputs raise a constant
`ValueError`. Direct reply/exchange decoding returns explicit invalid-input or
invalid-limits results, with private input records omitted from rejection reprs.
Wrong raw-byte API types raise a constant `TypeError`.

The executor reconstructs the entire immutable plan and bounded finite limits
before its first stream operation. An invalid later query rejects the whole plan:
it does not send an earlier valid prefix. The validated copy is used throughout
execution. This boundary protects the documented grammar and resource caps; it
does not claim to isolate arbitrary Python code executing in the same interpreter.
