# Physical APK-backed cached identity observation

The bounded observation succeeded on 2026-09-29. Stock Sparrow's existing cached DNA and file-key ranges
were read twice through the validated APK-backed reader: four positioned reads, 48 bytes total. Both
24-byte samples match. Unit values remain private; no key material is reproduced in this report.

## Authority and method

The operator authorized on-scope cached observation and subsequent autonomous bounded continuation.
The preceding standalone-file attempt stopped before staging; its failure remains separate evidence.
The [APK geometry and disposable guest control](apk-backed-cached-identity.md) passed before this task
was admitted and pushed. No physical entitlement, capability or calibration transition was authorized
or performed by this batch.

Fresh host baseline checks retained the isolated dock interface, separate default route, disabled IPv4
and IPv6 forwarding, inactive host DHCP client and no active NAT, Internet Sharing or bridge membership.
The earlier captured one-hour private lease remained valid. A fresh full packet capture preceded the
temporary host address. No gateway or DNS was supplied and no new lease ACK was needed during this run.

Existing ADB credentials reported the existing root identity. Fresh command line, PID/starttime, boot ID
and maps selected Sparrow and its mapped APK. The currently mapped APK was pulled and verified against
SHA-256 `6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b`; the embedded Auklet remains
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.

The frozen reader SHA-256 is
`4c1dd59391117311072a659514185867b69c524fe8e75302db7f086b9190316d`.
It was staged in a fresh temporary directory and roundtrip-verified before exactly one positive invocation.
The reader pinned the whole APK and embedded ELF, resolved the original file-backed data mappings and
opened one read-only process-memory descriptor. It performed requests of 8, 16, 8 and 16 bytes. No target
attachment, initialization call, target write, register access or fallback backend occurred.

The helper and its output are explicit temporary filesystem writes, distinct from read-only process
observation. Their exact staging path is retained privately. They remain on the device; this run did not
make a second connection to remove them. Stock APK, firmware, calibration, entitlements and capability
configuration were not modified by the procedure.

## Results and limits

The independent offline audit accepts all four raw process/map epochs, the repeated bytes, backing-file
metadata, both stock hashes, APK-relative address geometry and fixed read counts. Fresh file identity and
physical read permission are now observed facts. Repeated samples are not an atomic snapshot and do not
establish all initialized private/FRAM state or physical option availability.

Physical `getenforce` reported `Disabled` both before and after observation. That is an observed specimen
baseline; the procedure did not change it. The disposable guest control separately remained `Enforcing`.
Do not transfer either environment's policy claim to the other.

Capture ran from approximately 12:24:48 to 12:24:58 UTC. Helper readiness was recorded at 12:24:54 and
observation completion at 12:24:57. The capture contains 42,067 complete frames, matching both recorded
packet counters, with zero reported kernel drops. Offline replay accepts the retained frames under the
recorded classifier: bounded ADB/file transfer, local ARP and previously characterized host traffic.
This verifies conformity to that classifier, not independent completeness of every possible network rule.

ADB disconnected, the temporary host address was removed, the lease responder and recorder stopped, and
post-run isolation checks passed. Network preference/interface property lists match baseline bytes.
The privileged host shell was closed. The previous lease remains valid until its recorded expiry.

## Decision boundary

The next useful question is offline: does original stock DNA-to-key derivation reproduce the physical
cached file keys, and can those keys coherently decode the previously acquired `Key.data`? Admit that as
its own hypothesis. Do not equate a coherent key record with entitlement installation, private FRAM state,
reboot durability or feature operation. No further physical action follows automatically from this result.

## Evidence

Private run: `out/physical/mho984-apk-cached-identity-20260929T122420Z`.
The raw samples, addresses, process identities, packet payloads and unit-specific artifacts remain local.

| Artifact | SHA-256 |
| --- | --- |
| `live/capture.pcap` | `9eddbc23e00588fdece837557bf45587f60dd85d4d0fce7002edb9158b2dc164` |
| `capture-validation.toml` | `05f720f0d73a01b6f8595eb0dee30a366b9c477f3e17ca33426d3b812c50c6a0` |
| `observation-validation.toml` | `94f0cecb3fd1c6640595863da05f43c6a0f5195fb1890cc30be559b825b5a94a` |
| `reader/observation/manifest.toml` | `5f79a8b86ab81f28a1332d0779a191006b58eb076079192f6b64fb9f7c9a5a96` |
| `control-inputs.toml` | `fc0172a205180c72e003fee44e7a132878fb351f695e86fa1d59eccd21b12b7b` |
| `evidence-sha256.txt` | `eeedb402dc7625c9fb056cfa2985ea83fb93d918e5c03a42d5e2151c1d694ab7` |
