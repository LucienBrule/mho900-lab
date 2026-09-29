# Specimen logical acquisition: active application lineage

The specimen's active Sparrow APK, packaged ARM64 Auklet library, and active Web Control APK are byte-identical
by SHA-256 to the official `.26` inputs already studied. This identifies the application bytes; it does not establish
that every partition, FPGA image, calibration asset, or running mapped page matches the update package.

The active packages are under `/data/app`. Copies under `/rigol/app` and `/system/app` differ. In particular, both
inactive Sparrow copies contain the same different Auklet library. Their exact release lineage remains unresolved;
file location and version strings alone are insufficient. None of these differing copies matched the pinned stock
or community APK/library inputs compared in this run.

| Active artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Sparrow APK | 38166679 | `6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b` |
| Packaged Auklet | 12453760 | `4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e` |
| Web Control APK | 3438109 | `7b37be5ee0b63857949f7ed7ea940b7593ab50058a3a4c608b8bda00f88d2736` |

## Acquisition and validation

Private run `out/physical/mho984-logical-acquisition-20260929T031955Z` preserves five streams: `/rigol`, active
application directories, system application copies, system native/configuration files, and boot configuration files.
All commands returned zero. Every regular tar member was read offline to its declared size; all acquired APK ZIP CRCs
passed. Source tar headers retain member names, modes, ownership, timestamps, and link information.

The boot-configuration stream contains a 39-byte `removing leading '/' from member names` message after its two
zero end blocks. The original stream is preserved verbatim. Its 34 tar members parse successfully; it is not claimed
to be a canonical tar stream with no trailing data. The other four archives have no nonzero trailing text.

The separately authorized single `adb root` attempt returned `restarting adbd as root`; subsequent `id` confirmed
UID 0. No reboot, remount, filesystem freeze, device-side archive staging, firmware, entitlement, or capability
change was performed. A previous preparation run stopped before root because its traffic classifier rejected known
scope IPv6 neighbor traffic. That negative run and its fresh DHCP ACK remain separate evidence. Offline replay
validated the corrected classifier before this acquisition.

The recorder exited normally: 540987 captured, 540987 received by filter, zero kernel drops. Full Ethernet frames
were retained without a BPF capture filter. The temporary host address was removed, forwarding remained disabled,
and network preferences plus hardware-interface mapping plists matched their pre-run bytes. The single-client DHCP
responder stopped after acquisition; the acknowledged private lease remained valid. Known host-local discovery
background was retained under the operator's accepted observation conditions.

## Integrity and limits

The private hash manifest is `sealed/SHA256SUMS`, relative to the run directory, SHA-256:
`2f6877974acceef7b343b0f32b4704275ec916530d6bf7775d7d51486cba34a0`.
It pins archives, pcap, host snapshots, command/error logs, extracted application manifests, and source comparisons.
Original archives and capture were made read-only on the host. Unit-specific calibration, key/license content,
identifiers, and proprietary binaries remain outside tracked source.

These are reads of live mounted filesystems, not an atomic snapshot. No ACL/xattr completeness is claimed. Raw
storage acquisition remains a separate task. Exact active application hashes let prior static Auklet conclusions
transfer at the binary level; synthetic guest responses and physical FPGA behavior remain distinct evidence classes.

`tools/bench/inspect-acquired-apps.py` performs offline tar/ZIP inspection with generated output names, avoiding
extraction of arbitrary tar paths. Python's standard tar/ZIP readers were used for this bounded acquisition utility.
