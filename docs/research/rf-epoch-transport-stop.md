# RF acquisition: offline metadata transport stop

The separately prepared impedance-aware A1 attempt stopped before its SCPI
session. The single fresh process-epoch read failed with `adb: device offline`.
It did not select the 50-ohm input, command the source or acquire a waveform.
This is a transport-readiness stop, not an accepted A1 arm or an RF result.

The run is preserved at
`out/rf/policy-comparison-A1-impedance-20261002T034000Z`, with native manifest
SHA-256 `d29bbcb71b6a3246d5232369581851490583bcde6c0abc9b839af499a06b126d`:
70 artifacts and 16,879,846 bytes. The recorder retained 13 packets, reported a
matching received count and zero kernel drops, and exited gracefully. The
lease helper exited successfully; the owned temporary host address was removed
and the isolation checks passed. The local ADB server's device list afterward
also reported the isolated peer as offline. That host-side status does not
establish the cause or prove a device reboot.

Independent review is sealed at
`out/rf/A1-epoch-stop-independent-20261002T034500Z.toml`, SHA-256
`8e2b8d4e48471e8c73a81e5539160645c19957c0596bf4552880f2fc097ed322`.
Its reconstruction found five TCP frames on the ADB endpoint, zero application
payload and no frames on the SCPI endpoint. The legacy live label `SCPI TCP`
covered both permitted management ports and is not evidence of a SCPI query.
The empty failed epoch output establishes no new process, policy or RF witness.

The existing controller requested a connection and immediately attempted its
single metadata read. A successful connection command is insufficient evidence
that the local transport is online. The proposed remedy disconnects only the
exact isolated peer from the owned local server once, connects that peer once,
then checks the local server's device list within a bounded deadline. Only an
unambiguous `device` state permits the original single metadata read. Timeout,
ambiguity or connection failure stops the attempt. No shell-read retry, device
daemon restart, root request or specimen configuration change is introduced.

`TASK.rf.epoch-transport-preparation` and
`TASK.rf.epoch-transport-decision` bound the offline preparation and evaluation.
The previous impedance remedy remains separate and unchanged. Every negative
attempt and controller is retained. A fresh execution requires independently
reviewed concrete bindings and a committed and pushed GO. All waveform slots,
source commands, epoch checks, restoration rules and numerical criteria remain
governed by the original frozen comparison.

The bounded transport decision is GO. Producer preparation is sealed with
SHA-256 `fa850e64bc7b7baf67a1985534e4bc90e7ad08b2937d7f922af8b230bdd12026`,
and independent concrete readiness review with SHA-256
`9d51fccfae35091c4d84780325e3f94238be122f1bfef8b8f64954c4034797ea`.
Seven producer and ten independent host-only controls passed. The matching
completed-arm verifier passed 47 controls, including complete synthetic
25-record witnesses for both original impedance states; its preparation seal is
`29147ba0fc3199182fc540ed832187ee9e638244a7de3c37e6584b4678438961`.

The fresh actual controller is prepared at
`out/rf/policy-comparison-A1-transport-20261002T035700Z`, with control manifest
SHA-256 `a1e300325925180b704cb6601be814b014fc4d9588ddfeacf663933c0a55b557`.
The stable run label is an identity; actual preparation timestamps are recorded
separately. The independently reviewed adapter replaces only the initial
connection step and retains all 11 existing callback bodies, the original
single epoch read, ordinary-setting remedy and measurement code. Acquisition
tasking explicitly depends on this decision. Fresh runtime checks still apply;
preparation and local transport readiness establish no physical RF result.
