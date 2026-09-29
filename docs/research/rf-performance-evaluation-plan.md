# Stage 5: RF performance evaluation plan

Status: prepared offline on 2026-09-29; **no RF test executed**. This plan makes no firmware changes and does not authorize a deployment, calibration write, or hardware operation. The operator must supply the RF equipment and a separately accepted stock/derived/rollback transition. The smallest useful result is a paired, corrected sine-response measurement on one channel at one gain setting. It is not a complete instrument certification.

Software selection and physical performance are separate evidence. The [capability component](specimen-d-capability-component.md) and [acquired comparison](acquired-capability-comparison.md) associate enum17 with `BW_800M` and enum18 with `BW_1G`, while retaining MHO984 public identity. Those results establish software policy. They do not establish an analog transfer function, calibration accuracy, or 1GHz performance. Before testing, attach the current physical software-state evidence; earlier guest reports are not a substitute.

## Evidence and applicable conditions

The local vendor-authored MHO900 datasheet was examined as text and its main specification table visually checked. It lists MHO984/MHO954/MHO934, **not MHO984D**; no 1GHz guarantee is imported from it. The archived datasheet's hash identifies the local document, not an independently authenticated download. The separately downloaded official user guide has a retained URL/retrieval receipt.

| Source | Relevant findings | Locator |
| --- | --- | --- |
| `local/reversing/MHO984D-Intel/MHO900_DataSheet_EN.pdf` | MHO984: 800MHz at−3dB into50Ω with one or two channels; 400MHz with three/four. At1MΩ the corresponding limits are500/400MHz. Maximum sample rates4/2/1GSa/s for one/two/three-or-four channels. Warm-up more than30min; properly grounded. | PDF page9, printed page6; channel-mode definitions PDF31/printed28 |
| Same datasheet | 50Ω±1%; 50Ω maximum input5Vrms; no transient overvoltage; FULL/250MHz/20MHz bandwidth settings. | PDF10–11, printed7–8 |
| Same datasheet | Operation0–50°C; recommended calibration interval18months. Internal AFG maximum100MHz; Bode plot maximum30MHz. | PDF29/printed26; PDF23–24/printed20–21 |
| [Official MHO900 User Guide](https://www.rigol.com/dam/global/downloads/brochures/en/user-manual/oscillosopes/MHO900_UserGuide_EN.pdf), §24.5 | More than30min warm-up before SelfCal; recommends SelfCal particularly after ambient change≥5°C. SelfCal changes instrument state and is not automatically part of this comparison. | Local `out/physical/host-recorder-control-20260929T022423Z/guide/official-MHO900-UserGuide.pdf`, PDF302/printed284; adjacent `user-guide-provenance.toml` |

Datasheet SHA-256: `ea71d7d881d71018201f07ce679431e0e37b9dae1412e98e0cc26ea1d4ed95af`.
User-guide SHA-256: `0fcd76ebc1e454af0f699811df5c2acd6243ade8e0626a0352c2d9d493dafab2`.

The plan below supplies experimental choices, not vendor performance-test instructions. No vendor service procedure for certifying a modified1GHz path was established in this review.

## Equipment and readiness

Use an external calibrated sine generator covering10MHz through at least1.2GHz. The internal AFG, compensation square wave, and built-in Bode plot cannot supply this test. Record generator model, calibration status, frequency/amplitude uncertainties, settling time, and harmonic/spurious limits at the actual levels. Verify troublesome harmonics with a suitable spectrum analyzer or documented filtering; a source amplitude display alone does not establish applied fundamental amplitude.

Use short, repeatable50Ω coax, rated adapters, and preferably a characterized fixed attenuator near the input to improve source match. Fix the complete cable/pad/adapter assembly mechanically. Supply a calibrated power sensor or reference receiver covering the sweep to establish fundamental level at the DUT connector reference plane. A VNA measurement of cable/pad loss and source/load reflection coefficients is preferred for mismatch uncertainty. A power-meter substitution into a nominal50Ω load still requires allowance for the DUT's RF input mismatch; the datasheet's DC resistance tolerance is not RF return loss.

For a defensible absolute−3dB statement, characterize delivered fundamental amplitude at every frequency, including reference frequency, before and after the comparison. If only generator setpoint or uncharacterized cables are available, report a qualitative A/B observation and stop short of claiming measured1GHz bandwidth. A VNA is not intrinsically required if a conservative, documented mismatch bound and calibrated substitution chain provide an adequate uncertainty budget.

Record scope and source warm-up exceeding30min, calibration dates, ambient temperature and stability, power/ground configuration, channel configuration, and any cooling interruptions. Target a stable laboratory temperature, for example23±2°C; this is a plan target, not a new vendor specification. If SelfCal is needed, obtain the separate operator decision, preserve calibration provenance before/after, and complete it once before the entire A/B/A comparison. Do not independently self-calibrate each arm and then attribute their difference solely to policy. A material thermal change or necessary recalibration invalidates the paired comparison until restarted under equivalent conditions.

## Fixed acquisition configuration

Use CH1 alone, CH2–CH4 disabled, logic acquisition disabled, DC coupling, native50Ω termination, probe factor1×, offset0, FULL bandwidth. Disable high-resolution, averaging, peak-detect, math filtering and automatic scale/channel changes. Use normal sample acquisition and verify the **actual acquired** rate is4GSa/s in every arm; exported waveform decimation must not silently replace it. Two-channel2GSa/s places1GHz at Nyquist and is unsuitable for this initial test.

Set a sine level of approximately200mVpp at the connector (70.7mVrms,−10dBm for a matched50Ω load), zero DC, and50mV/div: four divisions peak-to-peak at low frequency. These are conservative test choices, far below the listed5Vrms input ceiling; do not interpret that ceiling as permission for high-frequency overload or transients. Keep source output off while connecting/changing termination, verify its amplitude/load convention, then enable at the predetermined level. Use the same gain setting throughout. Stop on clipping, unexpected offset, overload indication, termination change or visible instability.

Capture at least10µs per waveform, nominally40,000 samples at4GSa/s, and at least five independent records at each point. Confirm record length, time increment and full waveform availability in saved metadata. At10MHz this covers100 cycles. Preserve raw waveforms and preambles; do not estimate amplitude only from displayed pixels, interpolated peaks, or a screenshot. Fit DC plus sine/cosine at the independently known fundamental frequency (or a bounded frequency fit), derive fundamental Vrms, and retain fit residuals. This avoids the phase-dependent peak-to-peak error from approximately four samples/cycle at1GHz. Screenshots and built-in measurements are supporting checks.

## Smallest paired experiment

Keep the RF cable connected and fixed. Use three arms: A1 stock enum17, B separately accepted derived enum18, A2 verified rollback enum17. Preserve actual native/APK hashes, model identity, raw/effective enum evidence, settings and calibration identity for each arm. Keep ordinary license state identical across all arms. This document supplies no deployment or rollback commands. If changing software requires a reboot, re-establish the same thermal and acquisition conditions before measuring.

| Point | Purpose |
| --- | --- |
| 10MHz | Low-frequency normalization and repeated drift anchor |
| 400,600MHz | Detect an incorrect channel mode, limit/filter, or broad response change |
| 800MHz | Published MHO984 single-channel50Ω reference edge |
| 900,950,1000MHz | Detect the proposed extension and directly measure the1GHz point |
| 1050,1100,1200MHz | Determine whether/where response rolls off beyond1GHz |

Measure all ten points in A1, B and A2. At minimum repeat10MHz and800MHz at the end of each arm, and repeat the source reference-plane calibration before and after all arms. Settle at each point according to the generator's documented requirement and stable readings. Use identical acquisition settings and source level; correct for measured delivered level instead of assuming a flat generator. An optional second B arm is justified only if A1/A2 drift or measurement uncertainty prevents a conclusion.

The ten-point experiment answers whether selected RF points differ and whether the1GHz point meets the chosen criterion. It cannot exclude an unsampled dip. To report a sampled−3dB crossing, add a fixed25MHz grid from600 to1200MHz, then refine the crossing bracket with10MHz steps. Report the actual bracket and any multiple crossings; interpolation is an estimate. A claim of continuous bandwidth or full product performance needs a more complete sweep and vendor-style channel/gain/environment coverage.

## Reduction, uncertainty and decision rules

For each arm and frequency, compute

`H(f) = measured fundamental Vrms / delivered fundamental Vrms`

`G(f) = 20 log10(H(f) / H(10MHz))`.

The−3dB amplitude ratio is approximately0.708. Use the same fundamental estimator throughout. Report corrected absolute response and the paired difference `Δ(f) = G_B(f) − G_A(f)`; bracket A with A1/A2 and retain their separation as a drift witness. Do not normalize each trace to its maximum or force its800MHz point to−3dB. A stock instrument may exceed its minimum advertised bandwidth; failure to distinguish A and B is a valid result.

Build an uncertainty budget in dB covering calibrated source/sensor relative response, cable/pad loss and reconnect repeatability, source/load mismatch, source drift, scope gain/nonlinearity/noise, finite-record sine estimation, repeatability, and thermal/software restart drift. Include correlations: common errors can cancel in a paired difference but do not disappear from an absolute bandwidth claim. Use measured repeat dispersion and justified TypeB bounds; state distribution assumptions and coverage factor. As a planning target, seek expanded uncertainty `U95≤0.3dB` near800–1100MHz and A1/A2 agreement within that budget. This target is not a manufacturer tolerance. If unavailable, widen the result's interval rather than dropping terms.

Predeclare these judgments before applying RF:

- Baseline validity: stock800MHz response is consistent with its stated−3dB limit and the setup checks pass. If `G_A(800)+U95 < −3dB`, stop and investigate the source, path, acquisition settings and calibration before attributing any change to software. If the interval straddles the limit, baseline conformity is inconclusive.
- At1GHz, B supports the selected-point target only if `G_B(1000)−U95 ≥ −3dB`. If `G_B(1000)+U95 < −3dB`, it misses that target under the recorded conditions; otherwise the result is inconclusive. Apply the same rule to every sampled passband point rather than cherry-picking1GHz.
- A reproducible policy-associated difference requires the positive B-minus-A response change to exceed its own expanded difference uncertainty at the nominated high-frequency points and A1/A2 to agree within their comparison budget. No improvement claim follows from enum18 alone, or from B meeting a limit that A also meets.
- Rollback acceptance requires stock hashes/enums/settings to return and RF A2 to agree with A1 within the predeclared budget. Failure preserves the evidence and stops further RF/configuration changes for operator review. It does not trigger calibration repair, automatic reinstall or unrelated storage changes.

Do not derive a1GHz verdict from rise-time alone: the datasheet's437ps value is calculated/typical and the usual bandwidth-times-rise-time relation assumes a response shape. A separate pulse/ringing test, other channels, other gains, two-channel operation, noise/ENOB, distortion and temperature coverage are follow-on evaluations, not consequences of this single-channel sine experiment.

## Operator handoff and retained evidence

Before execution, fill in equipment availability and calibrated range, exact cable/pad chain, delivered-level/mismatch characterization, uncertainty budget, thermal window, capture/export method, accepted software-state transitions and rollback reference. These are the remaining operator inputs; equipment capability has not been inferred from the repository.

Retain a TOML run manifest with source-document hashes; software/calibration/configuration hashes per arm; generator/sensor identifiers and calibration dates; frequency, setpoint and corrected input level; raw waveforms and preambles; fit amplitudes/residuals; repeated-reference drift; uncertainty calculations; UI/setting witnesses; source output state on completion; and actual rollback result. Keep specimen identifiers and raw private evidence in ignored run output. Publish only a sanitized table/plot and scoped conclusion: one channel, selected scale, acquisition mode, temperature, sampled frequencies, uncertainty, and what was or was not established.

Stage5 is ready for operator preparation. No RF measurement, hardware access, firmware modification or calibration action was performed in producing this plan.
