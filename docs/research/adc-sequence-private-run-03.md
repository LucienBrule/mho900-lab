# Private ADC sequence qualification

Attempt `private-adc-sequence-03` passed all twelve frozen private controls and
the final suite audit. The native executable and profile are unchanged from the
original freeze. The only per-arm checker change is the compiled worker-load
width correction documented in `adc-worker-width-correction.md`.

The complete arm executed all 99 predicted accesses, including 97 writes and the
two explicit synthetic logging readbacks. Worker acknowledgment, uninterrupted
atomic completion, the 33 expected final shadows and an unexecuted precise final
instruction were verified. The eleven negative controls rejected changed,
reordered, omitted and unknown operations; a wrong terminal PC; mismatched entry
state; another thread's mapped access; a new clone; a deadline; missing atomic
completion; and an incorrect final shadow. Every tracked thread was reaped.

The independent final audit checked 413 consumed artifacts within the complete
649-file index. All indexed hashes also passed a separate rehash. `system_server`
remained PID 1052 across the suite and final health collection; Enforcing remained
active. Sparrow was absent throughout. Final health commands, emulator teardown
and ADB teardown succeeded; reserved ports were idle afterward. Stock APK and
native-library hashes are unchanged.

This qualifies the private observation mechanism for the bounded candidate. It
does not establish that stock ADC initialization follows the candidate, that a
physical FPGA supplies these responses, or that acquisition works. Earlier
attempts retain their original outcomes: attempt 01 never started a guest;
attempt 02 stopped at its frozen checker mismatch. Offline replay does not replace
those records.

The supported next batch prepares one stock validation of the full predicted ADC
sequence. It must reuse the validated calibration filesystem, preserve the stock
APK and native library, check entry guards and every predicted access, and stop
at unexecuted caller PC `0x333bac`. Only the two declared synthetic logging
responses are supplied. Unknown accesses, new threads or mismatched state remain
decision events. No next-subsystem response is included.

`experiments/adc-sequence/private-run-03-results.toml` binds the manifest, final
audit, index, preservation and teardown evidence.
