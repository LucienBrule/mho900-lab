# Decision: repair host admission before completing controls

The first loader-control attempt is a no-go for stock execution. It ended before
any loader arm or filesystem fixture ran. The native tail control itself passed
an explicit offline review; the observed failure was its verifier's old binary
digest requirement. A second, unreached host assertion compared 466 writes with
an index list containing only 464 entries.

Keep the native candidate, calibration candidate, private programs, register
responses, breakpoints, and capture interface unchanged. Add an explicit private
build profile to the legacy tail verifier and correct the loader index list.
The profile must retain the default and stock pins and reject stock use. Review
the preserved tail capture under both profiles before freezing a fresh suite.

Repeat the complete suite to obtain one coherent frozen run after admission is
corrected. This is justified by the previously incomplete run and changed host
verifier admission. It is not evidence that the new loader controls already work.
Stop at any divergence and report the exact executed subset. No runtime outcome
or native behavior will be changed merely to satisfy the prediction.

The [recorded first result](../../experiments/calibration-loaders/run01-results.toml)
and independent native and admission reviews support this bounded continuation.
The [successor batch](../../.agents/plans/calibration-loader-admission.yaml)
contains the host repair and private suite followed by a separate decision gate.
Stock execution remains unadmitted.
