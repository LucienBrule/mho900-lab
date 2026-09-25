# ADC input capture: private controls

The frozen private suite `private-adc-input-capture-01` completed all eleven arms
with the expected native exit 78 and accepted frozen verification. The runner
exited zero. No stock application was installed or launched.

Arms 90 and 91 captured complete canonical and fallback selections. Arms 92–96
rejected the intended binding, table pointer, config pointer, excessive bound,
and unreadable address. Arm 97 retained the deliberately shortened matrix and
rejected incomplete capture. Arm 98 identified its exact one-bit canonical
divergence; arm 99 captured the changed delay/mode pair. Arm 100 rejected a real
late clone before the final loader checkpoint and before any ADC input capture.

The independent audit verified all 436 indexed artifacts. Normal terminal arms
completed four atomic steps before stopping; the late-clone arm completed three
before rejection. Debug-state clearing preserved the terminal general registers,
no terminal arm resumed afterward, and all three normal or four late-clone
threads were reaped. The private helper recorded the same `system_server` PID
1086 before startup, after every arm, and during finalization. Final state was
Enforcing, the stock package was absent, research processes were absent, cleanup
commands succeeded, and dedicated experiment listeners were released.

The userdata copy was byte-identical with an independent inode. It used a COW
clone and passed the 2 GiB free-space gate. Existing evidence, the stock APK and
native library, and the older frozen observer were preserved.

## Stock continuation requires an orchestration correction

The generic runtime reports `final_health_attempted = false`. Its dispatch list
includes older modes but omits `adcinputcontrol` and `adcinputmodel`. The private
helper has its own final health checks, which supply the observations above.
The stock verifier additionally requires the generic final-health artifacts;
its frozen stock run would therefore lack mandatory evidence.

No stock run was attempted. The native private controls are accepted, while stock
admission is deferred until a separately tasked routing repair and host review.
The initial post-run audit incorrectly expected the generic files in this private
run and failed on their absence. That audit and its error remain preserved; the
corrected audit checks the actual private-helper records and explicitly records
the dispatch omission. Neither raw guest evidence nor the frozen experiment was
changed or rerun.

The next bounded change should add the two modes to final-health dispatch, prove
success and failure finalization in host controls, and freeze a revised stock
contract. The capture binary, stock program, device responses, and successful
private results need no change. This is evidence about observation plumbing,
not physical calibration or acquisition.
