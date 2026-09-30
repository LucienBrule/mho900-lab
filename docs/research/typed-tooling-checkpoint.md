# Typed tooling checkpoint

2026-09-29. This is offline tooling work after physical enablement. It does not
extend the physical result or claim RF characterization.

The first workspace boundary now has two consumers: a reusable `mho-evidence`
library and delegated Click commands in `mho-lab`. Versioned TOML manifests describe
an exact recursive regular-file inventory. Pydantic validates external values;
named immutable requests and outcome alternatives carry the library contract.
The [manifest runbook](../runbooks/evidence-manifests.md) states the precise scope.

The workspace gates pass 85 tests, Ruff lint and formatting, strict mypy, and the
authored typing-policy checker. Independent review found real failure modes:
rebound prohibited imports and blanket tool directives escaped the policy checker;
publication could initially report success after staged bytes or the output-parent
name changed. Regression controls now cover those cases. Failures after publication
retain an explicit uncertain outcome rather than claiming no output was created.
These checks are not a proof that all concurrent filesystem mutation is detectable.

An external new manifest was created for a preserved physical identity-display
run. All 84 original seal members matched their original hashes and the new
inventory. The new exact inventory contains 86 files and 17,161,570 bytes; its scope
also includes the old seal and an existing file excluded from that legacy seal.
An independent standard-library hash pass checked every new member. The original
seal remained byte-identical. No physical interface was used.

| Artifact | SHA-256 |
| --- | --- |
| Original identity-display seal | `a2cd302541632c520bd18a34740a092df448adb584aa5a2e37f666323fc3ccba` |
| New external inventory | `b4e1cda332af59daf17a87495a43b564a974f19e5dc94a08030ee8f081b8ef0c` |

Private comparison outputs remain under `out/tooling/evidence-manifest-01/`.
The pinned D-persistence verifier was separately rerun against preserved files,
writing its result outside the original run, and still returned accepted. Its
source hash remains `1a6bba615401ad3bb935e19fad3b13c603b86a3ef4222c77bc7b434a0f76e827`.
Experiment-specific acceptance remains the responsibility of those verifiers;
the new inventory tool only checks retained content.

The next useful boundaries are installed-package verification and offline TCP
transcript reconstruction. Editable development imports can hide packaging errors.
The old verifier chain also repeats packet parsing and byte-sequence recovery,
making an independently tested transport-evidence library valuable. Recorder
ownership and active read-only transport can wait until those offline contracts
are stable. A general bench orchestrator is still premature.

## Installed packages and offline transport

The successor batch adds `mho-transport` as a third workspace member. Its bounded
classic-pcap profile recovers one explicit IPv4 TCP connection with named request
and reply bytes. The CLI reports TOML counts and hashes without payload disclosure.
Its [profile and limits](../runbooks/offline-transcripts.md) distinguish captured
content from delivery, application execution and recorder-drop statistics.

All 124 workspace tests and typed quality gates pass. Independent review exercised
11 additional sequence-boundary controls, including wrap, bytes before the SYN
origin or after FIN, conflicting SYN payload, repeated FIN and reversed capture
order. The supported profile has no remaining blocking finding from that review.

The new parser reproduced 333 request bytes and 72 reply bytes exactly from the
preserved 12-query identity-display run: 61 total frames, 45 selected TCP frames
and zero repeated payload bytes. Capture SHA-256:
`c61c6bb3f11546cbd8c7685aaa90d73b786c09088d0d4a2ddf41e67b55bd6921`.
The comparison reads local files only; raw payloads and endpoint configuration
remain private. Evidence is under `out/tooling/offline-tcp-01/`.

The installed-package gate rebuilt all three wheels from generated source
distributions, installed locked runtime dependencies into an external noneditable
environment, and exercised public imports, typing markers and both CLI/library
paths under Python isolated mode. Evidence and transport positive and negative
controls passed with `UV_OFFLINE=1` using cached tooling. Build constraints also
pin the backend and its dependencies through the workspace lock. Outputs are under
`out/tooling/installed-packages-02/`.

