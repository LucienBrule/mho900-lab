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
See [offline evidence manifests](evidence-manifests.md) for the first reusable
operation and its limits, and [offline transcripts](offline-transcripts.md) for
the transport profile. This workspace setup is not a bench acquisition procedure.
The [capture assessment](capture-evidence.md) separates retained frame/count
agreement from process exit and traffic completeness.
The [recorder lifecycle](recorder-lifecycle.md) provides explicit child ownership
and failure outcomes for future configured acquisition procedures.

The [SCPI contract](scpi-contract.md) composes canonical query semantics with explicit
stream ownership; its CLI only interprets preserved files.

The [sealed offline review](sealed-offline-review.md) binds the component results to
a pinned inventory and explicit role assertions.

The [logical archive tools](logical-archive-deltas.md) inventory pinned uncompressed
archives and compare content without extraction or payload disclosure.

The [offline ADB evidence profile](adb-evidence.md) decodes retained bytes without
running ADB or requesting any device action.

Start with the [public synthetic walkthrough](synthetic-review-walkthrough.md)
to reproduce accepted and rejected composed reviews without private evidence.
