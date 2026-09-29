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