A Linux/macOS GitHub Actions workflow defines these gates using pinned action
commits and uv 0.6.17. Its first Linux run passed; macOS stopped during interpreter
setup because setup-python does not distribute Python 3.12.13 for macOS. The
corrected matrix uses 3.12.13 on Linux and the available 3.12.10 binary on macOS;
local macOS checks use 3.12.13. The corrected [workflow run](https://github.com/LucienBrule/mho900-lab/actions/runs/36645549162) passed both quality and installed-distribution gates on both platforms.

## Capture finalization and owned processes

The next batch separates classic-pcap structural inspection, reported terminal
counts and process ownership. The TCP decoder and generic capture inspector now
share one record reader. `capture assess` accepts the preserved 61-frame run with
matching final counts, and rejects the earlier four-frame Stage Two A capture
because terminal counts are missing. The four retained frames remain structurally
valid evidence; missing statistics are not promoted to a zero-drop observation.
Private comparisons and the shared-reader transcript regression are under
`out/tooling/capture-assessment-01/`.

`mho-capture` owns one configured foreground child. Synthetic controls demonstrate
child-only signal normalization, exact-line readiness, graceful reaping, abnormal
exit, bounded escalation and retained uncertainty. Independent review found a
startup-cancellation leak; the same probe now confirms reaping before cancellation
is re-raised. The API retains a handle when ownership remains uncertain and supports
later bounded reap-only reconciliation. Provisional terminal files explicitly do
not authenticate their own publication completion.

The full workspace passes 188 tests and typed gates. Review added nine actual-child
controls and thirteen capture/count controls. Four installed distributions rebuilt
from source archives pass the offline packaging gate, including execution of the
installed private child bootstrap and a synthetic recorder's graceful stop.
Evidence is under `out/tooling/installed-packages-03/`. No capture interface was
opened, no physical scope was contacted and no old verifier was edited.

The [recorder contract](../runbooks/recorder-lifecycle.md) is intentionally narrow:
direct-child ownership, serialized handle use, bounded waits and no automatic
recording-duration or disk-quota policy. Neither a graceful exit nor matching
reported counts independently proves complete on-wire acquisition. Those remain
separate facts for a future explicit acquisition procedure to compose.

## Typed identity and option observations

The SCPI member models identity and eleven ordinary option-status queries as named
alternatives. Preserved twelve-query evidence decodes into one opaque identity,
ten enabled statuses and one disabled status, without contacting the specimen or
changing its original seal. Raw requests and responses remain byte-identical;
the default CLI output omits identity fields. The comparison is under
`out/tooling/scpi-composition-01/`.

The stream executor accepts an explicitly supplied, exclusively owned transport.
It provides a whole-plan deadline, bounded replies, partial progress, and no query
retry. It creates no connections. Independent Unix-socket controls confirm timeout
restoration and preservation of unread surplus; these also demonstrate why a valid
reply cannot establish stream exhaustion or causal attribution on a dirty stream.

Five distributions rebuilt from source archives pass the offline installed-package
gate, including actual codec/executor calls and the default-redacted CLI. Evidence
is under `out/tooling/installed-packages-06/`. Strict quality gates and 277 tests
passed after the final review additions. The [SCPI contract](../runbooks/scpi-contract.md)
states the grammar and ownership limits independently of the research notes.

The [SCPI workflow run](https://github.com/LucienBrule/mho900-lab/actions/runs/36647210465)
passed both platform gates for `23da684`. The next bounded step binds these
separate consumers to a caller-pinned exact inventory and explicit role map.
This addresses accidental mixing of valid files; it cannot authenticate a
physical origin merely because a bundle was sealed.

## Sealed composition

The composed review binds each input role to a caller-pinned exact inventory,
checks capture/count agreement, reconstructs one explicitly selected TCP stream,
and compares its bytes exactly with ordered raw query/reply members before SCPI
interpretation. Complete inventory verification runs before and after, including
unselected files. Independent controls mutate an unselected file after decoding;
that still rejects at final inventory verification.

The preserved identity run passes as an 86-member sealed inventory containing a
61-frame capture and twelve exact query pairs. Its original seal remains unchanged.
Comparison and redacted output are under `out/tooling/sealed-review-01/`.
The [review contract](../runbooks/sealed-offline-review.md) records the important
limit: a deliberately mixed bundle can be internally consistent, so membership
cannot authenticate a common physical origin.

Optional verification limits now bound manifest bytes, enumerated files and
directories, depth, individual bytes and aggregate bytes. Actual growth controls
reject oversized data during reading, not only during initial size inspection.
The old unbounded verification default remains available; composed review always
supplies explicit limits. Blocking filesystem calls still have no deadline claim.

All 327 workspace tests and strict gates pass. Six distributions rebuilt from
source archives pass the isolated installed-package check, including accepted
review, default identity redaction and rejection of a subsequently mixed input.
Artifacts are under `out/tooling/installed-packages-08/`. No old verifier or
sealed physical evidence was rewritten.

The [sealed-review workflow](https://github.com/LucienBrule/mho900-lab/actions/runs/36647858444)
passed on Linux and macOS for `ec90e06`. The next offline batch inventories
preserved uncompressed logical archives and compares file-content deltas without
extracting them. Existing ordinary-option verifiers repeat that operation, making
it a concrete reuse target rather than a new bench controller.

## Logical archive content deltas

The evidence library now inventories the narrow uncompressed USTAR/GNU-USTAR
profile present in the logical acquisitions. It checks headers, canonical names,
member extents, zero padding and complete termination; unsupported forms reject
instead of falling back to an extractor. Named additions, removals and modifications
compare regular-file path/size/digest records without rename inference.

The pinned first ordinary-option archives reproduce one added `data/FlexA.lic`
with all 22 previous files unchanged. The original seal and legacy ordinary-install
verifier hash remain unchanged. No file was extracted and no physical interface
was contacted. Comparison artifacts are under `out/tooling/archive-delta-01/`.
The [archive contract](../runbooks/logical-archive-deltas.md) distinguishes content
consistency from option behavior, metadata restoration and persistence.

Independent review found a public typed-value edge: equal digest strings in
different valid Pydantic subclasses were incorrectly reported as modified. The
comparison now uses primitive digest values, with a retained regression control.
All 397 tests and strict gates pass. The installed-distribution gate under
`out/tooling/installed-packages-10/` exercises archive inventory/delta through
both the library and delegated CLI outside the checkout.

The [archive workflow](https://github.com/LucienBrule/mho900-lab/actions/runs/36648692153)
passed on both platforms for `593de9c`. The next proposed offline component is
ADB frame and stream-ready evidence, keeping acknowledgment separate from completed
instrument behavior. Its [reference profile](../runbooks/adb-evidence.md) records
the protocol text's checksum terminology discrepancy before implementation.

## Offline ADB stream observations

The seventh workspace member decodes six cleartext frame variants under an
explicit additive-checksum-required profile. It retains bounded failure offsets
and accepted prefixes. Matching selects one OPEN by exact payload digest and
requires consistent server stream identifiers, with identifier reuse rejected.
CLI reports expose only hashes, counts and numeric identifiers.

The preserved reboot-delivery comparison accepts 481 client and 497 server frames
and finds one matching OKAY. The server direction lacks a FIN witness, so the
result is limited to retained directional prefixes. Neither a complete connection
nor a completed reboot follows from it. The original capture remains unchanged;
derivation, comparison and redacted CLI reports are separate under
`out/tooling/adb-evidence-01/`.

Independent reviews exercised malformed headers, truncated prefixes, forged typed
records and identifier ambiguity. No blocking issue remains. All 479 tests,
formatting, lint, strict typing and authored-type policy checks pass. Seven source
archives rebuilt into installed wheels pass public library/CLI controls outside
the checkout under `out/tooling/installed-packages-11/`. No device was contacted.

The [ADB workflow](https://github.com/LucienBrule/mho900-lab/actions/runs/36649631782)
passed on Linux and macOS for `22659a4`. The next batch makes composed review
reproducible from public synthetic inputs; it adds no acquisition interface.

## SCPI complete-plan correction

Independent review found that unchecked Pydantic instances could bypass the
nominal read-only selector and configured timeout/query/response caps. An in-memory
reproducer demonstrated the issue without opening an endpoint. Its eight original
cases and source pins remain preserved under `out/overnight/scpi-boundary-review/`.

The codec now reconstructs supported query and limit values. The executor validates
and freezes the entire bounded plan before any stream operation, including later
queries. Independent reruns of all eight cases show zero reads and writes; the
canonical twelve-query grammar remains unchanged. Twenty-four regression controls
cover malformed records and direct codec entrypoints. All 503 workspace tests and
strict gates pass. The isolated installed-wheel check also proves zero submitted
bytes for an invalid plan (`out/tooling/installed-packages-12/`). This changes no
pinned legacy verifier or physical procedure.

The [SCPI preflight workflow](https://github.com/LucienBrule/mho900-lab/actions/runs/36650317177)
passed on Linux and macOS for `656393c`.

## Public synthetic walkthrough

A contributor can now reproduce the composed review from tracked public files.
The fixture contains six manufactured Ethernet/IPv4/TCP records, two query/reply
pairs and authored counter text. Its provenance explicitly denies instrument or
recorder origin. No new production abstraction or acquisition command was added.

The [walkthrough](../runbooks/synthetic-review-walkthrough.md) preserves acceptance,
post-seal inventory rejection and separately resealed transcript disagreement.
Independent review recomputed all IP/TCP checksums and sequence extents, checked
manifest/profile pins, and confirmed that repeating an existing destination changes
no output bytes. The exact script also runs against installed wheels outside the
checkout. All 505 tests and strict gates pass; seven rebuilt distributions pass
`out/tooling/installed-packages-13/`. Relevant runbook and fixture changes now trigger
CI. The independent adversarial packet builders remain separate.

The [public walkthrough workflow](https://github.com/LucienBrule/mho900-lab/actions/runs/36650519725)
passed on Linux and macOS for `8da9c56`. The next bounded controls connect an owned
synthetic child lifecycle to sealed review, and remove shared presentation helpers
from command modules. These demonstrate composition without adding a bench runner.

## Validated artifact boundaries and lifecycle composition

Tiny-file probes found that unchecked model copies could disable declared archive,
verification and capture limits, or substitute a broader downstream bound for the
review limit. Those originals remain under `out/overnight/remaining-boundary-review/`.
Affected entrypoints now revalidate their own complete models before artifact reads,
including nested review roles and digests. Deliberate `VerifyRequest.limits=None`
remains available; malformed fields inside an explicit bounded model reject.
Manifest diagnostics no longer echo invalid private field values.

Recorder startup now reconstructs a concrete request and readiness model before
creating a directory or launching a child. Malformed requests have a constant
rejection reason and no validated directory. The ownership handle retains an
independent validated snapshot; ordinary caller mutation or reassignment cannot
change readiness or cleanup budgets. Forty-eight new controls cover all deadline
fields, malformed nested records and snapshot independence; all 26 previous
lifecycle controls remain passing.

Independent artifact review exercised 147 controls, including early reader-seam
rejection and deliberate unbounded verification. The preserved private identity
review still accepts twelve queries from 61 frames, and the logical archive delta
still reports one addition with 22 unchanged files. New comparison outputs are
separate under `out/tooling/final-boundary-comparison-01/`; originals are unchanged.

The [owned-recorder control](../runbooks/owned-recorder-review.md) joins a fixed
synthetic child's observed lifecycle to sealing and composed review. A graceful
child with matching manufactured data accepts. Exit seven stops before sealing;
one reported drop rejects at assessment. Independent review also injected a
subsequent sealing failure and confirmed the child was already reaped. Lifecycle
observations remain separate from synthetic packet/counter provenance.

Shared TOML/observation rendering now lives outside command modules. Authored import
controls preserve library, delegate and presentation direction. String controls
round-trip through TOML, while lone surrogates reject without echoing content.
All 608 workspace tests, formatting, lint, strict typing and policy checks pass.
Seven source archives rebuilt into installed wheels pass the complete public,
malformed-boundary and owned-child controls under `out/tooling/installed-packages-15/`.
No physical interface was contacted and no pinned legacy verifier was changed.

The [boundary/composition workflow](https://github.com/LucienBrule/mho900-lab/actions/runs/36651397027)
passed on Linux and macOS for `4b5439e`. A final construction-only check identified
a separate recorder serialization mismatch: accepted DEL-bearing arguments and
readiness markers were emitted literally into TOML. A bounded successor will make
those supported strings round-trip through the child/bootstrap records.

## Recorder string fidelity

The DEL reproducer is now closed. Supported Unicode scalar values retain their
exact values through launch arguments, readiness markers and diagnostic strings.
TOML serialization escapes DEL while preserving supplementary Unicode without
JSON surrogate-pair escapes. Request validation and child ownership are unchanged.

Seven new source controls cover scalar/array encodings, an actual child's DEL-
bearing arguments and readiness, and immutable terminal/reconciliation records.
The installed consumer separately injects a synthetic signal-submission failure,
retains the unreaped uncertainty, restores normal signaling, and confirms later
reaping without rewriting the first terminal witness. All children are local
synthetic controls; no physical interface is opened.

The 615-test source gate and seven rebuilt installed distributions pass. Evidence
is retained under `out/tooling/recorder-toml-01/`,
`out/tooling/recorder-toml-independent-01/` and
`out/tooling/installed-packages-17/`. The workspace runbook now maps each public
surface to its CLI availability and strongest unestablished claim.
