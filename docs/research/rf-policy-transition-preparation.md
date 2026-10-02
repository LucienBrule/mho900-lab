# Matched-policy controller preparation

2026-10-01. Offline preparation for `TASK.rf.policy-comparison-preparation`.
The controller and supplied-record reduction are prepared; this report records
controls, not a physical rollback or a comparative RF result. The
[numerical contract](../../experiments/rf-policy-comparison/contract.toml) and
[numerical preparation](rf-policy-comparison-preparation.md) remain separate
from the physical [execution gate](rf-policy-comparison-readiness.md).

The experiment retains an initial verified stock rollback, then A1 stock,
B derived and A2 stock. Each arm has five records at each of 100, 800, 975,
1000 and 100 MHz. One normal reboot follows each native-file transition;
more than 1800 seconds of serviced warm-up follows each reboot. The final
software state is stock. The source ends at 100 MHz with the same raw output
code, and ordinary scope/export/RUN settings are restored while their state
and transports remain established.

## Transition evidence and controls

The healthy-transition adapter replaces the earlier recovery-only rollback
branch. Before any file mutation it requires fresh package selection, signed
APK, native-file hash and ownership, mapped-library geometry, boot/process
identity, option state, protected logical content and repeated policy samples.
Rollback removes only the independently hash-matched introduced standalone
file, with preserved original-absence ancestry and durable removal intent.
Deployment retains the exact approved derived bytes and the established
temporary-copy, readback, ownership, mode and atomic-rename procedure.

Each policy observation uses the unchanged helper's four fixed four-byte reads,
retained as two eight-byte samples: 16 bytes per observation. A successful
transition has a prechange and a post-warm-up observation, totaling 32 bytes.
Independent original-byte inspection checks APK member placement, ELF load
geometry, all four observer epochs, selected backing file and expected 17/17
stock or 18/18 derived cached enums. Historical inputs used in offline controls
remain historical; they do not establish a fresh physical arm.

Visible UI acceptance binds a new screenshot to its hash, PID, process start
time, boot ID, phase and acceptance time. The controller refreshes process and
logical state immediately before mutation. Reboot delivery occurs once outside
reconnection loops. Ambiguous delivery stops without retransmission. Postboot
readiness requires a changed boot ID, a fresh captured isolated six-hour lease,
normal UI, unchanged protected content and stable post-warm-up state. One
bounded adbd restart is permitted only if needed for the established observer;
there is no remount, calibration or host-policy change.

Initial-stock, derived and final-stock stages require at least 7200, 4800 and
2400 seconds remaining respectively. These reserves cover the remaining arm
sequence and cleanup, rather than only the next command. A preparation result
does not waive them or authorize beginning a partial comparison too late.

The transition controls passed 70 cases. They exercise altered source and
inventory, symlinks, UI identity/time/hash, process and mapping changes,
deadline and warm-up boundaries, capture/lease failures, no-retry reboot
behavior and shutdown preservation. An independent suite separately exercises
original-byte mapping, policy-sample, ownership and protected-data failures.

## Lease and acquisition handoff

The initial lease proof uses the latest sealed bench capture, not an expired
deployment log. A typed claim binds the exact predecessor manifest and PCAP.
A separate streaming decoder requires the captured matching DHCP REQUEST and
ACK, the intended client/server identities, a six-hour lease and isolated /30
subnet, with no gateway, DNS, boot server or relay. It rejects a subsequent
RELEASE or DECLINE. Original TOML and JSONL recorder histories are interpreted
through explicit separate adapters; neither history is rewritten.

Preparation review found that the TOML adapter accepted an explicit failure
event alongside graceful recorder termination. Both adapters now reject the
same failure events, with retained negative controls. Capture decoding has a
512 MiB extent limit and at most 262144 bytes per frame. Exact original capture
statistics and normalized signal records remain bound to the seal. A recorded
graceful exit and zero reported drops do not prove whole-wire completeness.

The acquisition adapter copies pinned dependencies and freezes its complete
control inventory, including the prior lease. It refuses a second freeze
before changing any frozen input. An accepted arm receipt binds reviewed
transition evidence and preserved file hashes; it is explicitly an actor
acceptance, not an independent proof of arbitrary supplied mapping rows.

