# Three stock calibration loaders match the static prediction

The unchanged whole-loader candidate completed in the second guest attempt.
The frozen verifier accepted the complete initialization prefix and all three
loader results. The previous attempt had stopped before stock admission; its
missing observations remain separate.

| Stock loader | Observed return | Observed destination |
| --- | ---: | --- |
| LSB | 192 | Complete 192-byte payload equals the stock default file payload |
| Vertical | 1,794,240 | Complete payload equals the stock default file payload |
| ADC | −1 | Both ADC paths absent; the 1,936-byte record is unchanged |

The ADC record was entirely zero in the entry capture and remained entirely
zero at the terminal checkpoint. This is now a live observation for this
fixture, beyond the earlier static zero-fill inference. It does not establish
valid physical calibration values or describe a real instrument's persistent
state.

Stock execution reached relative PC `0x333ba8`, immediately before the call to
`SetADCParameter(0)`. The call instruction did not execute. The inherited
two DNA reads, 466 stores, ten tail reads, and their synchronization checkpoints
validated before the loader sequence. No new modeled register response was
needed for the loaders.

All five complete captures were recovered. All 23 observed threads converged
before terminal capture and were reaped during cleanup. The captured
`system_server` samples remained PID 1048; enforcement stayed enabled. Final
file bytes, labels, four absent paths, package removal, runner collection,
health collection, and teardown statuses passed. Dedicated listeners were
absent after teardown. Stock APK, native library, original guest ramdisk, and
observer hashes remain unchanged.

The run spans 13:16:28–13:18:20 UTC on 2026-09-25. The actual repeat identity and
harness are pinned separately from the original prediction manifest consumed
by the unchanged verifier. See
`experiments/calibration-loaders/stock-run02-results.toml` for raw evidence,
verification, and independent review pins.

The next question is the complete software grammar of `SetADCParameter(0)`
under the captured record and existing shadows. Recover its transitive calls,
tables, loops, record reads, branches, and hardware-returned boundaries before
selecting another runtime candidate. This result supports that static recovery;
it does not yet establish useful UI, ADC programming, or acquisition behavior.
