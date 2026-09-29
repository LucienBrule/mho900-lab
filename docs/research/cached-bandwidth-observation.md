# Cached bandwidth observation contract

The remaining narrow physical capability question is whether the initialized
stock process holds the same raw and effective bandwidth enums as the acquired
stock guest. The prior physical SCPI run returned zero for all eleven documented
option selectors; it did not read either cached bandwidth field.

## Static contract

Pinned Auklet SHA-256:
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
Fresh disassembly, dynamic symbols and relocations establish:

| Field | Getter | ELF VA | ELF file offset | APK offset | Bytes |
| --- | --- | --- | --- | --- | --- |
| mStaticRawBand | GetModelBw, 0x429b40 | 0xbbcce4 | 0xbbbce4 | 0x1ac0ce4 | 4 |
| mStaticSysBand | GetBw, 0x429b10 | 0xbbcce8 | 0xbbbce8 | 0x1ac0ce8 | 4 |

Each getter loads its relocated global and copies one 32-bit word to its caller.
Neither getter performs device access or recomputation. The proposed external
reader will not invoke the getters. It will read each field twice through a
single read-only process-memory descriptor: four reads, sixteen bytes maximum.
Repeated equality is not an atomic snapshot guarantee. Enum 17 is the acquired
stock guest expectation; actual physical values remain unobserved by this batch.

Both fields occupy file-backed writable data. The data PT_LOAD maps virtual
addresses 0x1000 higher than file offsets; the APK's stored ELF begins at
0xf05000. Retain complete APK/ELF pins, unique executable anchor, exact loaded
segment geometry, permissions, process lifetime and backing-file checks from
the validated identity reader. Do not include DNA or file keys in this profile.

## Built-in option limit

ApiLicense_GetLicenseValid at 0x43254c checks license-map membership before its
OptType 1/2/3 branch writes true at 0x432674. This is built-in query policy,
not evidence for three simple cached booleans. No independently validated
physical heap traversal exists. Leave built-ins as a static expectation;
this observation will neither invoke license methods nor read the heap.

Private static evidence: `out/physical/cached-bandwidth-static-01`.
Static evidence index SHA-256: `6a4f1859d719d834d3a58de1d8e6e714b84e3c04638a382288db54cf6a454127`.

## Scope

The admitted first batch is offline reader construction and disposable-guest
control. Physical helper staging and observation require a separate admitted
batch after those controls pass. No entitlement installation, capability patch,
reboot, calibration action or analog bandwidth claim follows from these words.

## First control: unavailable guest utility

The new reader build passed sixteen host Python controls, ten compiled-C
mapping comparisons (one positive, nine negative), two ELF checks and two
SHA-256 checks. The separate reader source restricts four reads to four bytes
each. The original identity reader remains unchanged.

Disposable run `out/specimen-entitlement/apk-bandwidth-reader-01` stopped
at 13:58:21 UTC on 2026-09-29 before helper staging: guest `sha256sum` was
unavailable (exit 127). There were no reader attempts or process-memory reads.
The guest was terminated and its dedicated ADB server stopped. This is a setup
precondition failure, not a passing reader control. Evidence index SHA-256:
`4ba8acdfc30cc2fe45f5f8ebcabe6cad08cd2bb85ef1050dde971d4af5351d02`. The index covers evidence and frozen inputs; mutable emulator disk
images and runtime home directories are excluded.

The bounded successor will capture the guest policy bytes with `exec-out cat`
and compare them on the host. It retains identical reader binary, fixed ranges,
negative controls and guest policy; no utility installation or policy change
is needed. Physical observation remains gated on a passing guest control.

## Policy-byte control passed

Run `out/specimen-entitlement/apk-bandwidth-reader-02` completed at
14:00:07 UTC on 2026-09-29. It used the identical compiled reader; only policy
evidence collection changed to raw-byte capture and host-side hashing.
The independent verifier accepted all three pre-read negative cases and the
positive four-read observation. Both eight-byte samples contain distinct raw
and effective fixture words, in the correct order. Total target bytes: sixteen.

APK/ELF pins, process epochs, file identity, loaded mappings, roundtrip helper
bytes and independent address resolution agree. The guest remained Enforcing,
its policy bytes were identical before/after, and system_server PID stayed
unchanged. Loopback confinement passed. This synthetic control does not establish
physical permissions or values. The guest and its dedicated server were stopped.

Reader SHA-256: `111ae759668e89d13090fc4ac1a930072d9cccc715b4f6b819cdcbf89b6dc4d8`.
Complete run index SHA-256: `f7fa38ed3de9baf1e40f3888dca1cf9b90a9acd1417a6b30e3f8ed4387b4f2a1`.

The selected continuation is one separately admitted physical observation of
these two fields, twice, using existing ADB credentials and a fresh temporary
helper directory under fresh verified capture. Keep original APK/firmware and
application state unchanged. Temporary helper/output files are explicit
filesystem writes; no target call, attachment, register access or memory write
is involved. Stop on mismatch or denial, without alternate access methods.

## Physical observation: stock guest baseline corroborated

On 2026-09-29, the single admitted physical observation read raw enum **17**
and effective enum **17** from initialized stock Sparrow. Both eight-byte
samples match. The reader requested exactly four four-byte reads through one
read-only descriptor. Independent offline reconstruction validates all four
process/map epochs, pinned APK/ELF identity, file stability, mapping geometry,
address arithmetic and the sixteen-byte budget.

Fresh capture began at 14:02:26 UTC, before temporary host addressing.
The prior six-hour lease remained valid; no forced renewal was needed.
Existing ADB credentials retained their previously observed root identity;
no root request, daemon restart or authentication approval occurred.
The loaded APK was freshly pulled and matched the stock pin before helper
staging. The frozen helper was roundtrip-verified and invoked exactly once.
The helper/output directory remains as explicit temporary filesystem residue;
there was no additional contact to delete it.

Physical enforcement mode was Disabled before and after, as in the earlier
specimen baseline; this procedure did not change it. Guest Enforcing controls
and physical Disabled observations remain distinct claims. No target method,
attachment, memory write, mapped-register access, entitlement installation,
capability change, reboot or calibration action occurred.

All 42,042 complete stored frames pass replay of the recorded bounded network
classifier. The two final recorder counters both report 42,042; kernel drops
are zero and recorder exit is zero. Replay against that classifier is not an
independent proof that its rules are exhaustive. ADB disconnected, host address
was removed, lease helper stopped and isolation was rechecked. Network
preference files match baseline bytes. The privileged host shell was closed.
No new operator UI report was collected during this short observation.

Private run: `out/physical/mho984-cached-bandwidth-20260929T140142Z`.
Capture SHA-256: `68b94f233589293be083f37dead00e2df14a4b7ad95e5d58196e03cc02d06688`.
Evidence index SHA-256: `f4c4782d1bd7acb1996dff659c848283d6c7131a8e44bb8bb52f8930086e8320`.

## Physical decision

The physical cached capability baseline agrees with the acquired stock guest:
17/17. Together with the physical identity and eleven zero documented option
replies, this removes the immediate software-state discrepancy question.
Do not extend this to analog transfer function, calibration, three built-in
heap states, feature operation or physical entitlement persistence.

The next useful branch is offline: extend the specimen-derived guest's existing
single-option persistence proof to the individually installable catalog, then
compare that exact combined state under the separate derived capability arm.
The earlier synthetic catalog and specimen-derived FlexA-only capability test
remain distinct evidence until that combination is actually exercised. Further
physical reads of the same baseline would have little information value now.
