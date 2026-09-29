# Owned recorder lifecycle

This package starts one explicitly requested foreground executable as an owned
child, retains separate stdout and stderr files, waits for a complete readiness
line, and requests a bounded shutdown. It does not select a capture interface,
construct recorder arguments, launch a shell, interpret packet statistics, or
contact an instrument. Its tests use synthetic local processes only.

`start(RecorderRequest(...))` returns `RecorderReady` with an ownership handle,
`RecorderStartRejected` if no child was created, or `RecorderStartFailed` with the
terminal cleanup evidence. `stop(handle)` returns one of `RecorderGraceful`,
`RecorderAbnormal`, `RecorderEscalated`, or `RecorderCleanupUncertain`. Repeated
stop calls return the same retained result. Calls on each handle must be serialized
by one owner; no other component may reap or signal that child.

Startup failure retains the handle. A cancellation during startup performs cleanup
before re-raising the original exception when reaped; if ownership remains unresolved,
`RecorderOwnershipUncertain` exposes the handle and terminal evidence. `reap(handle)`
can reconcile a prior unreaped result with one further bounded wait and no signals.
It preserves the original terminal witness and appends a reconciliation witness.
Later reaping does not promote the earlier failed or uncertain lifecycle to success.

The request requires an absolute executable and evidence directory, a homogeneous
argument tuple, an exact readiness line and stream, and explicit bounded waits.
The evidence directory must not already exist. Output files are created exclusively.
The installed private bootstrap runs with Python isolated mode, clears its inherited
signal mask, resets INT/TERM/HUP dispositions, preserves its signal witness, and
executes the requested executable. It does not use `preexec_fn` or change the
parent process's signal configuration. The before witness describes Python bootstrap
entry state, not a claim that Python startup preserved every disposition unchanged.

A complete readiness line plus validated signal witness establishes startup. Stop
requests SIGINT, waits, then escalates to SIGTERM and SIGKILL only as required by
the supplied deadlines. Zero exit before a requested stop is unexpected, not graceful.
Startup timeout remains failure even if cleanup exits zero. Any escalation remains
non-success. An unreaped child keeps its PID and unknown return code in an uncertain
outcome; the library never claims that child was removed. An uncertain result is
retained rather than automatically retrying operations later.
Signal attempts marked `submitted` mean the process API returned without a reported
error while no exit code was available. They do not prove that a handler processed
the signal or that the signal caused the subsequent exit.

Only the direct foreground child is owned. Programs that daemonize, spawn output-
inheriting workers, or require process-group cleanup are outside this profile.
The caller must stop a ready handle, including on its own error paths. Output growth
after readiness is not capped by this library. Startup readiness scanning is limited
to 1 MiB of its selected output stream. Timeout bounds apply to child waits, not to
an operating system filesystem call that stalls.

Raw outputs, launch details, readiness and signal witnesses remain in the requested
directory, including failed runs. Terminal publication and output fsync failures
produce uncertainty; a file written before a later durability error is preserved.
The returned typed outcome is authoritative about completion of publication, not
the mere presence of a terminal file; that file labels its result as intended and
does not claim its own publication completed. These checks do not provide an atomic snapshot
or protect against arbitrary concurrent path replacement. A graceful child exit
alone does not prove valid packet counts, zero packet loss, or complete wire capture.
Those are independent retained-evidence checks.
