# MHO900 Lab

Research harness for the RIGOL MHO900 platform, initially the MHO984.
Physical enablement is established: all ten individual ordinary options survived a normal
instrument reboot, and a separate native capability selection produced repeated 18/18
readings across deployment and an independent reboot. The signed stock APK and public
MHO984 identity remain unchanged.

**RF characterization remains outstanding.** Software capability selection does not establish
1 GHz analog performance or validate every enabled feature. The enablement experiments are
complete; the next bench objective is the prepared RF comparison. A complete emulator and
independent instrument implementation remain longer-term research.

- [Physical ordinary-option installation and persistence](docs/research/physical-ordinary-options.md)
- [Physical D-capability deployment and independent reboot](docs/research/physical-d-capability.md)
- [Current RF roadmap: preparation, arrival/integration, and measurement](docs/research/rf-response-roadmap.md)
- [RF characterization plan and remaining bench inputs](docs/research/rf-performance-evaluation-plan.md)
- [Reusable bench-tool composition proposal](docs/research/bench-tooling-composition.md)
- [Earlier guest entitlement checkpoint](docs/research/specimen-entitlement-checkpoint.md)
- [Physical logical acquisition and software identity](docs/research/physical-specimen-logical-acquisition.md)
- [Physical raw storage acquisition](docs/research/physical-specimen-raw-acquisition.md)
- [Kernel-reported SD storage classification](docs/research/physical-storage-classification.md)
- [Original Java/JNI component host](docs/research/specimen-art-component.md)
- [Ordinary option catalog and reboot persistence](docs/research/individual-option-catalog.md)
- [Separate MHO984D capability comparison](docs/research/specimen-d-capability-component.md)
- [Bounded cached-identity observation control](docs/research/cached-identity-reader.md)
- [Research draft: the consumer boundary](docs/blog/consumer-boundary.md)
- [Research draft: what survived the reboot](docs/blog/persistence-boundaries.md)

Earlier subsystem research and experiment history:

- [Whole-subsystem ADC software contract](docs/research/adc-parameter-static.md)
- [Independent ADC contract review](docs/research/adc-parameter-review.md)
- [Bulk software input capture decision](docs/research/adc-input-capture-decision.md)
- [System boundary and reconnaissance](docs/research/architecture.md)
- [External input inventory and provenance design](docs/research/provenance.md)
- [Staged emulation plan](docs/research/emulation-plan.md)
- [API-25 guest baseline and decision gate](docs/research/guest-baseline.md)
- [Scoped APK admission and startup boundary](docs/research/guest-admission.md)
- [Scoped process labeling and splash rendering](docs/research/guest-labeling.md)
- [Live stock startup and the PCIe hardware stop condition](docs/research/guest-startup.md)
- [XDMA reference comparison and negative mapping-adapter experiment](docs/research/xdma-boundary.md)
- [Independent stock mmap failure control](docs/research/xdma-syscall.md)
- [External native first mapped-register capture](docs/research/xdma-native.md)
- [Synthetic single-read comparison and three-experiment conclusion](docs/research/xdma-single-read.md)
- [Stock two-word identity composition and downstream dataflow](docs/research/xdma-identity-flow.md)
- [Two-word observation and guest single-step control finding](docs/research/xdma-two-word.md)
- [Pinned guest step profile and stock mutex retry observation](docs/research/xdma-two-word-profile.md)
- [Private exclusive-operation observer comparison](docs/research/guest-exclusive-control.md)
- [Private post-atomic execution-stop setup finding](docs/research/guest-execution-stop.md)
- [Profiled post-atomic breakpoint delivery](docs/research/guest-execution-profile.md)
- [Stock post-store observation and private inventory finding](docs/research/xdma-post-store.md)
- [ARM64 thread-inventory controls](docs/research/xdma-thread-inventory.md)
- [Stock register responses reach application state](docs/research/xdma-post-store-witness.md)
- [Private worker and new-thread observation controls](docs/research/guest-thread-control.md)
- [Bounded thread-set discovery controls](docs/research/guest-thread-discovery.md)
- [Stock stopped-thread coverage](docs/research/stock-thread-coverage.md)

Authored source and research belong here. Proprietary inputs remain outside the source tree, exposed locally through
the untracked `local/reversing/` location. Generated evidence and emulator state belong in ignored output directories.

Start repository work with `./taskctl doctor`, `./taskctl context`, and `./taskctl frontier`.
See [AGENTS.md](AGENTS.md).

New reusable Python tooling uses a typed uv workspace. See the
[workspace runbook](docs/runbooks/python-workspace.md) for installation and quality gates.
The [offline waveform boundary](packages/mho-waveform/README.md) parses preserved
ASCII voltages and qualifies explicit raw record metadata through
`mho-lab waveform inspect`; it does not contact instruments or estimate RF gain.
The [synthetic review walkthrough](docs/runbooks/synthetic-review-walkthrough.md)
reproduces accepted and rejected evidence checks without an instrument.
