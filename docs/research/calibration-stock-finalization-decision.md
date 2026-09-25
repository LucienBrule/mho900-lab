# Preserve failure evidence before repeating stock loader validation

The first stock-loader attempt stopped during boot metadata collection, before
stock admission. This is an outer harness failure and leaves the static loader
prediction untested. Neither the observer model nor stock inputs need changing.

Repair the runner's early exit path first: record mandatory command statuses,
skip admission after incomplete boot collection, attempt final health collection,
and preserve result, teardown, and an evidence index on runtime exit. Do not
retry a failed command inside the experiment. Exercise these paths using
deterministic host controls before a single fresh guest attempt.

The repeat retains the same complete initialization prediction, native observer,
two calibration files and their tested labels, absent ADC files, loader return
values, full buffer comparison, thread convergence, and terminal stop before
`SetADCParameter(0)`. The existing verifier remains frozen; additional runner
status evidence is reviewed separately.

If the loader observation agrees, recover the complete mode-zero parameter
routine statically through its return: all record fields, tables, loops,
branches, helper formulas, and hardware-dependent boundaries. The scope review
in the decision manifest identifies the existing partial grammar and unresolved
helpers. It does not claim this path was reached. This preserves the strategy
of whole-subsystem recovery followed by selective runtime falsification.
