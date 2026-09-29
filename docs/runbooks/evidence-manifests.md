# Offline evidence manifests

`mho-evidence` records the exact recursive inventory of regular files beneath an
explicit directory. It hashes file contents with SHA-256, records byte counts and
canonical relative names, and writes a versioned TOML manifest outside that tree.
It does not acquire instrument data or interpret the meaning of the files.

```sh
uv run --locked mho-lab evidence seal out/example-run --output out/example-run.toml
uv run --locked mho-lab evidence verify out/example-run --manifest out/example-run.toml
```

The output parent must already exist. An existing destination is never replaced.
There are no implicit exclusions: additions, removals, size changes and content
changes cause verification to fail. Empty directories do not become artifact
records; sealing an entirely empty file inventory requires `--allow-empty`.
The manifest records that choice explicitly. Put manifests outside the evidence
root, including when describing an older sealed run.

An example with one empty file is:

```toml
schema_version = "mho-evidence.manifest/1"
inventory = "recursive-regular-files"
empty_allowed = false

[[artifacts]]
path = "capture.log"
sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
size_bytes = 0
```

Records are sorted by path and must be unique. Paths are relative slash-separated
names without empty, dot or parent components, backslashes, colons or control
characters. Digests use lowercase hexadecimal. Unknown schema versions, unknown
fields and incorrectly typed fields are rejected. The writer emits deterministic
bytes for identical inventories; timestamps, host paths and operator identities
are deliberately absent. Such metadata belongs in a separately scoped run record.

The reusable library accepts named `SealRequest` and `VerifyRequest` values.
`seal` returns `SealCreated`, `SealRejected` or `SealPublishedUncertain`; `verify`
returns `VerificationAccepted` or `VerificationRejected`. Callers must handle
each alternative. Domain values and requests do not depend on Click.

| CLI exit | Meaning |
| --- | --- |
| 0 | Manifest created, or inventory verified |
| 1 | Operation rejected; inspect the diagnostic |
| 2 | Invalid command-line usage |
| 3 | Publication occurred, but integrity, path identity or durability could not be confirmed |

For exit 3, preserve and inspect the named output before deciding what to do next.
The reported hash describes the intended encoded manifest; it is not a claim
that the currently named output contains those bytes. It is not a successful seal,
and retrying must not overwrite it. A temporary file
can remain after a cleanup failure; its presence is not evidence of publication.

The implementation rejects symlinks in traversed paths and special files in the
evidence inventory. It opens directory-relative file descriptors without following
links, compares file identity and metadata around reads, rescans the inventory,
and checks that named roots still refer to the opened directories. Publication
uses an exclusive temporary file, file synchronization, a non-replacing hard
link and directory synchronization.

These controls detect observable races; they do **not** create an atomic filesystem
snapshot or prove that a source stayed unchanged at every instant. Work on quiescent
preserved data. Filesystem read-access metadata may change. Ownership, permissions,
extended attributes, sparse layout, empty directories and hard-link relationships
are outside this content-inventory contract. A matching digest proves consistency
with the supplied manifest, not authenticity or instrument provenance. Preserve
the manifest and its reported SHA-256 through an independent trusted channel.

Only filesystems and platforms supporting the required descriptor, no-follow,
hard-link and synchronization operations are supported. Unsupported operations
fail rather than silently weakening publication behavior. This tool does not
replace existing experiment-specific verifiers or their immutable receipts.
