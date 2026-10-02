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
