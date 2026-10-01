# Synthetic RAW AC statistics example

Run from the repository root, choosing a new output directory:

```sh
uv sync --locked --all-packages
uv run --locked python examples/raw-ac-statistics/walkthrough.py out/rf/raw-ac-example-01
```

The script uses only Python's standard library and invokes the public CLI module
with the current Python executable in isolated mode (`-I -m mho_lab_cli`).
An installed consumer can run the same script with `python -I` in its
environment, without uv. It makes no instrument, socket or network calls.
Both waveform records are manufactured by the tracked script; no private physical
dataset is read. Existing output directories are refused, and failures retain
their evidence.

The script generates original ASCII voltages and matching before/after RAW
preambles, invokes `rf raw-ac-inspect` and `rf receive-inspect`, and checks the
expected exits, selected named fields and all three input hashes. It retains the
complete TOML receipts and stderr separately. The generated `verification.toml`
contains the script digest, waveform digests, expected quantities and checked
statuses. [expected.toml](expected.toml) provides the authored numerical reference.
The selected-field check in the walkthrough is not a full receipt-schema validator.

It prints each command and its actual and expected exit status separately from
the preserved TOML stdout. The weak sine has 1 mV peak AC and 10 mV DC;
the constant record has 10 mV DC and
exactly zero sampled AC. Both have valid supplied RAW statistics. Both fail the
default receive profile's 5 mV minimum Vpp. These are expected receive rejections,
with exit status 1; an unexpected status or metric stops the script.

See the [walkthrough](../../docs/runbooks/raw-ac-statistics-walkthrough.md) for the
formula, individual commands, receipt fields and limits on interpretation.
