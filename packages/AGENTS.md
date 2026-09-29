# Typed Python workspace

These rules apply to new code under `packages/`. Historical experiment scripts
remain pinned research inputs and are not silently migrated into this workspace.

- Use the root uv workspace and committed lockfile. Keep reusable evidence code
  independent of the CLI project and of network or instrument access.
- Click endpoints parse arguments and render results. Application delegates
  coordinate typed requests and call library operations. Library code never
  calls Click, prints to a terminal or exits the process.
- Validate external data with Pydantic; forbid unknown fields and unintended
  coercion. Prefer immutable named dataclasses/models and discriminated unions.
- Annotate public and internal code, including tests. Do not author `Any`, legacy
  `Dict`/`Tuple` annotations, untyped containers, positional tuple records,
  unchecked casts, blanket type ignores or blanket lint suppressions.
- Homogeneous `tuple[Element, ...]` collections are allowed. Use named models for
  records with differently meaningful fields. An `object` boundary must be
  validated or narrowed before use; it is not an excuse for a dynamic domain model.
- Model success, rejection and uncertain side-effect outcomes distinctly. Do not
  call an already-published artifact absent merely because a later durability
  check failed. Never claim an atomic filesystem snapshot from repeated reads.
- Run `tools/check-python.sh` before completion. Preserve raw external evidence,
  keep private paths and identities out of fixtures, and use TOML for authored
  manifests/configuration. Do not contact the physical instrument from tests.
