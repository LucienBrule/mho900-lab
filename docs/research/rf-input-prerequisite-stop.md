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
