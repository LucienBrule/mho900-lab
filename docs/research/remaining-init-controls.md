# Remaining initialization observer: first control result

The first private control stopped on an unexpected debug-register readback before
arming its first native checkpoint. This is a negative observer result, not evidence
about Sparrow's transport branch. Stock execution remains gated on a successful
successor control.

Run `group-remaining-init-01` used executable SHA-256
`d6630eafbe3646f938f0de42ddfe84ec1ee9c4a1fd6f9cb8c2ed85c04a243586`.
All forty existing runtime controls and thirty malformed-input controls passed.
The new suite stopped after arm 40; arms 41–58 did not run.

The private program completed the 452-write ADC prefix, eight SPU writes and two SCU
writes, retaining only the two existing synthetic identity reads. After SCU write 2,
the observer read 264 bytes of initially empty hardware-breakpoint state with metadata
`0x0606`. Its 24-byte request to clear slot 0 used address zero and control zero.
The request returned success. The following 264-byte readback retained the metadata
and zero addresses, but slot 0 control was `0x1e4`; all other slots remained zero.

The fixed observer expected an all-zero cleared slot, emitted `debug-initial` rejection,
and stopped without installing a target, reaching a checkpoint, or executing the private
atomic work. Terminal counts were 462 accepted writes, zero checkpoints, zero atomic
increments and zero device-I/O sentinel writes. All three threads were quiesced and
exactly reaped. This does not establish whether the physical breakpoint was disabled:
a register-set readback and actual delivery are separate observations, as the earlier
[execution-stop investigation](guest-execution-stop.md) already demonstrated.

The compiled fixture review established ten distinct NOP checkpoint sites outside its
exclusive-load/store loops, atomic completion before each following checkpoint, and
success-open sentinels after their stopping points. Those are static fixture properties;
this run did not dynamically establish rotation, atomic progress, successful-open stops,
LA stores, the final version-read boundary, or the remaining negative controls.

## Independent verification

The frozen success verifier rejected the capture. Its first failure was an independent
literal-check bug: it compared zero-padded captured strings against ELF words that also
contained adjacent bytes after the terminator. Post-run verification now checks the exact
literal including its terminator against the ELF, then derives the padded captured words.
A second corrected expectation uses the completed synthetic identity value
`0x0123456789abcdef` at the private terminal object, rather than its initial sentinel.
The original source, error and raw evidence remain frozen in the run directory.

An explicit `40-clear-negative` verification mode checks the actual incomplete sequence,
successful clear request, exact anomalous readback, immediate rejection and complete
cleanup. It does not weaken the success profile. The valid evidence copy passes; seven
altered copies fail after removing a clear readback, removing its SET result, changing
the control word, changing an unused slot, changing the SET result, changing the atomic
count, or removing a reaped thread. The original capture is unchanged.

The ordinary success verifier also requires every breakpoint SET result and readback,
completion of each rotation, and a register-invariance record before resuming. It cannot
accept an omitted rotation merely because the next checkpoint appears.

All 47 recorded `system_server` samples retained PID 1070. Enforcement remained enabled,
the stock package was absent, and teardown stopped the dedicated guest services. Stock
APK and library inputs remain unchanged. The next bounded question is the guest's
clear/rearm readback and delivery contract. Do not change the fixed experiment or run
stock merely to bypass this observation.

See the [control manifest](../../experiments/remaining-init/controls.toml),
[result manifest](../../experiments/remaining-init/control-results.toml), and
[region decision](remaining-init-decision.md).
