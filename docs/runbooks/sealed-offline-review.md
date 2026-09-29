# Sealed offline review

`mho-review` binds [capture assessment](capture-evidence.md), selected
[TCP reconstruction](offline-transcripts.md) and [SCPI decoding](scpi-contract.md)
to one caller-pinned [exact inventory](evidence-manifests.md). This is an offline
consistency review, not an acquisition or instrument-management procedure.

The input roles are explicit TOML. Addresses in this example are documentation
fixtures; supply the tuple already established by the retained evidence.

```toml
schema_version = "mho-review.profile/1"
capture = "capture.pcap"
statistics = "capture.stderr"

[client]
address = "192.0.2.1"
port = 41000

[server]
address = "192.0.2.2"
port = 5555

[[transcripts]]
request = "queries/00-request.bin"
reply = "queries/00-response.bin"
```

Every role must name a different canonical member of the inventory. Transcript
pairs are ordered, with exactly one complete request and one complete response
line per pair. Add another `[[transcripts]]` table for each subsequent query.
The profile permits one to 128 pairs and an explicit IPv4 tuple; it performs no
name resolution or endpoint discovery. Unknown fields and coercions are rejected.
The profile is a caller assertion about how the files relate, not an authenticated
statement of their origin.

```sh
uv run --locked mho-lab review inspect \
  --root out/example-run \
  --manifest out/example-run.toml \
  --expected-manifest-sha256 "$EXPECTED_MANIFEST_SHA256" \
  --profile out/example-profile.toml
```

Obtain the expected digest from the previously preserved seal, not by trusting
whatever file currently occupies the manifest path. Keep the profile and rendered
report outside the sealed tree. The CLI prints TOML to standard output and exits
zero only on acceptance. Rejection exits one with a structural stage/code/message;
command syntax errors use Click's normal exit two. No output file is silently
created or replaced. Identity strings and endpoint addresses are omitted from the
report by default; `--show-identity` deliberately includes all four identity fields.

The review proceeds through these independent checks:

1. Read and validate a bounded manifest matching the caller's expected SHA-256.
2. Verify the complete inventory, including files not used by the selected roles.
3. Bind capture inspection and terminal statistics to their sealed digest/size;
   require matching retained-frame and captured-packet counts with no reported drops.
4. Reconstruct the explicit TCP connection and bind that consumer to the same capture.
5. Read each bounded transcript member and match concatenated request/reply bytes
   exactly to the reconstructed stream before interpreting canonical SCPI.
6. Verify the complete inventory again against the same pin.

Acceptance retains typed component results. Rejection identifies the stage that
failed and does not promote earlier partial successes to an accepted review.
The CLI delegates to this reusable library; neither layer launches a process,
opens a network connection, or touches an instrument interface.

Default review limits are 64 KiB of profile input, 4 MiB of manifest input, 4096
inventory entries, 128 MiB of aggregate artifact data, 64 MiB per artifact, depth
32, and 100,000 captured frames. Statistics are capped at 1 MiB; each raw query or
reply at 4096 bytes; combined SCPI bytes at 1 MiB. Library callers can provide a
validated `ReviewLimits` within the supported bounds. Limits constrain bytes,
entries and depth, not the duration of blocking filesystem operations.

An accepted report establishes content consistency with the supplied pin and role
assertions. It does not establish an atomic snapshot, physical origin, graceful
recorder exit, complete wire acquisition, platform support for drop reporting,
peer delivery, reply causality or device execution. In particular, sealing a
purposefully mixed bundle cannot make those files originate in the same run.
Do not interpret a provisional recorder `terminal.toml` as proof of publication
completion; recorder lifetime remains a separately established fact.
