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
