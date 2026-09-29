# Recorder shutdown: inherited blocked signals

A host-only loopback differential reproduced the recorder shutdown failure and
verified a process-local correction. No specimen interface was opened, no scope
traffic was generated, and no host network or security policy was changed.

The privileged authorization-shell launch path passed a blocked signal mask into
the recorder child, including SIGINT and SIGTERM. The earlier supervisor reset
signal dispositions but did not clear this mask. Those are independent process
properties: restoring a handler does not unblock delivery.

The inherited-mask control reset the same dispositions and retained the mask.
It captured all three known local UDP payloads but did not exit on SIGINT within
three seconds, requiring SIGKILL and yielding no final statistics. Clearing the
child's mask immediately before exec resolved that failure through the same
privileged launch path.

| Control | Termination | Exit | Stored frames | Received by filter | Kernel drops |
|---|---|---:|---:|---:|---:|
| Inherited mask | SIGINT timed out; SIGKILL cleanup | -9 | 3 | unavailable | unavailable |
| Cleared mask, repetition 1 | SIGINT, graceful | 0 | 3 | 3 | 0 |
| Cleared mask, repetition 2 | SIGTERM, graceful | 0 | 3 | 5 | 0 |
| Cleared mask, repetition 3 | SIGINT, graceful | 0 | 3 | 3 | 0 |

Each successful exit occurred in less than four milliseconds after its stop
signal. Each capture retained all three independently received loopback payloads
in complete pcap records. The differing filter counter is preserved as reported;
it is not rewritten to match the stored-frame count. These are low-volume
termination controls, not throughput or physical-Ethernet loss measurements.

The result establishes the failure mechanism in a matched current launch-path
control. It supports the explanation for the prior physical runs; their process
masks were not recorded, and their missing drop statistics cannot be recovered
or replaced by these successful controls.

## Reusable correction and control

[recorder-exec.py](../../tools/bench/recorder-exec.py) records the inherited mask,
resets INT/TERM/HUP dispositions, clears the owned child's mask and execs the
specified recorder. It changes no other process or host policy. Its `inherit`
mode exists only for the differential control. Physical captures must use the
default `normalize` mode and preserve the signal-state receipt.

[test-recorder-shutdown.py](../../tools/bench/test-recorder-shutdown.py) is restricted
to local IPv4 sockets and the loopback capture interface. It accepts a private
evidence directory, configurable tcpdump path and capture-file owner. Execute it
through the same privileged authorization-shell path used for the recorder. It
preserves the expected negative control followed by three required positive
controls. Python's standard library provides subprocess signal control and owned
test sockets; this is host evidence tooling, not instrument implementation.

Future physical acquisition must preserve final packet/drop counters, require a
graceful recorder exit and verify complete records. Recorder failure remains a
stop condition; forced termination must not be treated as successful acquisition.
No physical capture was performed to verify this correction.

The [control result manifest](../../experiments/physical-first-contact/recorder-control-result.toml)
binds private evidence and tested source. The next admitted task prepares only an
identity-query proposal; it does not authorize a scope connection.
