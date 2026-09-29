# Specimen raw acquisition: complete live reads, userdata differences

Two independent reads of `/dev/block/mmcblk0` each produced exactly **31299993600 bytes**, returned status zero,
and had empty error streams. Both originals are preserved separately and read-only. Their whole-device hashes differ,
but **every byte outside the userdata partition is identical**. This includes all fifteen other named partitions and
the gaps outside them, including the complete `/rigol`, system, kernel, boot, and recovery regions.

The kernel identifies the card as **SD**, product `MSSD0`. This supersedes the earlier eMMC assumption; physical
packaging was not inspected. See [the storage classification correction](physical-storage-classification.md).

| Read | SHA-256 |
| --- | --- |
| First | `06d40136e071f06e971aeeffe705476dac958ba379e8886bd7d20684dfb090e7` |
| Second | `aef20abb3a5047bcdda086505acc748a1f1032be0bb6ff36dbdb68d332be04ac` |

The first read ran from 2026-09-29 03:26:12 UTC to 04:17:12 UTC, or September 28 20:26:12 to 21:17:12 PDT.
The second ran from 04:17:55 UTC to 05:09:00 UTC, or September 28 21:17:55 to 22:09:00 PDT.
The recorded event log retains subsecond timestamps. Each read opened the block device through a separate
`cat /dev/block/mmcblk0` invocation over the already authorized ADB transport. No device-side staging was used.

## What differs and what that proves

The full comparison found **52150905 differing bytes**, all within userdata. The report groups these into 112
coalesced ranges at 4096-byte granularity, covering 148041728 bytes. The larger covered size is not a count of changed
bytes. Kernel sysfs supplied all sixteen partition starts and sizes; observed by-name links supplied their names.
All differences fall entirely within the observed userdata extent.

This is consistent with reads of a live mounted Android filesystem. The changed files and exact causes have not
been attributed. Neither read is an atomic filesystem snapshot, and neither is declared an independently verified
restorable image. No reboot, remount, freeze, or repeated acquisition was used to force matching hashes. Both
originals remain authoritative for their respective read intervals.

Acquisition-time Python hashes were independently reproduced by the Kotlin whole-image comparator. The comparator
also checks input size, modification time, and file identity across its read. Its controls cover equality, changed
bytes across buffer boundaries, a partial final block, short images, and accidental comparison of one file to itself.
The five mounted ext4 signatures were observed at the kernel-reported offsets in the acquired bytes.

## Capture, host restoration, and physical state

The unfiltered full-packet Ethernet capture is 67989986953 bytes. Graceful recorder shutdown reported **65541469
captured, 65541469 received by filter, and zero kernel drops**. Final offline validation checks complete record lengths
and replays the recorded traffic classifier. Known host-local discovery background was retained, as previously accepted
by the operator. Three single-client DHCP renewals were acknowledged without gateway or DNS options.

The temporary host address was removed and the lease responder stopped. IPv4 and IPv6 forwarding remained disabled;
the normal default route stayed on the separate interface. Network preferences and hardware-interface mapping plists
are byte-identical to their pre-acquisition baselines. This restores the isolated bench configuration, not the Mac's
pre-bench network-service settings. The prior restoration material remains preserved.

The single authorized ADB root transition occurred during logical acquisition; raw acquisition only rechecked UID 0.
No second root request, unroot, reboot, firmware, entitlement, capability, or calibration operation was issued.
The ADB transport was disconnected at the end. The instrument remains powered and physically connected as before.

Three read-only QuickTime camera-preview observations showed the normal waveform UI with no prompt and an advancing
clock; the last was after acquisition. The visible front USB host port and analog inputs remained empty. These are
sampled visual observations, not a continuous recording or an input-responsiveness test. Their transcriptions are in
the private observation log; screenshots remain in the conversation, with no separate image-file hash claimed.

## Evidence and next boundary

Private run: `out/physical/mho984-raw-acquisition-20260929T032542Z`.

- `images/mmcblk0-read-1.img` and `images/mmcblk0-read-2.img`: untouched raw originals.
- `raw-comparison.toml` and `partition-comparison.toml`: whole-image and partition coverage results.
- `live/capture.pcap` and `capture-validation.toml`: raw traffic and final validation.
- `baseline/`, `after/`, `metadata/`, `events.jsonl`: host state, commands, errors, and timing.
- `sealed/SHA256SUMS`: final private artifact inventory; hash recorded in the public result manifest.

The [logical acquisition](physical-specimen-logical-acquisition.md) independently establishes that the active Sparrow
APK, packaged Auklet, and active Web Control APK match official `.26`. That permits reuse of existing binary-level
research. It does not make synthetic hardware responses physical evidence or establish that all installed firmware
components match `.26`. The next useful boundary is specimen-derived guest environment and entitlement behavior,
with full board-image boot kept separate and physical mutations held at their later authorization gates.
