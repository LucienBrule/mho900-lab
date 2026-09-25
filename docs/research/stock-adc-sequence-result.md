# Stock ADC sequence matches the static prediction

The single frozen `stock-adc-sequence-01` attempt passed. The byte-identical stock
Sparrow application and library executed all 99 predicted ADC register accesses:
97 software-determined writes and two reads supplied with the explicit synthetic
values `0x11234` and zero. The native observer stopped at unexecuted relative PC
`0x333bac`, opcode `0x5285070a`, immediately after ADC parameter initialization.

The independent frozen checker accepted the inherited startup prefix, all 175
entry guards, raw calibration/configuration captures, access order and operands,
register transitions and all 33 final software-state values. The full sequence
was validated in one stock attempt; no operation-by-operation experiment or
adaptive retry was required. This supports the static-first strategy for this
routine and selected configuration.

The reads remain synthetic instrument responses. This result does not establish
physical ADC readiness, reset values, timing, acquisition, or a useful UI. The
51 statically predicted sleep calls were not separately timed by the observer.
The private suite's worker/atomic witnesses remain private controls; the stock
record correctly reports those private metrics as zero.

The observed group contained 23 threads. The observer checked thread coverage,
converged the group at the final checkpoint and reaped all 23. `system_server`
remained PID 1042 across admission, observation and final health; enforcement
remained enabled. Emulator console, signal, wait and dedicated ADB cleanup all
returned zero. All four dedicated listener ports were idle after teardown.

All 378 indexed artifacts rehashed successfully. The installed APK and its native
library matched their established hashes, as did the host originals before and
after the run. No physical instrument was accessed. Raw local evidence remains
under `out/guest-admission/stock-adc-sequence-01`; external verifier output and
preservation audits are under `out/stock-adc-sequence-preparation`. The durable
hash summary is `experiments/adc-sequence/stock-run-01-results.toml`.

The next dispatcher calls are AFE zero and bandwidth calibration loaders, followed
by clock calibration. Those instructions have not executed in this experiment.
Their filesystem and software-state contracts are the next static recovery scope;
this result supplies no response or behavior for that subsystem.
