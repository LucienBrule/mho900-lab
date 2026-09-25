# Stock ADC software-input capture

Stock Sparrow reached the established pre-ADC stop and the observer captured all
nine requested regions, totaling 11,565 bytes. The capture-phase checker accepted
them. The overall frozen stock verifier rejected the run at its final evidence
index-coverage check; this remains the recorded experiment outcome.

The selected software state is:

| Input | Observed value |
| --- | ---: |
| Series selectors | 8, 900 |
| Selected row | 2, exact match |
| Channel enable mask | 0 |
| Normalized table mask | 0 |
| Table entry bound | 16 |
| Sample-mode word | 1 |
| Signed sample rate | 0 |
| Configuration ADC delay | 250000 |
| Configuration point time | 250000 |

The bound is a table-index safety value, not a physical channel count. Under the
reviewed static grammar, sample rate zero selects the Stary bypass-only path:
the candidate whole routine has **97 writes and two readbacks**, with 25,200 µs
of requested sleeps. This is a prediction from captured software inputs. The
ADC call at `0x333ba8` remained unexecuted, so these operations have not yet been
validated dynamically and imply no physical calibration or acquisition behavior.

The inherited prefix and loader checks passed before the index failure. All
22 tracked threads converged and were reaped, with no post-terminal resume.
`system_server` remained PID 1129 before admission, after detachment, and after
observation. All generic final-health and cleanup commands returned zero;
Enforcing state, package removal, absence of research processes, and release of
the dedicated listeners were checked. Runner exit was zero and native exit was
78. Instrumentation detached normally; no timeout adjustment was made.

## Index failure and evidence boundary

All 325 indexed files match their recorded hashes. The nine raw input captures,
native events, frozen source, and health evidence are indexed. Exactly eight
consumed files under `adc-parameter-static/` are missing from the index. They are
present and independently match the fixed hashes embedded in the frozen stock
verifier, but the runner index loop does not visit that new nested directory.

The synthetic full-profile host fixture used a recursive index builder. It
therefore tested index rejection without exposing this mismatch with the actual
runner. This is a harness integration gap, not a reason to rewrite the finished
run's index or turn its frozen rejection into a pass.

The original evidence, original index, and failed verification output remain
unchanged. A separate audit identifies every missing entry and its matching
frozen hash. The next decision should consider an offline completeness review,
correction of future indexing with tests that invoke the actual index function,
and typed instantiation of the 97-write candidate from the existing snapshot.
No guest rerun is needed to answer the index question.

Free space after the run was below the current 2 GiB preboot gate. Further guest
execution requires a separate capacity decision; current evidence is preserved.
