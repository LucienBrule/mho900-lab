# mho-review

Reusable offline composition of a pinned evidence inventory, capture statistics,
selected TCP bytes and canonical identity/option-status SCPI observations.

`load_profile` validates a bounded versioned TOML role map. `review` accepts a
named `ReviewRequest` and returns `ReviewAccepted` or a stage-specific
`ReviewRejected`. Consumers retain the original bytes and component outcomes.
No Click, network connection, subprocess or physical interface is involved.

See the repository's `docs/runbooks/sealed-offline-review.md` for the schema,
limits, proof boundaries and delegated CLI usage.
