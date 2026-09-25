# Stock version and DDR-consumer initialization

The byte-identical stock application matched the complete recovered initialization
tail under the fixed synthetic fixture. Run `out/guest-admission/stock-init-tail-01`
started at `2026-09-25T10:51:16Z` and finished at `2026-09-25T10:53:02Z`.
The observer executable was identical to the successful private controls.

After the two DNA responses and 464-store prefix, stock executed the predicted
ten reads and two stores without another hardware access. All three checkpoints
passed. The last checkpoint stopped at relative PC `0x2e57f8` before its branch
instruction executed, leaving the calibration path unentered.

| Stock consumer state | Observed value under the synthetic fixture |
| --- | --- |
| Packed version | `0x12345678` |
| Hardware version | `0x10203040` |
| DAC shadow and store at `0x1428` | `0x646e` |
| Tap outputs, argument order | `0x21, 0x345, 0x234, 0x456, 0x167, 0` |
| Ready byte | `1` |
| Status object from `R32 0x1008` | `0x20000000` |
| Control shadow and store at `0x1000` | `0` |

The live configuration selected the predicted skip-tap path. Parent-frame tap
outputs were checked at their actual widths, including all four 64-bit outputs.
The clock-counter response was `62500`; its recovered predicate was not captured
from a dead helper frame and is not claimed as a separate live observation.
The ready byte, not that clock predicate, controlled the recovered retry path.

Direct initial checkpoint arming and all subsequent rotations matched the private
control profile. Read completion changed only W9 and PC; store completion changed
only PC. Checkpoint setup and clearing preserved all captured registers. The
final stop preceded calibration rather than inferring its absence from the
observer's private-only counters.

All 21 initial threads and one prefix clone were covered and exactly reaped.
No clone appeared in the added region. Four `system_server` samples stayed at
PID 1066, enforcement remained enabled, stock APK/library hashes stayed unchanged
and the dedicated guest listeners were absent after teardown. The independent
preservation audit verified all 192 indexed artifacts and frozen sources.
The frozen verifier accepted an unchanged evidence copy and rejected twelve
isolated altered copies with regenerated indexes, testing the semantic checks.

This establishes actual stock software propagation under explicitly synthetic
instrument state. It does not establish FPGA reset values, physical DDR training,
clock accuracy or acquisition. Main-thread checkpoints are not an atomic snapshot
of the process. The next boundary is calibration initialization; recover that
subsystem and its environment dependencies statically before adding responses.

Reproduce with pinned local inputs and a fresh run identifier:

```sh
ANDROID_SDK_ROOT="$ANDROID_SDK_ROOT" tools/guest/run-admission.sh NEW_RUN_ID tailmodel
kotlin out/guest-admission/NEW_RUN_ID/source/VerifyStockInitTail.main.kts \
  out/guest-admission/NEW_RUN_ID
```

The [result manifest](../../experiments/init-tail/stock-results.toml) pins the raw
capture, executable, verifier, independent audits and altered-evidence checks.
