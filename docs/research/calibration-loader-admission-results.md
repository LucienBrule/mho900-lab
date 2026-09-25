# Admission repaired; filesystem setup is the next unresolved precondition

The second private run passed all 76 legacy runtime controls and all 30 malformed
inputs using the unchanged observer. The explicit private tail profile also
passed eight host checks: it admits the new private binary, preserves baseline
acceptance, and rejects mismatched, unknown, stock and unsupported uses.

The run then stopped before the first new loader control. The fixture command
`mount -o remount,rw /` returned `mount: 'rootfs'->'/': No such device`.
Because subsequent operations were joined with `&&`, no directory creation or
guest asset push followed. Local asset inspection and source hashes passed.
The 14 loader controls, full-buffer captures and altered-loader-evidence checks
remain unexecuted.

Static ramdisk evidence shows an explicit read-only rootfs remount during boot.
The failed command does not establish current mount flags or that a different
explicit mount form would work: live `/proc/mounts` was not captured. This is an
environment precondition, not a native observer or hardware-model result.

All 675 indexed artifacts verified. The 85 recorded `system_server` samples were
1045 and enforcement was enabled through fixture entry. The failed helper did
not record post-failure PID, enforcement, process or package samples. Successful
emulator teardown and absent dedicated listeners do not fill that health-evidence
gap. Stock artifacts remain unchanged; no stock application ran.

Separate the independent questions in the next batch. Private loader programs
generate their own buffers and need no `/rigol` fixture. Run their 14 controls
without making filesystem preparation a prerequisite, carrying forward the
byte-identical observer's complete legacy pass. Evaluate rootfs state and fixture
installation separately, with final health samples captured even on failure.
Require both results before admitting any stock loader continuation.

See the [frozen inputs](../../experiments/calibration-loaders/admission-inputs.toml)
and [result manifest](../../experiments/calibration-loaders/run02-results.toml).
