# Whole-sequence observer implementation checkpoint

Status: **compiled prototype; not frozen or guest-tested**. Resume taskctl task
`TASK.guest.adc-sequence-control-freeze`. The private-run task remains waiting.

The profile compiler binds the completed ADC candidate and emits 99 bus operations:
97 writes and two explicitly synthetic reads. Its 175 entry guards cover typed
calibration/runtime fields, live shadow values, relevant mask-table words and
selector fields. It also emits 33 scalar final-shadow expectations. Regenerating
the profile produces byte-identical C and TOML artifacts.

The native observer adds `control-adc-sequence` and `stock-adc-sequence` commands
with the existing loader command argument shapes. No admission-runner mode has
been added yet. Do not launch either command as an admitted experiment until the
freeze task and the applicable execution prerequisites are complete.

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

## Work required before freeze

- Implement the independent private-run verifier, covering the inherited prefix,
  raw input captures, new entry guards, each access and register transition,
  expected failure arms, worker/atomic outcomes, terminal state and cleanup.
- Exercise that verifier with meaningful positive and corrupted host evidence.
- Add the private admission helper and runner mode, source/profile pins, final
  health routing and indexing for all newly consumed nested inputs. Test the
  actual production index function and runtime health paths.
- Freeze the complete sources, binary, profiles and verifiers; commit and push
  the freeze before the one admitted private guest suite.

The stock validation still requires the later decision task. No guest, stock
application continuation or new hardware response has been executed by this
implementation checkpoint. The stock APK and native library remain unchanged.
