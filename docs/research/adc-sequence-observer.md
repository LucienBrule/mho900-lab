# Whole-sequence observer private-suite freeze

Status: **frozen for the private suite; not guest-tested**. The freeze is recorded
in `experiments/adc-sequence/control-inputs.toml` and `freeze-results.toml` in the
same directory. Execute only after taskctl makes
`TASK.guest.adc-sequence-private-run` ready and the freeze is committed and pushed.

The profile compiler binds the completed ADC candidate and emits 99 bus operations:
97 writes and two explicitly synthetic reads. Its 175 entry guards cover typed
calibration/runtime fields, live shadow values, relevant mask-table words and
selector fields. It also emits 33 scalar final-shadow expectations. Regenerating
the profile produces byte-identical C and TOML artifacts.

The native observer adds `control-adc-sequence` and `stock-adc-sequence` commands
with the existing loader command argument shapes. The private `adcsequencecontrol`
admission mode stages pinned inputs, executes arms 101–112, and stops the suite
on the first unexpected result. Do not launch it until the freeze task and the
applicable execution prerequisites are complete.

## Implemented behavior

The mode preserves the inherited initialization and software-input capture, then
checks the relevant entry values while the whole thread group is stopped. It
checks the selected row and mapped base, relies on the existing relocated binding
and selected-pointer checks, and compares field values independently of relocated
pointer bytes. A mismatch stops before the ADC continuation.

After arming the post-return breakpoint, it resumes every live stopped thread.
Mapped accesses must come from the admitted thread and match the predicted
instruction, width, address, order and write value. Reads supply `0x00011234` and
`0x00000000`, respectively, as software protocol controls. Only the witnessed
mapped instruction's required register/PC state is completed; execution between
accesses uses ordinary continuation. Sleeps remain in the stock code and are not
observed or claimed as validated by this boundary.

The terminal stock breakpoint is at `0x333bac`, before that caller instruction
executes. It requires all 99 accesses, zero routine return status, and the 33
predicted final-shadow values. It then converges and cleans up the thread group.
Unexpected accesses, signals, clones and deadlines stop the experiment rather
than extending the modeled response set.

The private fixture has twelve planned arms:

| Arm | Question |
| ---: | --- |
| 101 | Complete sequence, worker dependency, both read protocols, atomic progress and final stop |
| 102 | Changed first write operand |
| 103 | Reordered first two accesses |
| 104 | Omitted first access |
| 105 | Unknown read before the predicted sequence |
| 106 | Breakpoint at the wrong private terminal PC |
| 107 | Changed entry configuration field |
| 108 | Another tracked thread accesses the mapping |
| 109 | Clone during the new phase |
| 110 | Deadline while waiting after the worker handshake |
| 111 | Missing private atomic completion |
| 112 | Wrong final shadow |

The fixture's explicit worker handshake requires another thread to progress after
entry capture. Its read helper decodes both ready-bit branches. Its final
exclusive load/store loop precedes the breakpoint site. These are designed
controls, not yet observed guest outcomes and not execution of the stock ADC
routine inside the private fixture.

## Completed host checks

The native executable builds as a freestanding static ARM64 ELF. An initial link
failure caused by an implicit large-structure `memcpy` was corrected with explicit
register-field copying. The compiled-image checker inspects the actual ELF data
layout for all 99 operations, 175 entry guards and 33 final shadows. It also
confirms the contiguous `LDAXR` / increment / `STLXR` / retry loop immediately
before the private stop-site call. Static inspection does not prove runtime
exclusive-monitor behavior.

The image controls accept the built image and reject changed compiled operands,
a changed guard width and a changed final atomic instruction. They use independent
copies and preserve the original image. The profile is regenerated independently
and compared byte-for-byte with the tracked generated artifacts.

## Independent verification and execution

The private-run verifier covers the inherited prefix, raw captures and maps,
entry guards, ordered register transitions, expected failures, worker/atomic
outcomes, terminal state and cleanup. One complete synthetic trace passes; five
targeted corruptions fail: operation value, register value, entry guard, atomic
completion and thread cleanup. These host fixtures test the checker, not guest
behavior. Draft-checker and fixture-construction errors were corrected before
freeze; the failed host outputs remain local. All 436 indexed artifacts from the
older private input-capture suite still match their original hashes.

The runner and final suite audit are integrated. The production index controls
accept all required nested inputs and reject four missing/changed/duplicate
variants. Seven mocked runtime cases check health routing, error propagation and
cleanup. The final suite audit accepts a synthetic complete record and rejects ten
corrupt provenance, capture, index or health variants. It checks the externally
supplied manifest digest and requires every consumed artifact in the final index.
The per-arm verifier separately checks native event semantics; a successful final
integrity audit cannot replace those checks.

With a configured Android SDK, the admitted private run uses:

```sh
tools/guest/run-admission.sh private-adc-sequence-01 adcsequencecontrol
```

The helper checks each arm immediately and stops on an unexpected outcome.
After finalization, audit the suite with the frozen manifest digest from
`freeze-results.toml`:

```sh
kotlinc -script tools/guest/VerifyAdcSequenceRun.main.kts -- \
  out/guest-admission/private-adc-sequence-01 "$FROZEN_MANIFEST_SHA256"
```

Keep that audit output outside the finalized run directory to preserve its index.
An unexpected result closes this experiment as a negative; it does not authorize
editing its evidence or changing the frozen suite and retrying it.

The stock validation still requires the later decision task. No guest, stock
application continuation or new hardware response has been executed by this
freeze. The stock APK and native library remain unchanged.
