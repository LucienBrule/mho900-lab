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
