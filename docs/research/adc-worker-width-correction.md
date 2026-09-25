# ADC worker-width checker correction

The checker now expects `0xb9400109` for arm 108's worker load, matching the
pinned compiled instruction and the actual attempt-02 trace. The change is one
opcode expectation. Thread identity, mapped address, PC, rejection ordering,
absence of modeled transfers and complete thread cleanup remain checked.

`tools/guest/test-adc-worker-width.main.kts` disassembles the pinned worker symbol
and replays arms 101–108 from independent copies of attempt 02. It also changes
the worker opcode, substitutes the leader thread, changes the mapped address and
corrupts the cleanup count in separate copies. The actual production checker must
accept the eight original records and reject those four corruptions. The original
492 indexed files are rehashed before and after the controls.

This offline acceptance of arm 108 does not revise the frozen attempt-02 result.
Its original verifier failure remains preserved, and arms 109–112 remain
unexecuted there. Read-only inspection found the remaining clone, deadline,
missing-atomic and final-shadow control paths consistent with their checker
expectations; only the new guest attempt can establish their outcomes.

`experiments/adc-sequence/control-inputs-03.toml` freezes the corrected checker
with the same native executable, profile, synthetic responses and twelve arms.
`worker-width-results.toml` records the controls and manifest digest. After the
freeze is pushed and its task closed, the separately admitted attempt uses:

```sh
ADMISSION_ADC_SEQUENCE_INPUTS="$PWD/experiments/adc-sequence/control-inputs-03.toml" \
  tools/guest/run-admission.sh private-adc-sequence-03 adcsequencecontrol
```

The suite still stops at the first unexpected result. Stock validation remains
gated on actual private control completion.
