# Stock ADC region validation

Stock Sparrow matched the complete **452-write ADC prediction** in `stock-adc-region-01`. The next access
was an unanswered main-thread W32 at offset `0x1000`, value `1`, using the stock store at library-relative
PC `0x27043c` (`0xb9000109`). This agrees with the recovered SPU reset sequence. No entry was added to the
transcript during the run.

The experiment used the unchanged stock APK/library, the exact native executable validated by the
[private controls](adc-transcript-controls.md), and the pinned [derived input](adc-transcript.md). It supplied
only the two existing synthetic identity reads and accepted the exact ordered ADC writes. Each accepted
store advanced only the PC; the mapped region stayed inaccessible and gained no device side effects.

## Observed inputs and state

Before the first accepted write, all eleven table/function/shadow bindings matched their expected library
locations. Both complete 111-word tables, four initializer/mask source words and the two initial shadow
records matched the pinned stock evidence. All 452 operands then agreed, including the initialized-shadow
tail that had previously been only a conditional prediction.

| Software state | Initial checkpoint | Terminal checkpoint |
| --- | --- | --- |
| ADC index-9 halfwords | `0x6721`, `0x6721` | `0x5721`, `0x4721` |
| ADC index-8 halfword | `0x000b` | `0x0000` |
| Identity object | Captured under the existing synthetic fixture | `0x0123456789abcdef` |

At the pending SPU access, the four independently checked SPU bindings exposed control `1`, gain `0`, TX
`0` and ADC-control `0`. **Control `1` is the checkpoint value after the first software bit-set**, before
its mapped store completes. It is not an observation of the value before SPU reset began. The separate
`GetSampleMode(1)` and `GetSampleMode(15)` selections were not captured and remain unresolved inputs to
the already recovered eight-write SPU sequence.

This is evidence for the complete predicted operand sequence, live input conditions and terminal software
state. It does not independently trace every internal call/return or exclude concurrent software-state
changes between checkpoints. Identifying the next store as SPU reset combines the observed operand with
the static call/operation graph; the common register wrapper PC alone does not identify its caller.

## Verification and preservation

The frozen independent verifier passed the stock binding checks, all pre/post register comparisons,
ordered transcript, terminal state, process snapshot and APK admission witnesses. Twenty initial threads
were covered, one runtime clone was observed, and all 21 terminal threads were quiesced and exactly reaped.
`system_server` remained PID 1073; enforcement stayed enabled. The stock hashes were unchanged, and the
disposable guest and dedicated services were stopped after capture.

The known composite snapshot command again returned 255. Its three separately captured commands each
returned zero, and the existing snapshot verifier validated those files, including 982 mapping rows.
The original composite status is preserved. No new snapshot workaround was introduced for this result.

The [result manifest](../../experiments/adc-transcript/stock-results.toml) pins inputs, raw evidence and
verification. No stable useful UI, ADC readiness, calibration, timing, sample data or acquisition is claimed.
The next decision should address the remaining software-selected SPU inputs and subsequent initialization
region, rather than discover each of the eight already predicted writes separately.
