"""Generate synthetic RAW volts and compare two public offline CLI endpoints."""

from __future__ import annotations

import argparse
import hashlib
import math
import shlex
import subprocess
import sys
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

POINTS = 100_000
PREAMBLE = b"2,2,100000,1,2.500000E-10,-1.250000E-5,0,6.6667E-06,0,32768\n"


@dataclass(frozen=True)
class SyntheticCase:
    name: str
    sine_peak_v: float
    dc_v: float
    expected_ac_rms_v: float
    expected_vpp_v: float
    constant_samples: bool


CASES = (
    SyntheticCase("weak-sine", 0.001, 0.01, 0.001 / math.sqrt(2), 0.002, False),
    SyntheticCase("constant-dc", 0.0, 0.01, 0.0, 0.0, True),
)


@dataclass(frozen=True)
class StatisticsProjection:
    dc_mean_v: float
    voltage_min_v: float
    voltage_max_v: float
    voltage_vpp_v: float
    ac_rms_v: float
    constant_samples: bool
    zero_sampled_ac: bool


def table(value: object) -> Mapping[str, object]:
    """Narrow a TOML table before inspecting its named scalar fields."""
    if not isinstance(value, dict):
        raise ValueError("expected TOML table")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError("expected string TOML key")
        result[key] = item
    return result


def number(values: Mapping[str, object], name: str) -> float:
    value = values[name]
    if not isinstance(value, float) or not math.isfinite(value):
        raise ValueError(f"expected finite float: {name}")
    return value


def boolean(values: Mapping[str, object], name: str) -> bool:
    value = values[name]
    if not isinstance(value, bool):
        raise ValueError(f"expected Boolean: {name}")
    return value


def projection(receipt: Mapping[str, object]) -> StatisticsProjection:
    metrics = table(receipt["metrics"])
    return StatisticsProjection(
        dc_mean_v=number(metrics, "dc_mean_v"),
        voltage_min_v=number(metrics, "voltage_min_v"),
        voltage_max_v=number(metrics, "voltage_max_v"),
        voltage_vpp_v=number(metrics, "voltage_vpp_v"),
        ac_rms_v=number(metrics, "ac_rms_v"),
        constant_samples=boolean(metrics, "constant_samples"),
        zero_sampled_ac=boolean(metrics, "zero_sampled_ac"),
    )


def run_cli(arguments: tuple[str, ...], output: Path, expected_status: int) -> Mapping[str, object]:
    command = (sys.executable, "-I", "-m", "mho_lab_cli", "rf", *arguments)
    print(f"Command: {shlex.join(command)}", flush=True)
    result = subprocess.run(command, capture_output=True, check=False)
    output.write_bytes(result.stdout)
    output.with_suffix(".stderr.txt").write_bytes(result.stderr)
    print(f"Exit status: {result.returncode}; expected: {expected_status}", flush=True)
    if result.returncode != expected_status:
        raise ValueError(f"unexpected CLI status {result.returncode}; expected {expected_status}")
    loaded: object = tomllib.loads(result.stdout.decode("utf-8"))
    return table(loaded)


def close(actual: float, expected: float) -> None:
    if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=2e-15):
        raise ValueError(f"unexpected metric: {actual!r}; expected {expected!r}")


def generate(case: SyntheticCase, directory: Path) -> bytes:
    directory.mkdir()
    # 975 MHz / 4 GHz = 39/160; modular phases avoid accumulating phase drift.
    # 100000 samples contain exactly 625 periods of the 160-sample sequence.
    samples = (
        case.dc_v + case.sine_peak_v * math.sin(math.tau * ((39 * index) % 160) / 160)
        for index in range(POINTS)
    )
    waveform = (",".join(f"{sample:+.17e}" for sample in samples) + "\n").encode("ascii")
    (directory / "preamble-before.txt").write_bytes(PREAMBLE)
    (directory / "waveform-ascii.txt").write_bytes(waveform)
    (directory / "preamble-after.txt").write_bytes(PREAMBLE)
    return waveform


