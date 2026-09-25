# Decision: separate private observation from filesystem reconstruction

Run02 validates the complete legacy suite for the unchanged build11 observer.
Its remaining failure is the root-filesystem setup command. Private loader
controls generate their own records and require no stock calibration files, so
making setup a prerequisite prevented an independent question from being tested.

Run the 14 new private controls in a minimal harness, carrying forward the
byte-identical observer's complete legacy evidence. Preserve their actual
inherited native access sequence and require complete raw captures and independent
verification. No native or modeled-register change is selected.

Separately recover enough of the pinned guest mount utility and init sequence to
freeze a justified setup candidate. Capture live mount flags, skip remounting if
already writable, and otherwise attempt only a predeclared guest-scoped form.
Stop on failure. A successful fixture must preserve exact stock bytes, absent
paths, permissions and final mount state. This does not prove stock UID access.

Both harness paths must collect final health and command statuses even when their
helper fails. Run02's pre-failure samples and successful teardown do not replace
those observations. No stock run is admitted until both independent results
support it.

The [three-task batch](../../.agents/plans/calibration-loader-independent.yaml)
implements these two questions and their combined decision gate. Commit and push
each guest conclusion before starting the next experiment. The native candidate,
stock artifacts, and no-physical-instrument scope remain unchanged.
