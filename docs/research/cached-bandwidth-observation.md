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
