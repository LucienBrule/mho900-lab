# RF acquisition: asynchronous local transport question

The explicit reconnect controller reached neither an online ADB transport nor
its initial process-epoch read. It stopped at the unchanged 20-second readiness
deadline, before SCPI, ordinary-setting normalization, source control or RAW
acquisition. The reconnect-only question has a negative result; the controller
is not modified or repeated in place.

The raw run is sealed at
`out/rf/policy-comparison-A1-transport-20261002T035700Z.toml`, SHA-256
`fe8526cca9a704ed31698e1a80d56a2cd5d88163aa2896cc8ddbabc9d3504169`:
354 artifacts and 17,021,214 bytes. The recorder retained 74 packets, reported
a matching received count and zero kernel drops, and exited gracefully. The
temporary host address was removed and isolation restored.

The controller issued one exact-peer disconnect, one connect and 69 local-server
status queries. The disconnect returned success, but the connect reported
`already connected`. Early status queries retained the old offline transport;
later queries reported it absent. On the wire, the scope answered the TCP
handshake, then the host immediately sent FIN without ADB application payload.
These observations distinguish a responsive TCP endpoint from a usable ADB
session. They support an asynchronous local-removal hypothesis but do not prove
the cause of the host closure or establish a fresh scope process epoch.

The next bounded question is whether requiring exact-peer absence after the
single disconnect, before issuing the single connect, resolves that ordering
problem. Both the removal and online checks must fit within the original total
20-second deadline. Unknown states, duplicate peer rows, other command errors
and expiration remain stop conditions. The existing metadata read is still
single and occurs only after both local readiness gates; no specimen daemon
restart, root request or reboot is introduced.

A separate host-only control characterized disconnecting an already absent
transport with the current pinned CLI. The isolated interface had no host IPv4
address and the local server listed no devices. One local disconnect returned
exit 1, empty stdout and the exact expected no-such-device stderr. This did not
request a specimen connection. The control is sealed at
`out/rf/adb-absent-disconnect-control-20261002T035600Z.toml`, SHA-256
`e05f712e2fc5f7cfc0ef444080b070899ecb4a10733cb36a4ffc0479807147ca`.
Only that exact outcome, followed by fresh unambiguous absence, may be treated
as an already-removed local transport; other errors remain failures.

Preparation and evaluation are tracked as
`TASK.rf.transport-deregistration-preparation` and
`TASK.rf.transport-deregistration-decision`. The previous attempts, tools and
receipts remain immutable. A separately reviewed, committed and pushed GO is
required before fresh execution. No waveform has yet been collected by these
three prerequisite attempts, and no RF-response claim is made.

The independent stopped-run review is sealed at
`out/rf/A1-third-stop-independent-20261002T040000Z.toml`, SHA-256
`6cc8e8cf427dbdf6438cf4c2d5cb9db5a5af3a4131b89156af90c4dea8ea74d0`.
It confirms the chronology, absence of application payload and acquisition,
graceful termination, zero reported kernel drops and host restoration.

The separate V4 preparation passed independent review at
`out/rf/transport-deregistration-independent-20261002T040500Z.toml`, SHA-256
`6b0322c2da03e717f0d62035ac208cb37d679b8b9b7e557987e670a90ba9ff05`.
Its completed-arm verifier preparation is sealed at
`out/rf/policy-arm-verification-v4-evidence-20261002T040100Z.toml`, SHA-256
`8ba347e54f2d647307be29ac0ba2fa81fe490dee22c2c960fa183cc6efc4494c`;
59 copied-source controls passed. Both successful disconnect and the exact
already-absent outcome require a fresh absence observation before connecting.
The normalizer, RF guards, epoch read and numerical contract remain unchanged.

The decision is GO for one fresh bounded A1 attempt. This is preparation
readiness, not evidence that the transport hypothesis succeeds or that a
waveform has been acquired. The three earlier stops remain separate results.
