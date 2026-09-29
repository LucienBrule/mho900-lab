# Owned recorder lifecycle

`mho-capture` is a library for one explicitly configured foreground child process.
It does not select a network interface, discover a device, configure host networking
or choose acquisition arguments. Current validation uses synthetic local children
only. No generic recorder-launch CLI is provided.

`RecorderRequest` contains an absolute executable, immutable argument collection,
a new absolute evidence directory, an exact stdout/stderr readiness line, and
bounded startup and termination timeouts. The executable is invoked directly,
without a shell. Request construction validates the external configuration through
Pydantic. The directory must not already exist.

`start(request)` returns one of:

- `RecorderReady`: an ownership handle after observing the complete readiness line
  and validating the child signal witness while the child was still running.
- `RecorderStartRejected`: no owned child was started; partial setup evidence may
  remain and must not be overwritten casually.
- `RecorderStartFailed`: startup failed after a child existed. The terminal result
  and handle are retained, including when cleanup remains uncertain.

The readiness line is a caller-selected observation, not an independent guarantee
that capture has begun. Its operational meaning needs a recorder-specific profile.
The caller owns the handle and must call `stop` in its cleanup path. Calls on a
handle must be serialized. Only the direct child is managed; daemonization and
descendant ownership are outside this contract.

The installed private bootstrap clears the child's inherited signal mask and sets
SIGINT, SIGTERM and SIGHUP dispositions to default before exec. It preserves a
before/after witness. The caller's signal state is not changed. This addresses the
previous recorder shutdown failure without using `preexec_fn` or changing global
host policy. See Python's [signal-mask semantics](https://docs.python.org/3.12/library/signal.html#signal.pthread_sigmask).

`stop(handle)` requests SIGINT and waits for the configured graceful interval.
If necessary it escalates to SIGTERM and then SIGKILL, with a bounded wait at each
stage. Named results distinguish:

| Result | Meaning |
| --- | --- |
| `RecorderGraceful` | Requested stop, zero exit and reaping observed without escalation |
| `RecorderAbnormal` | Unexpected early exit or nonzero requested-stop exit |
| `RecorderEscalated` | Termination required escalation, even if the eventual exit code was zero |
| `RecorderCleanupUncertain` | Reaping or evidence preservation could not be confirmed |

A signal marked submitted records the send operation; it does not prove handler
execution or that the signal caused the observed exit. Repeated `stop` returns the
retained outcome. If that outcome is unreaped, `reap(handle)` performs a bounded
wait without sending new signals and appends separate reconciliation evidence.
Later reaping never retroactively promotes the failed operation to success.

Cancellation during startup triggers owned-child cleanup before re-raising the
original cancellation. If ownership remains unresolved, `RecorderOwnershipUncertain`
carries the handle and terminal evidence and chains the original exception. Do
not discard that handle or assume the child has stopped.

Exclusive evidence files preserve the launch configuration, stdout/stderr, signal
witness, readiness observation and terminal attempt. Witness reads reject special
files, links, oversized inputs and observable changes. The terminal file records
an **intended result**: a later publication or synchronization failure can still
make the returned API outcome uncertain. The file explicitly does not prove its
own publication completion. Preserve the caller's returned outcome separately;
do not infer success from that provisional file alone.

These bounds cover readiness polling and termination waits. They do not impose a
maximum recording duration or a storage quota after readiness. The caller must
bound its experiment and stop the recorder. Output contents may change while the
child is running, and the library does not claim an atomic snapshot.

Process lifecycle and [retained capture assessment](capture-evidence.md) answer
different questions. A graceful exit does not establish packet completeness;
matching frame counts do not establish process exit. A future acquisition procedure
must compose both and separately establish the intended interface and scope.
