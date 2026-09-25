# Continue from ADC into the complete AFE calibration contract

The stock ADC prediction passed with the frozen synthetic readbacks. Keep the
mapped-access observer: this experiment provides no evidence that a kernel facade
or emulator device is needed to reproduce the next initialization stage. Continue
static-first recovery and reserve guest runs for branch ambiguity and observation
of complete state transitions.

The dispatcher stops at `0x333bac`. Existing byte-pinned dispatcher and loader
records identify AFE zero loading at `0x333bcc`, AFE bandwidth loading at
`0x333bd8`, then clock loading at `0x333bf4`. AFE zero requests 560 payload bytes
from primary/fallback `cal_afe_zero.hex`, targeting AFE object offset `0x29e8`.
Bandwidth requests 320 bytes from primary/fallback `cal_afe_bandwidth.hex`, targeting
`0x2728`. Both use `/rigol/data/` and `/rigol/data/default/`. The dispatcher ignores
their returned statuses; this does not prove that internal loader state or later
consumers ignore failure.

Bandwidth loading has additional software initialization and a call to
`DrvCalibrationAfe_BandWidthSaveData`. Its reachable effects must be resolved
before admitting a continuation. Selecting only the first loader now would risk
returning to per-operation discovery while the neighboring software contract is
available statically. The next batch therefore recovers the entire AFE loader
pair, including that helper, before choosing a runtime boundary. Clock and later
calibration remain outside this batch.

These facts come from `experiments/calibration-static/dispatcher.toml`,
`loaders.toml` and `call-inventory.toml`, corroborated against the stock library.
They establish code order and candidate filesystem behavior. Neither AFE loader
executed in the successful ADC experiment, and no AFE fixture or hardware response
has been supplied. The current guest construction supplied only LSB and vertical
calibration files; corpus and live guest absence claims need separate witnesses.

The admitted successor consists of one static recovery task and one evaluation
task. It must classify deterministic operations separately from runtime selection,
hardware-returned values, asynchronous behavior and unknowns. Its evaluation may
admit a small preparation/control/stock validation batch under standing operator
authorization, with tasking committed and pushed before execution.
