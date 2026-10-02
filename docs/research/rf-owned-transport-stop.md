# RF acquisition: connect timing and host transport lifetime

The fourth prerequisite-only A1 attempt passed its local removal gate, then
stopped during its single connect command. It issued no process metadata read,
SCPI connection, ordinary-setting change, source command or RAW acquisition.
The raw run is sealed at
`out/rf/policy-comparison-A1-deregistration-20261002T040000Z.toml`, SHA-256
`8ada4706c6bdb5a18f7fd2bd1a54551b964bd35e3eb548b7a9cfa2641071d0d8`:
82 artifacts and 16,902,752 bytes.

The exact already-absent disconnect outcome was followed by a fresh absence
inventory and one connect. The connect client timed out after 5.007422 seconds;
the helper lasted 5.076718 seconds of its twenty-second total allowance. The
45-frame capture contains 17 TCP frames. This time the host sent a complete
310-byte ADB CNXN message; the peer acknowledged its bytes but sent no ADB
application reply during the captured interval. No AUTH, peer CNXN or OPEN was
observed. This differs from the preceding immediate host closure without
application payload, but still establishes no accepted ADB session or epoch.

Independent review is sealed at
`out/rf/A1-fourth-stop-independent-20261002T041500Z.toml`, SHA-256
`4249853d196048858f057a14d694697f4705f2ce570706d1c79b55561cbd00f9`.
The recorder and lease helper exited zero and reported zero kernel drops.
The interface and host configuration restoration checks passed. Those checks
have a material limitation: they did not prove termination of the separate,
persistent host ADB server or its automatic reconnect behavior.

A subsequent host-only inspection found that exact owned server with a pending
reconnect socket sourced from the normal host interface, after removal of the
isolated address. The private peer route had consequently fallen back to the
normal default route. The process identity, socket and route evidence were
preserved, then only that known owned server was terminated and its absence
verified. No specimen command was issued by that intervention. This proves a
host process lifecycle defect; it does not prove delivery outside the segment
or external reachability. Evidence is sealed at
`out/rf/owned-server-route-stop-20261002T041400Z.toml`, SHA-256
`5a717cb2350b6467e9c2c4aead673b97d1afdf77ff0134aca077d2d8723bb483`.

Further physical work is stopped pending explicit ownership and termination
of the dedicated host server before isolated address removal, including error
paths. The separately bounded preparation also examines the current connect
implementation wait: the five-second client timeout must not be mistaken for
an exhausted twenty-second handshake observation. Earlier successful stock
captures provide a control for the exact CNXN bytes; protocol incompatibility
and the reason for peer silence remain separate hypotheses.

`TASK.rf.owned-transport-preparation` and `TASK.rf.owned-transport-decision`
track this host lifecycle and timing question. No specimen daemon restart,
root request, extra reboot or numerical relaxation is admitted by them. All
four stopped attempts remain immutable and no RF response claim follows.