Fresh metadata checks bracket acquisition and follow ordinary restoration.
They compare PID, start time, boot ID, selected-library rows and all signed-APK
mapping rows. Review found and fixed a case where an added embedded stock
executable view could otherwise escape the B-arm metadata check. These reads
are sequential metadata observations; they are not atomic snapshots or hidden
DSP telemetry.

Before acquisition changes ordinary settings, fresh SCPI readbacks require CH1
alone, volts, 50-ohm DC, 1× probe, zero offset, ordinary limit OFF, normal
acquisition, 500 mV/div, 10 ns/div and actual 4 GSa/s. Measurement readbacks
then require 50 mV/div, 1 us/div, 100000-point RAW geometry and 4 GSa/s. Every
record preserves its original preambles and voltage bytes, arm/visit/repeat,
query sequence, unchanged default receive receipt and experiment eligibility
receipt. Five source commands implement the fixed five visits; failed slots
are retained rather than replaced. The acquisition preparation passed 22
controls, including frozen-input and borrowed-mapping failures.

The directory reducer accepts three explicit preserved arm roots. It requalifies
original bytes, checks complete receipt values and scalar types, validates the
fixed directory schedule and slot metadata, and checks input inventories and
hashes after reduction. Symlinked roots or directory parents reject. Missing
records remain missing slots; they do not become synthetic supplied records.
TOML and CSV retain group statistics, ten return controls, 50 primary pairs and
100 secondary pairs when structurally valid. Its physical-association and
acquisition-freshness claims remain false.

All 18 directory-reduction controls passed. A complete manufactured matched-sine
fixture supplies 75 eligible records, 15 groups, ten passing return controls,
50 primary and 100 secondary pairs, with independently checked CSV row counts.
Equal simulated arms correctly produce an unresolved contrast. Negative controls
retain missing arms, extra slots, malformed or changed bytes, wrong metadata,
receipt mismatch, symlink traversal and output-overwrite refusal. This fixture
is explicitly synthetic and supplies no physical arm or RF evidence.

## Provenance and limits

The new preparation, configuration, eligibility, decision, metadata and reduction
code passed strict type, lint and formatting checks. Retained legacy executor
callbacks are explicitly outside that strict typing claim. The signed APK,
stock native member, original observers and public receive/statistics modules
remain unchanged. Local run configuration and unit-specific material stay in
ignored evidence areas.

| Evidence | Preserved manifest SHA-256 |
| --- | --- |
| Numerical controls and archived-file witness | `27305259dc6fff315400cbcfb4113ee091b3aa69c514d3c280f9a98b5e80b612` |
| Independent numerical and original-byte transition review | `d50b76b534407803c3b2ccfd9dfb2b2c6d14b820421a575d63ba9be1e30cad86` |
| Final healthy-transition controller and streaming lease proof | `6c701e331e847ebe9e77c38acab2141152159f381abdec964072af6c2f82dfec` |
| Acquisition preparation and quality controls | `b99ce7de9132137d203261b9ded5568ddb3a0d99bdad77927cafc85e2d7f62de` |
| Independent acquisition and lease follow-up | `3f8cb8de02088ceda342be5cf9f4d6fc97f546b17c62e2c9068081387f542bcc` |
| Independent final preparation-freeze review | `a38316d8be2862abd58cff65d6949f909698abd24c276d6015b23c176ebeec18` |
| Directory reducer and full synthetic fixture | `e80054b20769effbba5c22e6ba6ef1d32068fcda1de12e433deffc8a70c00186` |

The numerical and reducer inventories use a separate authored evidence format;
the other rows use the native recursive-regular-file manifest. Negative symlink
controls preserve link metadata without treating linked targets as regular
evidence. Format distinctions remain explicit rather than claiming that every
inventory passed the same verifier.
The reducer inventory binds 1037 entries, including 13 link-text entries.
Independent rehashing verifies every bound entry and records the two unbound
generated Python bytecode files separately. Bytecode caches are not included
in its source/output preservation claim or copied into prepared controllers.

These receipts support preparation. Physical rollback, the comparison and RF
determination remain open. Loaded cached-policy enums identify the software
arm; they do not independently establish CH1's effective internal driver enum,
AFE tuple consumption, DSP path or calibrated fundamental amplitude. A future
positive sampled contrast must retain those limits. Absolute 1 GHz bandwidth
still needs a characterized source and reference-plane measurement.
