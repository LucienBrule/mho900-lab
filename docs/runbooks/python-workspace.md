# Typed Python workspace

The typed tooling lives in seven uv workspace members:

- `packages/mho-evidence`: reusable typed evidence contracts and operations.
- `packages/mho-lab-cli`: Click adapters, application delegates and presentation.
- `packages/mho-transport`: offline packet and TCP transcript evidence.
- `packages/mho-capture`: ownership and bounded shutdown of a configured recorder child.
- `packages/mho-scpi`: typed read-only query observations and supplied-stream execution.
- `packages/mho-adb`: offline frame decoding and bounded stream-ready observations.
- `packages/mho-review`: sealed-input composition of capture, TCP and SCPI observations.

The root project is a development workspace, not an installed library.
Python 3.12 is the development baseline. `uv.lock` pins resolved dependencies;
`.python-version` selects the development minor version. Existing scripts under
`tools/bench/` and `tools/guest/` keep their original dependency and provenance
contracts. Installing this workspace neither runs those scripts nor contacts a
physical device.

From the repository root:

```sh
uv sync --locked --all-packages
uv run --locked mho-lab --help
uv run --locked mho-lab version
./tools/check-python.sh
mkdir -p out/tooling
./tools/check-python-packages.sh out/tooling/installed-packages-01
```

The gates run Ruff lint/format checks, strict mypy with Pydantic's plugin, an AST
policy check and pytest. The policy checker supplements type checking by rejecting
prohibited authored forms; it is not a complete proof of Python program semantics.
Rules apply to tests as well as production modules. See `packages/AGENTS.md`.

Choose a new evidence directory for each packaging run; it refuses an existing
output directory. Logs and built artifacts are retained there.
The packaging gate builds distributions and installs their wheels into a separate
environment, then exercises public imports and commands outside the checkout.
GitHub Actions runs both gates on Linux and macOS. A local pass is not evidence
that those remote jobs have completed; consult the individual workflow result.

Thin CLI endpoints should construct named requests and pass them to delegates.
Delegates call reusable library operations and retain typed outcomes. Render those
outcomes only at the presentation edge. Domain records use named immutable fields;
collections are parameterized, and sum types distinguish meaningful alternatives.
Pydantic validates external data rather than propagating dynamic dictionaries.

The implementation follows the official [uv workspace model](https://docs.astral.sh/uv/concepts/projects/workspaces/),
[Click command model](https://click.palletsprojects.com/en/stable/commands-and-groups/),
and [Pydantic union guidance](https://docs.pydantic.dev/latest/concepts/unions/).

The public surfaces have different evidence limits. Recorder ownership and supplied-
stream SCPI execution are library-only; the CLI operates on preserved local files.
This workspace setup is not a bench acquisition procedure.

| Package / operation | Entry point | What acceptance does not establish |
| --- | --- | --- |
| `mho-evidence`: seal / verify | Library and `evidence` CLI; [manifest contract](evidence-manifests.md) | Atomic snapshot or artifact origin |
| `mho-evidence`: inspect archive / compare inventory | Library and `archive` CLI; [archive contract](logical-archive-deltas.md) | Payload semantics or persistence across restart |
| `mho-transport`: reconstruct / assess capture | Library and `transport` CLI; [transcripts](offline-transcripts.md), [assessment](capture-evidence.md) | Peer delivery, device action or complete wire observation |
| `mho-capture`: start / stop / reap | Library only; [recorder lifecycle](recorder-lifecycle.md) | Packet completeness or descendant-process cleanup |
| `mho-scpi`: decode exchange | Library and `scpi inspect`; [SCPI contract](scpi-contract.md) | Authenticated origin or causal pairing |
| `mho-scpi`: execute | Library only, caller-supplied stream; [SCPI contract](scpi-contract.md) | Delivery or device execution; it does not connect an endpoint |
| `mho-adb`: decode / match open | Library and `adb` CLI; [ADB evidence](adb-evidence.md) | Shell-command execution, reboot or complete TCP capture |
| `mho-review`: review | Library and `review inspect`; [sealed review](sealed-offline-review.md) | Live process exit or authentic acquisition provenance |

Start with the [public synthetic walkthrough](synthetic-review-walkthrough.md)
to reproduce accepted and rejected composed reviews without private evidence.

The [owned-recorder composition control](owned-recorder-review.md) joins an actual
synthetic child lifecycle to sealed review, retaining abnormal exit and reported
loss as distinct failures. Shared rendering lives in a neutral presentation module;
command endpoints do not import sibling endpoints. A bounded AST regression check
covers authored imports between libraries, delegates and presentation. It does not
claim to analyze arbitrary runtime imports or Python execution.
