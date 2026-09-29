# Specimen-derived entitlement research handoff

> Later checkpoint: [acquired-input FlexA persistence](acquired-option-persistence.md)
> and the [acquired-input stock/D capability comparison](acquired-capability-comparison.md)
> now pass. The cached-identity question below was subsequently resolved in
> [physical cached-identity evidence](physical-apk-cached-identity.md).
> The remaining physical parity question is the complete untouched option and
> capability baseline. The original overnight report below remains historical.


2026-09-29. All work in this overnight program used preserved files and disposable ARM64 guests.
No physical instrument connection, command, lease renewal or mutation occurred during the program.

The main result is established: unchanged specimen-identical Auklet accepts all ten tested individual
ordinary options under a coherent synthetic identity, and reloads the combined state after both a fresh
process and an actual guest reboot. The separate derived capability experiment preserves public MHO984
identity while selecting the MHO984D record and bandwidth enum 18.

## What the guest actually runs

The [acquired APK and native library](physical-specimen-logical-acquisition.md) match the analyzed official
`.26` bytes. The APK SHA-256 is
`6a08d97ff903e97c1c99792b69eef9b0a3bec0b43fe348e4af93861673bbec6b`; Auklet is
`4e7eb0bb81b6bcc6923ceff75fd259d41be555dccc6867e53ed7ee2ea3b2894e`.

The [ART component host](specimen-art-component.md) loads the original Java API and JNI initialization,
constructs the original 49-service factory and invokes the stock license consumer. This is a component
experiment, not a complete Sparrow UI or a boot of the physical factory image. Hardware identity is
explicitly synthetic. Acquired unit keys and calibration assets were not used in the option experiments.

## Ordinary option state and persistence

| Catalog entries | Clean baseline | After their installs | Final process reload | Final guest reboot |
| --- | --- | --- | --- | --- |
| EMBD, COMP, AUTO | True through built-in policy | True | True | True |
| FlexA, AUDIOA, AUTOA, AEROA | False | True | True | True |
| AFG50, AFG100, RLU05 | False | True | True | True |
| BWU03T05, BWU03T08, BWU05T08 | False | True | True | True |
| BND | False | Not exercised | False | False |

The final fourteen-entry catalog therefore has thirteen true entries. Ten are installed individual
licenses; three are built-in query cases. BND was excluded because bundle behavior can remove individual
license files. Each candidate was tested once and its conclusion committed before the next.

The final install/process/reboot phases retain exactly the same ten license files, Key.data, ten crypto
witnesses and canonical private stream: 22 files. The guest boot identity changed. Reloads made no installer
or token-producer calls and the stock consumer revalidated every installed individual token.
See the [catalog report](individual-option-catalog.md) and
[per-run hashes](../../experiments/specimen-entitlement/catalog-results.toml).

Guest changes consisted of the declared synthetic identity/key fixture, stock-written license files and
harness-directed persistence of the stock MemFile representation to ordinary guest files. Stock parsing and
serialization execute; automatic physical FRAM flushing, trial timers and power-loss recovery do not.
Thus persistence works for this component/store model. It does not yet prove physical installation durability.

## Separate D-capability result

The [derived-copy experiment](specimen-d-capability-component.md) changes 27 bytes inside one 32-byte span.
The original APK and library remain immutable. Across its initial, process-reload and guest-reboot phases:

- public identity remains MHO984;
- selected capability record changes from MHO984 to MHO984D;
- raw and effective bandwidth enums remain 18 before and after original option-policy evaluation;
- the previously accepted FlexA seed and its files remain unchanged.

Enum 18 is labeled BW_1G in the software. No 1 GHz analog response, calibration suitability, AFE operation
or physical deployment has been demonstrated. The three ordinary bandwidth options retained enum 17 on
stock MHO984; no ordinary enum-18 entitlement route was found. The D arm used the FlexA seed, not the final
ten-license catalog, so the combined all-options/D configuration is not a demonstrated result.

## Useful failures and the next bench question

The first token producer passed its own crypto roundtrip while the real consumer rejected it. Capturing
stock decoder input/output exposed low-nibble-first text encoding. Corrected positive and wrong-name
negative fixtures then separated software acceptance from a producer's internal consistency.
The [complete trial history](synthetic-entitlement-trial.md) retains those failures.

A [bounded cached-identity reader](cached-identity-reader.md) now has a validated guest observation:
two independent 24-byte samples, 48 bytes total, after setup detaches. Earlier failures exposed lingering
code-page permissions and a separate read-only whole-file mapping. The final controller succeeded; its
original runner status remains failed because the frozen verifier pinned the old reader build. A separately
preserved offline audit of the new admitted build accepted the existing evidence. No guest rerun was used
to erase that verification defect.

The highest-value next physical question is:

> What cached eight-byte DNA and sixteen-byte derived file-key values does the already initialized stock
> Sparrow process hold, and do they explain the acquired Key.data when evaluated offline?

The proposed read requires renewed authorization, including temporary helper/output staging, existing
credentials, a fresh isolated capture and exact process/file/map checks. It must stop on permission denial.
No initialization call, register read, attachment, daemon restart or policy change is proposed. A guest pass
establishes the method, not physical permissions or the specimen's values.

Initialized private/FRAM records and physical option-query state remain separate gaps. Missing `.lic` files
in the acquired archives cannot establish that every option is unavailable. Likewise, the two prior live
storage images preserve the kernel-reported [SD medium](physical-storage-classification.md), not external
FRAM or application RAM; they differ within userdata and are not identical frozen restore images.

Further startup/MMIO/ADC work and full-image boot attempts have lower immediate value for this entitlement
question. Resolve specimen identity coherence, reconstruct its actual state in the guest, then evaluate a
separately authorized physical procedure. Physical feature operation and RF characterization remain later
experiments with their own evidence requirements.
