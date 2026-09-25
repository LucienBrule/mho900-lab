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

Authored source and research belong here. Proprietary inputs remain outside the source tree, exposed locally through
the untracked `local/reversing/` location. Generated evidence and emulator state belong in ignored output directories.

Start repository work with `./taskctl doctor`, `./taskctl context`, and `./taskctl frontier`.
See [AGENTS.md](AGENTS.md).
