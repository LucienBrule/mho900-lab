# Reusable bench tooling after physical enablement

Proposal, 2026-09-29. Physical enablement is established; RF characterization is
still open. This document selects the next software boundary to develop. It does
not implement a new bench controller or authorize further instrument operations.

The experiments now provide enough examples to compose a small toolkit. Start
with offline evidence verification, then add capture and read-only transport.
Keep mutating procedures separate and explicit. A generic runner should not infer
permission to install an option, change a native file, restart a service or reboot.

## What already exists

| Responsibility | Existing implementation | Reuse boundary |
| --- | --- | --- |
| Graceful packet-recorder termination | `tools/bench/recorder-exec.py`, `test-recorder-shutdown.py` | Owned child process, signal state, final drop counters and exit result |
| Bounded SCPI reads | `tools/bench/query-option-status.py` | Existing connected socket, exact requests, bounded responses and raw transcripts |
| One ordinary option installation | `tools/bench/install-ordinary-option.py` | Explicit pinned request; separate from read-only query transport |
| TCP transcript reconstruction | `tools/bench/verify-ordinary-install.py`, `verify-ordinary-reboot.py` | Offline packet parsing, sequence coverage, consistent retransmissions and transcript comparison |
| Reboot delivery evidence | `tools/bench/verify-d-capability.py` | One ADB request and acknowledgments; client completion and boot completion remain separate facts |
| Native observations | Fixed readers under `tools/guest/` and their independent verifiers | Exact binary profile, process/boot identity, mapping geometry and bounded byte reads |
| Storage comparison | `tools/bench/CompareRawReads.main.kts` | Exact extents and differences; no automatic atomic-snapshot claim |
| Host isolation, lease handling and orchestration | Private captured run controllers | Explicit local configuration and observations; no private endpoint or host topology in source |

The verifier chain already imports pinned predecessor modules. That is useful
provenance, but it also couples later checks to earlier experiment scripts.
Changing an old module in place could invalidate otherwise reproducible evidence.
Introduce new modules beside that chain, with an explicit version and migration
comparison. Keep the old verifiers and sealed raw evidence usable as they stand.

## Proposed components

1. **Run evidence.** A versioned TOML manifest describes relative artifact paths,
   byte counts, hashes, observation times, tool versions and declared scope.
   Preserve raw wire formats and existing external JSON evidence unchanged.
   Private configuration and unit identifiers stay in local evidence. Reject
   missing files, duplicate paths, traversal and unexpected symlink escapes.
2. **Offline transport evidence.** Packet records and TCP streams feed independent
   SCPI and ADB decoders. Report capture loss, truncation, gaps and conflicting
   retransmissions explicitly. A connection attempt with no payload is not an
   application request. Delivery acknowledgment is not proof of device action.
3. **Capture session.** Own recorder lifecycle and final statistics. A stopped
   recorder, failed cleanup or uncertain child exit is an outcome to preserve,
   not a successful run with a warning hidden in a log.
4. **Read-only transport.** Accept a configured endpoint and bounded query list;
   preserve exact bytes and deadlines. Do not scan for devices or silently retry
   a request. A supplied socket keeps host setup separate from SCPI semantics.
5. **Experiment procedures.** Compose these pieces for specific questions. Each
   procedure declares observations, allowed interventions, stop conditions and
   cleanup. Native readers remain separate fixed-profile tools rather than a
   general process-memory interface.

This preserves the useful distinction between acquisition, interpretation and
acceptance. A manifest hash proves the retained bytes match a manifest; it does
not independently establish that those bytes came from a particular instrument.
A result must identify the observations supporting that attribution.

## First bounded implementation

Build a new offline run-manifest validator and seal writer with a versioned TOML
schema and synthetic fixtures. It should accept explicit input/output paths,
perform no network or device I/O, and never overwrite an existing seal. A seal
writer records bytes; a separate validator checks them. Neither marks a task
complete or turns an actor assertion into an independent observation.

Acceptance should demonstrate:

- A valid synthetic run verifies deterministically; modifying, removing or
  truncating an artifact causes rejection.
- Duplicate paths, absolute paths, traversal and links escaping the run root are
  rejected. Unsupported schema versions fail explicitly.
- A file that changes during sealing is rejected where observable; the tool
  does not claim an atomic filesystem snapshot or eliminate all races.
- A private completed physical run can be described in a new manifest written
  outside its sealed directory, then verified without changing any original
  evidence. Existing independent verifiers still produce their original result.
- Portable source and examples contain no unit identities, private paths,
  license material or proprietary binary payloads.

Use the existing host Python environment for this first module to integrate with
the current verifiers. Keep the manifest contract language-neutral. Kotlin can
consume the same contract later; a language migration is not required to settle
artifact semantics. Fixed native observations remain C. No package-wide rewrite
or new framework is justified by this first task.

After that result, decide whether TCP reconstruction or capture-session ownership
removes the next largest source of duplication. Do not build a universal bench
orchestrator first. The smallest next reusable tool is one that can validate an
experiment's files without conducting the experiment.
