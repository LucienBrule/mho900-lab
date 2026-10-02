# Exact-stock enum 17/18 filter selection

Fresh static decoding of the admitted official 0.26 AArch64 ELF establishes a software selection difference at 4 GSa/s in the normal acquisition branch: bandwidth enum 17 selects digital filter ID 27, and enum 18 selects ID 29. Both branches load analog tuples whose constructor defaults are `(3, 3, 27)`. This identifies a concrete digital policy difference to investigate. It does not establish that the live measurement used either payload, or predict a physical bandwidth improvement from changing policy.

The machine-readable claim boundary is [contract.toml](../../experiments/rf-policy-filter-static/contract.toml). The stock SHA-256 is `4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`; size is 12,453,760 bytes. The source locator was taken from `official26.path` in the preserved three-way manifest and resolved through a configurable corpus root. The old report, assembly, coefficient inventory and synthetic matrix were used as locators. All function bytes, jump entries and the two payloads described below were reread from this hash-verified ELF. No prior matrix execution was rerun, and no device, guest or firmware state was changed.

| Exact driver condition | Enum 17 | Enum 18 |
| --- | --- | --- |
| `UpdateBandLimit` jump target | `0x301050` | `0x300e88` |
| `SetBandLimit` jump target | `0x302a28` | `0x30282c` |
| Sample-rate getter value | 4,000,000,000 | 4,000,000,000 |
| Normal branch selector | 11, excluding special selectors 6 and 8 | 11, excluding special selectors 6 and 8 |
| Selected digital filter ID | 27 | 29 |
| Analog tuple row | 6 | 7 |
| Constructor tuple default | `(3, 3, 27)` | `(3, 3, 27)` |

`UpdateBandLimit` uses a signed relative jump table at `0x99aad8`; `SetBandLimit` uses the same encoding at `0x99ab60`. Both index by `enum - 2`. The 4 GSa/s comparisons materialize `0xee6b2800`. The normal filter immediates are at `0x3010ac` and `0x302b30` for ID 27, and `0x300ee4` and `0x302934` for ID 29. The Update path substitutes selector 11 when `getAcquireMode() != 3`; a high-resolution acquisition reads its separate selector. The Set path receives its selector argument. These are explicit static inputs, not observations of the live device's hidden acquisition mode.

The AFE member is constructed at owner offset `0x242838`. Its tuple array starts at member offset `0x2868`, hence owner offset `0x2450a0`, with a `0x60` byte stride for four channels and eight 12-byte tuple rows per channel. The constructor stores row 6 at offsets `+0x48/+0x4c/+0x50` and row 7 at `+0x54/+0x58/+0x5c`; both are `(3, 3, 27)`. SetBandLimit's enum 17 branch reads owner offsets `0x2450e8/ec/f0`, while enum 18 reads `0x2450f4/f8/fc`, plus the channel stride. This links the driver loads to distinct rows with equal defaults.

`LoadAfeBandWidthCalData` supplies its checked-stream loader with member-relative start `0x2728` and size `0x140` (320 bytes), on both primary and fallback paths. Its exclusive end is `0x2868`, exactly the tuple array's start. Its subsequent direct default writes remain within that payload region. The supplied payload extent and direct default stores do not overlap the tuple array; this is not a recovery of every unexpanded checked-stream or save callee. Constructor provenance alone does not establish the live tuples: other runtime writers and the actual object's memory have not been excluded or observed.

The tuple wrapper compares all three fields against separate per-channel caches at setting offsets `0x1db8`, `0x1dc8` and `0x1dd8`, then updates and forwards them only when any field changes. `DevInOutAFE_SetHzFilter` packs the fields into register `0x2e` as

```text
(old & 0xf900) | ((a & 3) << 6) | ((b & 3) << 9) | (c & 63)
```

The default tuple inserts `0x06db`; bit 8 and bits 11–15 are retained from the prior register value. Equal tuple defaults therefore establish equal inserted fields, not equality of the complete live register word. The analog meaning of each field remains unknown.

