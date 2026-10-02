# RF acquisition: complete connection wait remains unsatisfied

The V5 A1 controller completed the new host-lifetime and connection-wait
question with a negative ADB connection result. It started a fresh verified
foreground server, observed local peer absence and issued one connect. The
client returned `failed to connect` after about ten seconds; its zero exit
code did not imply connection success and the exact response was rejected.
No metadata read, SCPI connection, ordinary setting, source command or RAW
record followed. The numerical comparison has no new measurement from this
attempt.

The raw evidence is sealed at
`out/rf/policy-comparison-A1-owned-20261002T042800Z.toml`, SHA-256
`3076c04212181e6e03004f3cf1584001ef45484d9198d0df646e456d5c71ea72`:
134 artifacts and 16,920,421 bytes. The recorder retained 63 frames, reported
a matching received count and zero kernel drops, and exited gracefully.
The controller terminated and reaped its exact owned server and proved the
process, owned sockets, complete dedicated listener and peer sockets absent
before removing the isolated address. Host configuration restoration passed.

The completed full wait is a different result from the earlier five-second
client timeout. It does not establish why the specimen supplied no accepted
ADB session or whether a device daemon, retained transport or application
condition is responsible. Repeating the same connect cannot resolve that
attribution by itself. The packet-level and lifetime review is separate from
the preparation readiness decision and must remain bound to this actual run.

The smallest independent diagnostic is one captured, documented read-only
SCPI `*IDN?` at the existing endpoint. A correct reply would establish that
stock Sparrow's command service is responsive while the ADB handshake remains
unsatisfied. It cannot replace the native epoch gate, establish a current
memory policy, or provide an RF record. No further ADB connect, extra reboot,
ADB setting change, option query or source command belongs to this diagnostic.
A current visual UI witness is also useful; the earlier camera image is not
current evidence, and inspecting the available camera application did not
provide a live bench view.

The bounded diagnostic is tracked by `TASK.rf.sparrow-liveness-preparation`,
`TASK.rf.sparrow-liveness-observation` and `TASK.rf.sparrow-liveness-decision`.
Its exact source and independent review must be committed and pushed before
execution. The original A1/B/A2 hypothesis, all five prerequisite-only stops
and the hard deadline remain unchanged.

The independent actual-run review is sealed at
`out/rf/A1-fifth-stop-independent-20261002T044000Z.toml`, SHA-256
`6ae481533e6eafbb8f913f1d52e571e95771e69a20d3943832b16f67e154b10f`:
24 artifacts and 112,023 bytes. It confirms connect elapsed
10.065821666 seconds, total helper elapsed 10.183961833 seconds, 29 TCP frames
and zero peer ADB application bytes. The peer acknowledged the same complete
CNXN request used by the preceding attempt. A host FIN and peer ACK occurred
during contained server termination before address removal. The typed lifetime
check validates the exact identity, SIGTERM, reap and all eleven original host
probes; no HOLD or teardown health fault occurred.

A bounded offline device-health assessment is sealed at
`out/rf/device-health-assessment-20261002T044000Z.toml`, SHA-256
`88b623bc3c94a56b343d1f5984694f40615c78c21a9c5d3354570d064a5898e8`.
It extracts the preserved boot-image adbd from matching independent raw
acquisition extents and identifies existing property-controlled startup and
restart behavior. That is implementation evidence, not a live daemon hash,
proof of a retained transport, or authorization to change a property.
The current application liveness question has greater information value than
further unchanged host connection attempts or speculative daemon surgery.
