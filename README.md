# MHO900 Lab

Research harness for the RIGOL MHO900 platform, initially the MHO984.
The project is running initial guest experiments; no complete emulator or physical validation is claimed.

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

Authored source and research belong here. Proprietary inputs remain outside the source tree, exposed locally through
the untracked `local/reversing/` location. Generated evidence and emulator state belong in ignored output directories.

Start repository work with `./taskctl doctor`, `./taskctl context`, and `./taskctl frontier`.
See [AGENTS.md](AGENTS.md).
