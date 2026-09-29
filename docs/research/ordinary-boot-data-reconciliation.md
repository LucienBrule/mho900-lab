# Ordinary boot data reconciliation

The retained pre-reboot and post-reboot archives show no change to the 320-byte
AFE bandwidth coefficient payload. The two changed files are consistent with
stock startup persistence: a fresh checked-record header and a randomized
identity fallback cache. This is an offline interpretation of retained evidence,
not a calibration operation or a measurement of RF performance.

| File | Observed change | Interpretation |
|---|---|---|
| `data/cal_afe_bandwidth.hex` | 348 bytes before and after; only offsets 0–3 and 12–15 changed | Header CRC and time metadata changed; all 320 payload bytes remained identical |
| `data/cal_tmp_hex.log` | 172 bytes before and after; all byte positions changed | Stock vendor-data loader writes a randomized encoded identity fallback cache |

Both files were identical between the postboot and post60 snapshots. Both
bandwidth records pass header and payload CRC checks, declare a 20-byte header
body and 320-byte payload, and have no trailing bytes. The twelve words that the
stock loader sets to 115 already had that value in both records. No default
bandwidth record was present in these archives; a default fallback is not needed
to explain the observation.

The [recovered AFE loader](afe-calibration-static.md) reads the bandwidth payload,
unconditionally applies those twelve words, and saves the primary record during
normal initialization. `LoadAfeBandWidthCalData` starts at `0x350e44`; the stores
start at `0x350f2c`, and the save helper starts at `0x350fbc`. The
[checked-record contract](../interfaces/checked-calibration-record.md) explains
why saving identical coefficients can change local-time-derived header metadata
and its CRC. Metadata was compared as bytes, without inventing a date decoder.

Despite its filename, `cal_tmp_hex.log` is an identity fallback cache rather than
an AFE coefficient record. In stock `CApiUtility::ApiUtility_LoadVendorData`
(`0x42a9e0`), the pathname at `0x9aac57` is used for both reading and writing:

- The fallback read opens the file at `0x42b128`, reads at `0x42b150`, decodes at
  `0x42b188`, and reconstructs identity bits used by the vendor-data key path.
- The write path opens that same pathname in mode 2 at `0x42cc68`. The loop at
  `0x42cca0` selects 57 identity bits. `random_device` at `0x42cd84` seeds the
  generator; a uniform distribution of digits 0–9 is configured at `0x42cdc8`.
- The loop at `0x42ce98` interleaves each identity character with two generated
  digits. The 171-character result is padded to a multiple of four, encoded at
  `0x42d020`, written at `0x42d054`, and followed by `fsync` at `0x42d070`.

Consequently, byte identity of this encoded cache is not a valid expectation
across a stock startup. This bounded review did not decode either private cache
or independently compare their underlying identity bits. The producer explains
why a 172-byte cache can change without changing calibration coefficients; it
does not by itself authenticate an arbitrary replacement cache.

The accepted reconciliation audit separately retained unchanged licenses, key
and vendor files and all other data-file contents, ten enabled ordinary options,
and stock cached bandwidth values 17/17. Its screenshots also retain the normal
restart display difference from 52 to 50 mV/div. No reset or calibration command
was issued by these controllers. That command audit and the unchanged coefficient
payload support a startup rewrite interpretation; they do not establish analog
accuracy, the absence of every internal startup hardware action, or durable
storage beyond the retained observations.

Evidence is retained privately under
`out/overnight/ordinary-boot-calibration-delta/`: original extracted bytes,
archive inventory, reproducible `analyze.py`, `analysis.toml`, and
`pinned-code.asm`. The latter's 2,817 instruction words were checked directly
against stock ELF SHA-256
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
The source disassembly is
`local/reversing/analysis/three-way/official26-full.asm`.
The reconciliation evidence seal is
`526628e2db6504925c44e61536d24e8b377243b364772de10b14a414b0f1ecc1`.
The pre-reboot archive precedes the transport-timeout interval; the postboot
archive comes from the separate reconciliation capture, so this comparison is
not a continuous trace of the writes themselves.
