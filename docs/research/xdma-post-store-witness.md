# Stock mapped responses reach application state

Run `post-store-snapshot-01` proves one bounded device-response to stock application-state transition. The unchanged
stock library consumed synthetic high word `0xe1234567` at mapped offset `0x4048` and low word `0x89abcdef` at
`0x4044`. At the precise stop immediately after its global store, `m_DNA` and `x8` both contained
`0x0123456789abcdef`; `x9` pointed to the expected global object. The global previously contained `UINT64_MAX`.

The result agrees with the [statically decoded composition](xdma-identity-flow.md):

```text
((uint64_t(0xe1234567) << 32) | 0x89abcdef) & 0x01ffffffffffffff
    = 0x0123456789abcdef
```

The supervisor supplied only those two guarded 32-bit reads. Stock instructions performed the composition,
masking and store. After the second response, execution continued normally to a hardware breakpoint at ELF
`0x42a8f0`, immediately after `str x8, [x9]` at `0x42a8ec`. The actual stop had signal 5/code 4, matching PC and
signal address, and the expected instruction word `0x14000001`. No instruction stepping through synchronization,
forced mutex return, instruction edit or third device response was used. The application was terminated/reaped
after capture, before the following branch and later identity converter.

This demonstrates the selected synthetic inputs and the stock consumer's state transition. It establishes no
physical identity value, FPGA register semantics, acquisition behavior or useful UI.

## Controls and snapshot diagnosis

The four width/direction controls, private positive composition and negative second-access control passed.
Both directory-flag comparisons again returned `EINVAL` for `0x10000` and succeeded for ARM64 `O_DIRECTORY`
`0x4000`. All private thread inventories were complete and correctly identified the stopped child and supervisor.

The original composite process snapshot returned zero in this run, as did the three separately recorded
command-line, process-label and maps reads. Their error outputs were empty. The snapshot verifier checked the
stock name/label, all 994 map rows, ordering, stack and expected executable APK mapping. The prior status-255
failure did not reproduce; its precise cause remains unresolved. Separate status capture and input validation
remain in the harness so a populated file cannot silently pass as a successful snapshot.

The independent post-run Kotlin verifier checked the sealed raw evidence index, admission controls and stored
certificates, installed APK/native hashes, executed observer ELF, mapping and opcode bindings, response register
checks, debug setup/readback, actual stop and application state. The ELF load bias is derived from the APK's ZIP
data offset and executable ELF segment, independently of the synthetic mapping.

## Thread coverage and preservation

Before-ready and terminal snapshots each enumerated 22 TIDs in the stock process. The main TID identified this
supervisor as its tracer; the other 21 identified no tracer. Inventories are non-atomic and siblings remained
runnable. The matching snapshots do not prove no intervening thread creation or process-wide access order.
All threads in the process may address its mapping; these captures identify supervision, not which siblings
would actually access the modeled device later.

The byte-identical APK and native library retain the pinned hashes. `system_server` remained PID 1061 across
all outer and final helper samples, final enforcement was `Enforcing`, and normal instrumentation detachment
completed. The emulator shut down and experiment ports were free. No physical instrument was accessed.

## Decision

Retain mapped-access observation and precise stops. The synchronization-compatible observer now has a stock
state witness, so deeper analysis of the identity transform is not needed to select the next step. First validate
multi-thread observation with private shared-mapping controls: existing siblings, newly created threads, a worker
mapped access, and fail-closed unknown accesses. Then admit a bounded stock continuation that reuses these two
responses and stops at the next externally unsatisfied initialization dependency. Do not add another response
until coverage and the newly observed access justify it.

The [result manifest](../../experiments/xdma-post-store/snapshot-results.toml) pins evidence and source. Reproduce
with the configured native compiler/linker and SDK, a fresh run ID and `NATIVE_POST_STORE=1`, then run
`VerifyPostStore.main.kts` on the completed capture. The unchanged observer ELF is the one built for the inventory
batch; this successor changes snapshot collection and offline verification only.
