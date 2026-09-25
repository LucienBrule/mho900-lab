# ADC software input capture decision

Use the existing mapped-access observer to collect one bulk snapshot before
`SetADCParameter(0)`, at the proven library-relative PC `0x333ba8`. The reviewed
[whole-subsystem contract](adc-parameter-review.md) supplies deterministic
software formulas; the missing inputs are the live matrix, shadows, and runtime
selectors. No new device response or execution past this checkpoint is needed
to obtain them.

The [capture decision](../../experiments/adc-input-capture/decision.toml) freezes
nine raw regions totaling less than 16 KiB. They cover the matrix and bucket
state, setting and sample-rate objects, series selectors and rows, selected
config and mode entry, and all fifteen live shadow objects. The existing terminal
ADC record supplies the main fields. One diagnostic-only ADC field remains
explicitly outside the snapshot because it cannot affect the predicted operands.

Capture follows whole-group convergence and the five existing loader captures,
and precedes the loader summary and bounded teardown. The observer must validate
relocations, object arithmetic, readable mappings, selected pointers, and bounded
sizes before dereferencing. The modeled mapping pointer is observed as a value
and is never read as ordinary memory. There is no post-terminal resume.

The series-table correction from review is applied: read only the selected
8-byte entry after stock mask normalization and an independent bound of 1–16
entries. Do not interpret that bound as a physical channel count. The maps
snapshot is capped at 2,048 records and 256 KiB, informed by the previous stock
snapshot's 988 records and 101,422 bytes. Overflow or partial evidence rejects
the capture.

A separate verifier will retain every inherited stock-loader check and explicitly
bind the new native and runtime identities. The old frozen verifier remains
unchanged. Independent recomputation from raw bytes, complete event ordering,
source pins, evidence indexes, final health, and cleanup are required.

The admitted batch contains implementation and host verification, one private
control suite, one stock observation conditional on accepted controls, and a
decision. Each guest conclusion is committed and pushed before another run.
Unexpected results close the attempted question and require deliberate branching.

Available storage is constrained. New disposable userdata staging may use verified
copy-on-write copies with separate inodes; a preboot space gate is required.
Existing evidence and source images will be preserved.

Changing to a kernel facade, emulator device, or higher native substitution is
not justified by this input question. Advancing a whole sequence before binding
the matrix and shadows would mix software-input assumptions with device-response
assumptions. Once the snapshot is accepted, the next batch can instantiate the
complete candidate and test it at meaningful checkpoints.
