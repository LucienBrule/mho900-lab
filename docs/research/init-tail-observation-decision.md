# Decision: test one coherent synthetic initialization region

The [static tail graph](initialization-tail-grammar.md) identifies ten returned words,
two deterministic writes, one writable configuration selection and a completion bit
before calibration. Test that entire region with the fixed
[candidate](../../experiments/init-tail/candidate.toml), retaining the validated
464-store prefix and its two synthetic identity words.

The first eight new words are synthetic markers chosen to make truncation, packing and
output ordering visible. Their high bits are not claimed to represent instrument
state. They produce packed version `0x12345678`, hardware version `0x10203040` and
tap outputs `0x21,0x345,0x234,0x456,0x167,0` in argument order. Status `0x20000000`
sets only the stock completion bit. Counter `62500` lies inside the recovered clock
predicate. This is coherent for this bounded software consumer; it is not a calibrated
FPGA personality or evidence for those values on physical hardware.

Permit exactly the ordered mapped operations in the candidate: three version reads,
DAC write, five tap reads, memory-reset write, and the self-test's two reads. Existing
stock load/store instructions execute with only their witnessed mapped-access effects
supplied by the observer. Read completion changes only the load destination and PC;
write completion changes only PC. Retain exact opcode, width, offset, main-thread,
signal and address-register checks and verify complete register readback after each
completion. Do not substitute native function returns or change code bytes.

Use three rotating main-thread hardware breakpoints. At `0x2e547c`, require three reads
and one write, the live DDR selector and `w10` equal to 1, the version locals correct,
and the DAC shadow correct. At `0x2e55a8`, require all ten reads and both writes, a
zero self-test return, six correctly masked tap outputs and ready byte 1. At
`0x2e57f8`, require no additional mapped access and unchanged relevant parent state,
then stop before the scope lookup leading to calibration. Preserve all registers at
checkpoints and validate the exact established clear/rearm profile.

Arm the first new checkpoint while the main thread is stopped, no later than completing
the first new version read. Capture bound live DAC upper half zero, SPU control zero,
series/configuration selection and config field 1 before supplying new returned state;
repeat relevant guards at their consumption boundaries. Require the exact stock
function/data bindings. Snapshot values are observations at stops, not an atomic
process-wide state proof. Unexpected mutation, changed selector or extra access is a
terminal negative, not an invitation to widen the fixture during the run.

Use the parent frame for version, tap and completion outputs. Do not read guessed
clock-helper locals after the helper returns; their ABI lifetime is over. The exact
clock-read response is evidence, and the derived clock predicate remains a static
prediction unless captured separately. No extra clock checkpoint is needed to answer
whether this region reaches calibration under the fixed candidate.

Keep the existing group observer and thread accounting. Any worker mapped access,
new clone in this region, unexpected trap, omitted checkpoint, process exit or deadline
is terminal. The existing prefix clone handling remains intact. Quiesce and reap the
whole registered group on every outcome; preserve `system_server` and enforcement.
A successful terminal stop establishes this consumer's path to calibration only.

Before stock execution, run a private suite with the exact new executable. Include the
complete positive region, atomic completion before each new checkpoint, wrong read
order/width/thread, wrong write operand, bad live shadows/config/binding, corrupted
parent outputs, extra self-test access, ready-byte mismatch, stale-site revisit and
deadline cleanup. Preserve prior observer regressions and malformed-input controls.
Keep new counters and event fields distinct from the earlier identity/remaining-region
counters. Independently verify raw fields and state transitions, not declared matches.

Admit private implementation/control, one fresh stock falsification, and an explicit
evaluation task. A private negative closes its own question and keeps stock gated;
a successor must be deliberately admitted. Commit and push tasking before implementation
and each conclusion before the next run. Neither calibration nor later known stores
are admitted here. Kernel-device adaptation and emulator-side observation remain
unnecessary for this recovered mapped-access region.
