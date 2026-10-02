# Matched RF comparison: execution decision

The stock readiness and execution decisions are GO for one frozen
stock–derived–stock comparison. The [warm stock baseline](rf-warm-stock-baseline.md)
and [remaining-arm preparation](rf-remaining-arm-preparation.md) are independently
verified. No comparative RF result is asserted by this decision.

The protocol remains the committed
`experiments/rf-policy-comparison/contract.toml`, SHA-256
`e1c0d43d4c06d0ff8c89e119859ae401bf33355a2a950e31335ccbb56bcfd11f`.
Each arm visits 100, 800, 975, 1,000 and 100 MHz, with five fresh RAW acquisitions
per visit: 25 records per arm and 75 records overall. Collection uses the same
50-ohm path, source power code, 100,000-point record, 4 GSa/s sample rate,
50 mV/div scale and unwindowed population AC RMS calculation in every arm.

The primary question is whether every derived-to-stock pair at nominal 1 GHz
shows at least a 1 dB increase, with both stock arms providing the comparison.
Every reverse-direction pair meeting the same margin is contrary evidence;
intermediate contrast is unresolved. The ten frozen return controls must remain
within 0.3 dB. Missing, invalid or unavailable controls make the result
unassessable. Secondary 800 and 975 MHz observations cannot replace the primary
question. No anchor correction, fitted-amplitude estimator, extra points or
outcome-driven repeats are introduced.

A1 starts from independently accepted stock policy 17/17. The derived transition
must establish the pinned native selection and 18/18 after its single normal
reboot, fresh UI, preservation checks and serviced warmup. The final-stock
transition must establish stock 17/17 with the same requirements. Each arm is
sealed and evaluated before proceeding, and the final software state is stock.
Healthy capture completion restores the actual pre-normalization ordinary and
export settings; the source ends at the final planned 100 MHz visit.

The concrete A1 control inventory is sealed at
`out/rf/policy-comparison-A1-normalized-20261002T032400Z-control.toml`, SHA-256
`386a17ac1acb06f894ba9044a3affc198ce099a9b4a0d7efc491413248425830`.
Independent concrete preparation review is sealed at
`out/rf/A1-concrete-preparation-review-20261002T032700Z.toml`, SHA-256
`3ce15967139a1ccbbd46845c47b1e1172a9a5df41a6a3a95abd32888a00bc6a4`.
It verifies the actual projection, original source/dependency pins, fresh local
outputs and the independently replayed captured 24-hour lease. No gateway, DNS,
forwarding or external route is introduced. Fresh runtime checks still apply.

The individual-arm verifier passed 20 controls and a complete synthetic
25-record witness; its preparation is sealed with SHA-256
`e62cb047ae37663adc2a4fbc5adf3a8f86455740e205c074810428454f6cd310`.
It independently checks original RAW records, exact source attempts and SCPI
bytes, process continuity, restoration and recorder statistics. Its legacy TCP
profile retains optional FIN diagnostics. Preparation is not acceptance of any
physical capture; the unchanged 75-slot reducer remains the final numerical
analysis.

The renewed operator authorization covers these reversible transitions and
ordinary capture operations until 2026-10-03T01:38:03Z. No new wiring, option
installation, calibration or host-security change is part of this procedure.
Unexpected state, overload, transport uncertainty or failed arm verification
stops the run and preserves its evidence. This decision is committed and pushed
before collection.

Any supported result describes the observed response of this fixed, uncalibrated
measurement chain under verified software policies. Source frequency commands,
cached policy values and increased sampled RMS alone do not establish a
calibrated 1 GHz analog bandwidth or independently authenticate fundamental
amplitude at the connector.
