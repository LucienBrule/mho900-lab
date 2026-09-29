# Individual option catalog in the disposable guest

This bounded extension tests the remaining individual option names through unchanged specimen-identical
Auklet. It follows the [successful FlexA persistence experiment](synthetic-entitlement-trial.md) and the
separate [D-capability comparison](specimen-d-capability-component.md). No physical scope access is involved.

## Frozen question

Can the stock ordinary installer accept each remaining individual catalog entry under one coherent
synthetic identity, preserve previous entries, and reload the combined state after a process restart and
an actual guest reboot?

The library is pinned to SHA-256
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.
The fixture uses the validated synthetic MHO984 personality and starts from the accepted FlexA seed.
The acquired unit's encrypted key and calibration files are not used.

The control submits a deliberately wrong option name in a 48-byte decoded token for BWU05T08. It must reach
the real decoder and all three consumer AES blocks, then fail original validation without changing catalog
validity or creating a new license file. Rejected-attempt private records are retained rather than treated
as an unchanged filesystem.

The positive sequence is fixed:

| Order | Option | Native type | Padded token bytes |
| ---: | --- | ---: | ---: |
| Seed | FlexA | 5 | 32 |
| 1 | BWU05T08 | 24 | 48 |
| 2 | AFG100 | 29 | 32 |
| 3 | AFG50 | 30 | 32 |
| 4 | AUDIOA | 6 | 32 |
| 5 | AUTOA | 4 | 32 |
| 6 | AEROA | 7 | 32 |
| 7 | RLU05 | 19 | 32 |
| 8 | BWU03T05 | 22 | 48 |
| 9 | BWU03T08 | 23 | 48 |

Each candidate gets one installer call. Its conclusion is sealed and committed before the next starts.
A new disposable guest may load the exact preceding successful snapshot; that lineage must remain explicit.
The final persistence arm restarts the process and reboots the same guest without regenerating tokens,
reinstalling options or formatting private state.

BND is excluded because its bundle behavior can delete individual option files. EMBD, COMP and AUTO are
already true through built-in query policy and would not provide useful installation transitions. The
expected final catalog therefore has thirteen true entries and BND false, if every candidate succeeds.

## Static predictions and limits

The recovered series-900 table contains fourteen entries. The validator accepts decoded lengths 32 or 48.
This fixture's AUDIOA and AFG100 plaintexts occupy 31 bytes, leaving exactly one NUL byte in a 32-byte token.
The bandwidth names require 48 bytes. Stock text decoding remains low-nibble-first; ordinary hexadecimal
formatting is not interchangeable with that wire representation.

BWU05T08 has an additional activation check against current bandwidth. Stock MHO984 enum 17 is predicted
to pass. The recovered ordinary option-policy targets are 14, 17 and 17 for BWU03T05, BWU03T08 and BWU05T08.
They cannot establish an ordinary enum-18 entitlement route. Actual model/raw/effective getters and explicit
stock option-policy evaluation will check that MHO984 stays at enum 17 throughout this batch.

Acceptance and queried validity do not demonstrate decoder operation, waveform generation, recording depth
or RF bandwidth. Private durability remains harness-directed stock MemFile serialization with a file-backed
guest store. The component does not run the full application lifecycle, automatic FRAM flushing or trial
expiration timers. Physical parity remains an unanswered bench question.
