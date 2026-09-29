# Specimen accession decision

The accession is sufficient to move the priority path into specimen-derived guest validation. The active Sparrow,
packaged Auklet, and active Web Control hashes equal official `.26`; the previously studied binary implementation is
therefore the right one. The inactive `/rigol` and `/system` application copies remain separate provenance inputs.
No port to an unknown active Auklet build is needed.

Two independent full reads of the observed SD user area are preserved. Whole-device equality did not occur, but
all differences are confined to userdata; every byte elsewhere, including `/rigol`, is identical. This is a useful
live acquisition with explicit consistency limits, not a quiesced factory snapshot or demonstrated restore image.
A third live read would have low information value merely to chase a matching whole-image hash. Neither acquired
image will be repaired, mounted writable, or substituted for the other.

The kernel's SD classification replaces the earlier eMMC assumption. The raw target and size were correct, and the
read-only acquisition method remains valid. Future board-image boot work must reconcile the actual storage and
partition presentation. It is not a prerequisite for tests of the byte-identical active applications.

## Next bounded batch

1. Recover the ordinary installer/query boundary and its state dependencies from stock code and preserved unit files.
   Identify entry points, option identifiers, argument/results, persistence, required initialization and identity
   inputs.
2. Establish a disposable guest baseline using copied specimen state and the existing harness. Test one bounded
   ordinary interface without applying options or a capability redirect. Preserve actual state, file deltas, synthetic
   inputs and the first unresolved dependency.
3. Evaluate whether that baseline supports an ordinary installer/persistence trial. Admit that experiment only when
   the evidence supplies its prerequisites, or admit one bounded environment correction instead.

This ordering prioritizes the user's accession/entitlement path. It avoids making remaining AFE initialization work
or full RK3399 image boot a speculative prerequisite. It also avoids treating a successful license parser return as
proof of a valid installation, persistence, or a fully initialized application. Any physical observation needed to
resolve a genuine guest dependency will be recorded as an exact bench question.

Ordinary entitlement handling, the separate guest D-capability experiment, full board-image boot, and physical
mutations remain distinct. No physical option installation, capability change, reboot or new management request is
part of this successor batch. The specimen remains at the isolated bench checkpoint after acquisition.

## Evidence

- [Logical acquisition and exact active application hashes](physical-specimen-logical-acquisition.md).
- [Complete raw reads, differences, capture quality and host restoration](physical-specimen-raw-acquisition.md).
- [Storage classification correction](physical-storage-classification.md).
- `experiments/physical-first-contact/specimen-logical.toml` and `specimen-raw-results.toml` pin private manifests.

The storage-class change was reconciled through taskctl before this decision. Results and successor tasking are
committed and pushed before execution. Proprietary bytes, unit identifiers, calibration data and key/license content
remain in the private evidence area.
