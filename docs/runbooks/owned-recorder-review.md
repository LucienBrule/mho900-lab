# Owned recorder to sealed review: a synthetic composition control

The public components are exercised together by `owned_recorder_review` in the
installed-distribution consumer, `packages/mho-lab-cli/tests/installed_smoke.py`.
The source gate runs the same composition function; the distribution gate copies
the full consumer outside the checkout and runs against rebuilt installed wheels. This is a control for component
composition, not a configurable acquisition procedure or instrument command.

The child is a fixed Python process. It copies the public manufactured capture and
transcripts into its new evidence directory, installs a SIGINT handler, and emits
an explicit readiness marker. When stopped, it writes manufactured final packet
counters and exits with the selected test status. It opens no network connection
and invokes no recorder executable. Child lifetime is observed; packet and counter
content remains synthetic.

The consumer performs these operations in order:

1. Start through `mho_capture.start` and require the named ready outcome.
2. Request bounded stop, reconcile reaping, and inspect the actual terminal outcome.
3. For a graceful result, seal the complete evidence directory only after lifecycle
   operations have finished writing their artifacts.
4. Review the new manifest against its returned pin and an explicit profile naming
   the child's copied capture, raw transcript files and final stderr counters.
5. Preserve lifecycle artifacts, manifests, profile and a separate summary.

| Control | Observed child outcome | Downstream result |
| --- | --- | --- |
| Exit zero, zero reported drops | graceful and reaped | sealed review accepted |
| Exit seven, otherwise matching counters | abnormal and reaped | no seal or review is attempted |
| Exit zero, one reported drop | graceful and reaped | sealed review rejects at capture assessment |

A graceful child is therefore insufficient for content acceptance, and plausible
counter text cannot turn an abnormal child exit into success. These are separate
facts. The offline review report still marks process-exit proof false because that
review, by itself, does not inspect a live ownership handle. The enclosing control
records its actual lifecycle observation separately.

Run the normal source and installed gates described in the
[workspace runbook](python-workspace.md). Installed evidence includes
`owned-review.toml`, the three retained child directories, and external manifests
for the two graceful cases. Existing output directories are not reused. If a
control fails, the packaging gate retains its scratch environment and logs.

Future acquisition procedures must explicitly own startup, stop and cleanup, and
must preserve uncertain cleanup as a failure outcome. They must also establish
real capture provenance, interface configuration, drop-reporting support and any
instrument-specific authorization. This synthetic control establishes none of
those bench facts and grants no permission to contact an instrument.