def inspect(case: SyntheticCase, directory: Path, waveform: bytes) -> str:
    arguments = (
        "--preamble-before",
        str(directory / "preamble-before.txt"),
        "--data",
        str(directory / "waveform-ascii.txt"),
        "--preamble-after",
        str(directory / "preamble-after.txt"),
        "--actual-rate-hz",
        "4000000000",
        "--memory-points",
        str(POINTS),
        "--start",
        "1",
        "--stop",
        str(POINTS),
    )
    statistics = run_cli(("raw-ac-inspect", *arguments), directory / "statistics.toml", 0)
    receive = run_cli(
        ("receive-inspect", *arguments, "--command-frequency-hz", "975000000"),
        directory / "receive.toml",
        1,
    )
    if statistics["schema_version"] != "mho-rf.raw-ac-inspection/1":
        raise ValueError("unexpected statistics schema")
    if statistics["result"] != "raw-ac-statistics":
        raise ValueError("statistics did not accept supplied RAW record")
    if statistics["method"] != "unwindowed-demeaned-population":
        raise ValueError("unexpected statistics method")
    if receive["result"] != "receive-rejected" or receive["stage"] != "range":
        raise ValueError("expected a receive range rejection")
    if receive["code"] != "vpp-range":
        raise ValueError("expected receive Vpp rejection")
    for receipt in (statistics, receive):
        if receipt["waveform_sha256"] != hashlib.sha256(waveform).hexdigest():
            raise ValueError("receipt does not identify original waveform bytes")
        for field in ("preamble_before_sha256", "preamble_after_sha256"):
            if receipt[field] != hashlib.sha256(PREAMBLE).hexdigest():
                raise ValueError("receipt does not identify original preamble bytes")
        for field in ("physical_origin_proven", "calibrated_amplitude_proven"):
            if boolean(receipt, field):
                raise ValueError("synthetic receipt claims physical proof")
    if boolean(statistics, "receive_qualification_proven"):
        raise ValueError("statistics receipt claims receive qualification")
    metrics = projection(statistics)
    close(metrics.dc_mean_v, case.dc_v)
    close(metrics.voltage_min_v, case.dc_v - case.sine_peak_v)
    close(metrics.voltage_max_v, case.dc_v + case.sine_peak_v)
    close(metrics.voltage_vpp_v, case.expected_vpp_v)
    close(metrics.ac_rms_v, case.expected_ac_rms_v)
    if metrics.constant_samples != case.constant_samples:
        raise ValueError("unexpected exact-constant classification")
    if metrics.zero_sampled_ac != case.constant_samples:
        raise ValueError("unexpected zero sampled AC classification")
    if case.constant_samples and metrics.ac_rms_v != 0.0:
        raise ValueError("constant samples must have exactly zero AC RMS")
    geometry = table(statistics["geometry"])
    if geometry["points"] != POINTS or geometry["memory_points"] != POINTS:
        raise ValueError("unexpected retained point count or observed memory")
    if geometry["start"] != 1 or geometry["stop"] != POINTS:
        raise ValueError("unexpected retained extent")
    close(number(geometry, "record_duration_s"), 0.000025)
    close(number(geometry, "first_to_last_span_s"), (POINTS - 1) / 4e9)
    # Complete CLI receipts are retained. This walkthrough checks selected semantic
    # fields and original hashes; it is not a replacement for a strict schema parser.
    return (
        "[[cases]]\n"
        f'name = "{case.name}"\n'
        f'waveform_sha256 = "{hashlib.sha256(waveform).hexdigest()}"\n'
        f"expected_dc_mean_v = {case.dc_v!r}\n"
        f"expected_ac_rms_v = {case.expected_ac_rms_v!r}\n"
        f"expected_vpp_v = {case.expected_vpp_v!r}\n"
        'statistics_result = "raw-ac-statistics"\n'
        'receive_result = "receive-rejected"\n'
        'receive_stage = "range"\nreceive_code = "vpp-range"\n'
        "statistics_exit_status = 0\nreceive_exit_status = 1\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        type=Path,
        help="new output directory; existing paths are refused",
    )
    arguments = parser.parse_args()
    argument_output: object = arguments.output
    if not isinstance(argument_output, Path):
        raise ValueError("output must be a path")
    output = argument_output
    output.mkdir(parents=True, exist_ok=False)
    sections: list[str] = []
    for case in CASES:
        directory = output / case.name
        waveform = generate(case, directory)
        sections.append(inspect(case, directory, waveform))
        print(f"[ok] {case.name}: RAW statistics accepted; receive Vpp rejection expected")
    header = (
        'schema_version = "mho-rf.synthetic-ac-walkthrough/1"\n'
        "synthetic = true\nphysical_origin_proven = false\n"
        f'walkthrough_source_sha256 = "{hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}"\n'
        "metric_relative_tolerance = 1e-12\nmetric_absolute_tolerance_v = 2e-15\n\n"
    )
    (output / "verification.toml").write_text(header + "\n".join(sections), encoding="utf-8")


if __name__ == "__main__":
    main()
