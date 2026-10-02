# RF acquisition: input-impedance prerequisite stop

The first A1 controller stopped before changing the source or scope settings.
Its fresh SCPI snapshot reported CH1 input impedance `OMEG` (1 MΩ), while the
frozen acquisition required `FIFT` (50 Ω). No waveform record was acquired and
this attempt is not an accepted A1 arm.

The snapshot also reported 50 mV/div, 2 µs/div, 10,000 points and 500 MSa/s.
Those observations describe the starting state; they do not establish the
required acquisition settings. The existing normalization rejected the
impedance difference before planning any writes. No RF contrast or input
amplitude can be inferred from this prerequisite stop.

The completed run is preserved separately at
`out/rf/policy-comparison-A1-normalized-20261002T032400Z`, with native manifest
SHA-256 `1b0a7b523bd2e5a42564818c797b2ef57f64a35bc5b89f15178ec678b328dcd5`:
123 artifacts and 17,306,495 bytes. The full Layer Two recorder retained 368
packets, reported a matching received count and zero kernel drops, and exited
gracefully. The temporary host address was removed and the isolation checks
passed afterward. The source was not commanded by this attempt; no native
selection, reboot, option installation or calibration action occurred.

Independent reconstruction verified the sole SCPI flow as exactly the 26
initial read-only queries. The review is sealed at
`out/rf/A1-impedance-stop-independent-20261002T033300Z.toml`, SHA-256
`19e3bff87a762c80cc4eb58980ea3aa6833270529f1a8f8350b9a137897e9fab`.
The before-query process snapshot matched the accepted stock epoch and mapping;
this attempt did not take another memory-policy observation or a post-stop
process snapshot. The evidence establishes that the controller issued no
experimental writes, rather than proving universal absence of device-side
state changes.

The next bounded question is whether the already-authorized ordinary 50-ohm
selection can be included in the captured normalization and restoration path.
The proposed variant must accept only `OMEG` or `FIFT` as its starting
impedance, issue `FIFT` once when required, and verify the original 50-ohm
prerequisite before any acquisition. It must preserve the full starting
snapshot and restore `OMEG` if that was the original state and SCPI framing
remains healthy. Unknown impedance values remain a stop condition.

This preparation and its decision are tracked as
`TASK.rf.impedance-preparation` and `TASK.rf.impedance-decision`. The original
controllers and this negative evidence remain immutable. A fresh attempt
requires independently reviewed preparation, a reasoned GO, and a committed
and pushed checkpoint. The 75-slot comparison, source power code, RAW sampling,
range guards, estimator and return-control criteria remain unchanged.

The bounded remedy decision is GO. The separate producer preparation is sealed
with SHA-256 `2c35dcd76fc60bc1b093696c3f51789f3213a1bb39f4939a6fdadd07b3861b04`;
independent readiness review is sealed with SHA-256
`30b1035c581c7c27adb2195d952dc7799abde3916160075f983b9387eb2e493f`.
Six producer and sixteen independent controls passed, including required
50-ohm verification, command ordering, conditional restoration, unknown-token
rejection and unchanged acquisition behavior. The fresh actual A1 root is
`out/rf/policy-comparison-A1-impedance-20261002T034000Z`, with control manifest
SHA-256 `d5debde9b13856dc10eba40d6064975cc545b4d2437a3cbaeebe9395201391e8`.
No physical acceptance follows from that readiness review. Execution still
requires fresh process, isolation, settings and receiver checks.
