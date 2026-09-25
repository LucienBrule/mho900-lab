# Calibration loader observer protocol

Modes are `control-loaders ARM ADCFILE SPUFILE OUTDIR` and `stock-loaders PID BASE ADCFILE
SPUFILE OUTDIR`. They retain the admitted ADC/SPU, remaining-init, and init-tail prefix and
add four main-thread execution stops: the three loader-return instructions and the call to
`SetADCParameter(0)`, which is never executed. No mapped response is added.

`loader-mode` records scope, arm, profile, four checkpoints, five captures, and the
`inherited-direct-arm-v1` debug profile. `loader-binding` records each getter, parent, loader
GOT slot and resolved target. `loader-layout` records scope, calibration, ADC, vertical, and
three destination address/length pairs.

Each stop emits `loader-checkpoint`, `loader-checkpoint-registers`, the signed 32-bit
`loader-status`, the existing 264-byte GET/24-byte SET debug events with `loader-` names, and
`loader-debug-registers`. Registers must not change during rotation.

Entry capture occurs while the inherited tail terminal stop holds the main thread:
`loader-entry-lsb.bin` (192 bytes) and `loader-entry-adc.bin` (1936 bytes). Terminal capture
follows full group convergence: `loader-terminal-lsb.bin` (192), `loader-terminal-adc.bin`
(1936), and `loader-terminal-vertical.bin` (1794240).  `loader-capture` records phase, index,
filename, address, requested length, completed byte count, chunk count, and completion. Raw hashes
are independently computed by the host verifier; the observer does not claim a cryptographic digest.

`loader-rejected` records reason, stage, TID, checkpoint, actual, and expected before bounded
group cleanup. `loader-summary` records checkpoints, captures, atomic count, clone TID, and
zero modeled reads/writes. All runtime outcomes exit 78; CLI/parser errors exit 2 and cleanup
failures retain existing non-success codes.

Arm 80 also emits `loader-worker-debug-*` GET/SET/GET and register events before any private
thread resumes. This private-only setup arms checkpoint 0 on the existing worker TID so the
wrong-thread control observes a real per-thread hardware-breakpoint stop.

Arms 76 and 77 reach the terminal boundary. Arms 78..89 isolate wrong PC, opcode, thread,
binding, pointer, length, short bulk read, full-buffer mismatch, unexpected mapped access,
clone, a successful old-breakpoint revisit, and missing-checkpoint deadline respectively.
Private buffers and actual program values are generated independently of observer expectations.
