# Stock loader attempt: pre-admission harness abort

The first frozen stock-loader attempt did not test the loader hypothesis. The
guest booted, but the outer runner exited with status 255 during boot metadata
collection. No filesystem helper, stock install, stock launch, native observer,
or loader capture was reached in the available record.

`getprop.txt` includes `sys.boot_completed=1`; the next mandatory output,
`guest-kernel.txt`, is absent. The frozen runner uses `set -e` and invokes
`adb shell getprop` without recording its status. The strongest supported
explanation is that this command returned 255 after producing its output.
The command status itself was not captured, so the transport cause is unknown.

The EXIT cleanup ran: the emulator acknowledged the console kill, and the
dedicated listeners and emulator process were absent at independent review.
There are no final guest health samples. Cleanup is not evidence that
`system_server` stayed healthy, nor is boot completion evidence of stock
application behavior.

The frozen whole-loader verifier exits 3 because required evidence is absent.
No result or index was produced by the runner. A separate post-run preservation
index records every remaining regular run file, including the disposable disk
images, without filling in missing observations. The frozen source and inputs,
stdout, stderr, verifier failure, independent review, and preservation hashes
are pinned by `experiments/calibration-loaders/stock-run01-results.toml`.

Stock APK, native library, observer binary, and original ramdisk hashes remain
unchanged. The predicted loader returns and ADC state remain untested. The
next decision must address the harness's incomplete finalization path with
deterministic host controls before another guest attempt. The candidate's
stock code, modeled register values, and terminal checkpoint need no change
on this evidence.
