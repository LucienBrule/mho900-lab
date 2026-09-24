# Repository tasking contract

Start with `./taskctl doctor`, `./taskctl context`, and `./taskctl frontier`.
Windows: use `./taskctl.bat` or `./taskctl.ps1`. Add `--format json` for
machine results. The launcher targets its own repository even from another
working directory; `--repo PATH` overrides it explicitly.

Tasks are atomic executable transitions. Prerequisites determine readiness.
Roadmaps are durable named lines of advance; epics are capability scopes.
Their memberships are independent and may be empty or overlapping.
Read `.agents/config.toml` and `.agents/policy.toml` for protocol/profile.

Use `taskctl seed --file PLAN --expect-revision REVISION` to admit an explicit
plan through normal validation. `taskctl show ID` reports the current task
contract. `taskctl verify ID --receipt FILE` validates supplied evidence;
it never runs a command or promotes an assertion into an independent proof.
`taskctl close ID --receipt FILE --expect-revision REVISION` binds closure
to that contract and the inspected ledger revision. Receipts are immutable.

Lifecycle and currency are independent. Use `taskctl status` and `affected`
to find stale work, `history ID` for immutable revisions, `revise ID --file
RECORD --expect-revision REVISION` for contract edits, and `reconcile ID
--plan` to inspect the exact inputs a review must address. Submit explicit
actor assertions with rationale and evidence through `reconcile --file`.
Never hand-edit HEAD or immutable history to clear an affected task.

Read commands do not write the project. Writes are bounded to tasking state.
No command implicitly commits, stages, merges, deploys, or contacts services.
Unknown required capabilities block execution. Never infer dependencies from
roadmap order or claim epic completion just because its tasks are closed.
Use `taskctl recover` for an interrupted tasking transaction; inspect any
reported external-edit conflict instead of deleting recovery data.

The `.taskctl/toolchain.lock` pins the exact release and platform digest.
Commit the generated launchers and state (preserve the POSIX executable bit).
Set `TASKCTL_OFFLINE=1` to require cached operation. Private GitHub release
acquisition accepts `TASKCTL_GITHUB_TOKEN` or `GH_TOKEN` with contents read.
Native alpha contracts are not v1; upgrades never silently rewrite records.
