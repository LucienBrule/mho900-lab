# First range stop in the matched RF comparison

The first stock arm stopped at the initial 100 MHz visit before collecting a
waveform. The matched stock–derived–stock comparison is **unassessable**, and
absolute 1 GHz response is **not assessed**. The acquisition, reduction and
decision tasks close this negative experiment; the RF response milestone still
requires a bounded follow-up.

The [frozen contract](../../experiments/rf-policy-comparison/contract.toml)
requires 75 unique records: 25 each for initial stock A1, derived B and returned
stock A2. All 75 are missing from this attempt. No B transition or A2 collection
occurred.

## What was observed

The initial process metadata matched the previously accepted stock epoch and
original APK/native mappings. Owned transport, isolated networking and capture
readiness passed. Acquisition settings read back as 50 Ω, DC, 1× probe ratio,
zero offset, FULL bandwidth, 50 mV/div, 1 µs/div, 100,000 points and 4 GSa/s.

One source command requested 100 MHz at raw power code zero. The serial driver
accepted nine bytes; the sender received no device acknowledgement. This proves
the host transport attempt, not the source's actual frequency or output level.

After the serviced five-second RUN interval, the scope returned these sequential
built-in measurements:

| Query | Response |
|---|---:|
| Frequency | `1.1111E+07` Hz |
| Vpp | `0.34393` V |
| Vrms | `0.083215` V |
| Vmax | `+0.18643` V |
| Vmin | `−0.19478` V |

Vmin was evaluated first and failed the unchanged strict ±0.18 V guard. Vmax
also exceeds it. Vpp passed its separate 0.36 V upper bound. The controller
stopped before `acquisition-begin`, any RAW DATA or preamble query, and every
waveform record.

These replies were obtained separately while acquisition was running. Their
extrema span is 0.38121 V, different from the reported Vpp. They do not establish
one coherent waveform, actual clipping, a calibrated voltage or the source's
fundamental frequency. The reported frequency discrepancy remains an open
question. This result provides no evidence that CH1 is dead and no measurement
of a 1 GHz policy effect.

## Restoration and evidence

The controller restored and verified the entire pre-normalization ordinary
settings snapshot and all six waveform-export values while SCPI framing remained
healthy. This included the original 1 MΩ impedance, 50 mV/div, 2 µs/div,
10,000-point depth and 500 MSa/s readback. No native selection, reboot, root
restart, entitlement or calibration write occurred. The last source request
remains nominal 100 MHz/raw power zero, with delivered RF unconfirmed.

The owned ADB server was reaped and its process/socket absence verified before
removing the temporary host address. DHCP and recorder exited gracefully.
Capture statistics retain 736 captured/received frames and zero reported kernel
drops. Host preference bytes match before and after; a separate host-only check
confirmed restored isolation and absence of the owned physical helpers. The
exception prevented a final or restored process-epoch read, so restoration is
not represented as a new native-policy observation.

| Preserved manifest under `out/rf/` | SHA-256 |
|---|---|
| `policy-comparison-A1-pinned-20261002T173100Z.toml` — raw run, 401 files | `a325ff2670905fcf2973b72e547ed0ac8be7c4b80bbd82e1927253ab2b1ca9d7` |
| `A1-builtin-abort-independent-20261002T174000Z.toml` — independent negative review | `52994c91bcbc6ee51cb4df39b282d47f1d9aa2d317cb87861e44e1db979bd208` |
| `A1-pinned-host-restoration-20261002T174000Z.toml` — current host-only proof | `deeea2c42312bf51f82f1a8cb8847a84d2d0919591765a6aac56749884e549ab` |
| `first-range-abort-reduction-20261002T175000Z.toml` — empty actual-data reduction | `1289560b40439ea389d5949f7675c12515f8582aee1ae04768b19a122a9d4832` |
| `first-record-range-assessment-20261002T174000Z.toml` — offline diagnostic proposal | `bad8a8590ecdac348b9d25eb89c52fe56fb78b9accc502297e8142ed2a58f879` |
| `first-range-abort-final-host-20261002T175000Z.toml` — recorded keepawake retirement | `f875d830da55e64279754edff76b83fe17426c9ea7e573aec16ab0194692febe` |

The unchanged frozen decision helper received zero actual records and returned
`unassessable` with `missing-duplicate-or-unplanned-slot`. No group statistics,
return controls or gain ratios were calculated. All 48 entries of the existing
numerical evidence inventory were rehashed; its 45 owner and 19 independent
controls remain applicable. Synthetic fixtures and older archived waveforms
were not substituted for missing comparison slots.

The deadline-bound host keepawake was retired after matching its recorded
process birth and command. It required no specimen contact. Earlier manually
estimated timestamps in five actor submissions are preserved with explicit
later clock-derived taskctl reviews: the closure and evaluation actions occurred
within the sampled UTC interval 17:44:45–17:48:45 on 2026-10-02. Individual
submission times were not sampled. Capture/controller event timestamps remain
the authority for physical chronology.

## Smallest next question

**With the source confirmed at 100.00 MHz / Point and the same cable untouched,
does one fresh stopped RAW acquisition at a wider vertical range show an
approximately 100 MHz waveform with comfortable headroom, or do its samples
corroborate a different or unusable signal?**

The offline proposal uses one separate diagnostic at 100 mV/div, retaining
50 Ω/DC/1×/zero/FULL, 1 µs/div, 100,000 points and measured 4 GSa/s. It would
preserve the full current settings first, capture one RUN→STOP record and equal
before/after preambles, report sample extrema, headroom, shape and periodicity,
then restore the full original settings. A source command would be unnecessary
if the displayed state is independently confirmed. No native transition, reboot
or new wiring belongs to that diagnostic.

This is a proposal requiring a separate admitted contract and operator decision;
it has not been implemented or executed. It cannot relax the frozen comparison's
guard or become an A1 slot. A known attenuator rated for the relevant frequencies
is an alternative only after its availability and a new physical path are
explicitly established. Physical acquisition remains on hold.
