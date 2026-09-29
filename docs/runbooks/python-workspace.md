# Typed Python workspace

The new offline tooling lives in two uv workspace members:

- `packages/mho-evidence`: reusable typed evidence contracts and operations.
- `packages/mho-lab-cli`: Click adapters, application delegates and presentation.

The root project is a development workspace, not a third installed library.
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
```

The gates run Ruff lint/format checks, strict mypy with Pydantic's plugin, an AST
policy check and pytest. The policy checker supplements type checking by rejecting
prohibited authored forms; it is not a complete proof of Python program semantics.
Rules apply to tests as well as production modules. See `packages/AGENTS.md`.

Thin CLI endpoints should construct named requests and pass them to delegates.
Delegates call reusable library operations and retain typed outcomes. Render those
outcomes only at the presentation edge. Domain records use named immutable fields;
collections are parameterized, and sum types distinguish meaningful alternatives.
Pydantic validates external data rather than propagating dynamic dictionaries.

The implementation follows the official [uv workspace model](https://docs.astral.sh/uv/concepts/projects/workspaces/),
[Click command model](https://click.palletsprojects.com/en/stable/commands-and-groups/),
and [Pydantic union guidance](https://docs.pydantic.dev/latest/concepts/unions/).
New evidence operations will be documented with their actual guarantees and
failure behavior as they are implemented; this workspace setup is not a bench
acquisition procedure.