The digital table contains 48 entries of 24 bytes, with payload pointer at `+8` and word count at `+16`. Resolving the exact ELF's `R_AARCH64_RELATIVE` addends gives distinct payloads:

| ID | Table entry VA | Payload VA | Size | SHA-256 of original payload bytes |
| --- | --- | --- | --- | --- |
| 27 | `0xb93940` | `0xb92ab8` | 64 words / 256 bytes | `d31bcee060aedb3ba8bedc7c6af8bcd0763a694e5aa95f1e27511b7b088ad63c` |
| 29 | `0xb93970` | `0xb92cb8` | 64 words / 256 bytes | `ca725b18d57162d1a2df7fea43c06fbef1eb7ac735d13d2d9c195069fcf0b3db` |

These hashes prove byte identity and difference. The words are preserved as raw little-endian 32-bit values; fixed-point interpretation, tap arrangement, normalization and effective response are not established here. An FFT of a guessed coefficient encoding would not resolve those missing semantics.

`DevAcquireSPU_SetSecondFilter` looks up the supplied ID and passes the resolved pointer and count to `configDspCoef1`, `configDspCoef2` or `configDspCoef3` for sample modes 1, 2 or 4. Modes 1 and 2 test the selected channel-mask bit; mode 2 also uses runtime counter parity. Enable flags can bypass coefficient programming. The driver call at `0x305fb8` supplies runtime getters for sample mode and channel mask, a calibration-owner byte at `+0x245aac`, an enable flag and the filter-ID argument. This establishes a consumer mechanism. It does not prove that an ID cached by SetBandLimit reached that call, or that the live DSP accepted or applied it.

SetBandLimit also has an early return when cached sample rate, bandwidth enum, high-resolution selector and impedance agree. On the update path it refreshes scale through `DrvChannel_SetScale` at `0x303c3c` and offset through `DrvChannel_SetOffset(..., true)` at `0x303ce0`, then stores filter/enable metadata. The normal ID difference must therefore be distinguished from a completed live transaction and any associated gain/offset refresh effects.

The upper API introduces additional selection gates. `ApiChannel_ConfigBandlimit` obtains `API_GetBandwidth()`, checks enums 17/18 against a virtual slot at `+0x58`, reads API scale storage at `+0x108`, and can select lower bandwidth enums before invoking the driver. Native scale thresholds of 200,000 and 500,000 occur there. It stores its bandwidth cache at `+0x120` before substituting the driver enum for a surviving FULL request. A cached FULL value therefore cannot establish the driver received enum 17 or 18. The driver reads `CChannel::getScale()` from its own channel object, while API scale setters include probe-ratio conversion and asynchronous property updates. This narrow recovery does not prove the numeric representation corresponding to the bench's 50 mV/div, the API-to-driver impedance mapping for the declared 50-ohm path, the live channel mask or the live sample mode. Those remain explicit unknowns; the public contract makes no claim that a live FULL request reaches enum 17 or 18.

The useful next bench question is whether a separately verified runtime transition from enum 17 to enum 18 changes the sampled response through the distinct digital banks while the actual analog tuple remains equal. Resolving that question requires its own admitted protocol with observed runtime selections and preserved acquisition geometry. The prior whole-chain survey and ordinary bandwidth-limiter control cannot establish this counterfactual. Static selection neither authorizes a policy change nor determines its physical result.

Fresh recovery evidence is preserved under the ignored `out/rf/policy-filter-static-20261002T000100Z/` root, with the bounded explicit-input decoder in `out/rf/policy-filter-static-tools/recover.py`. The decoder hashes one byte buffer and parses all symbols, segments, relocations and instructions from that same buffer. Seven source-rejection, occupied-output, repeated-decoding and preservation controls passed; 35 bounded input artifacts retained equal hashes. An independent stdlib ELF checker rehashes the source, resolves relocations separately, verifies key instructions and tuple stores, and rejects changed-source controls. The independent checker and final preservation inventory are separate receipts supplied with the task closure; they are not substituted for a physical witness.
