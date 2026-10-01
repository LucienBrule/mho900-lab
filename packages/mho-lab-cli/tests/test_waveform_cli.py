"""Offline CLI/delegate qualification, typed failures and structural disclosure controls."""

import os
import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

from mho_lab_cli.cli import main
from mho_lab_cli.waveform_delegate import (
    WaveformInputRejected,
    WaveformInspectionRequest,
    inspect_waveform,
)
from mho_waveform import RawAcquisition, RawQualified

PREAMBLE = b"2,2,3,1,2.5e-10,-1e-6,0,6e-6,0,32768\n"


def request(directory: Path, preamble: bytes = PREAMBLE) -> WaveformInspectionRequest:
    before = directory / "before.txt"
    data = directory / "data.txt"
    after = directory / "after.txt"
    before.write_bytes(preamble)
    data.write_bytes(b".125,-.25,.003\n")
    after.write_bytes(preamble)
    return WaveformInspectionRequest(
        preamble_before=before,
        waveform=data,
        preamble_after=after,
        acquisition=RawAcquisition(actual_sample_rate_hz=4e9, memory_points=3, start=1, stop=3),
    )


def arguments(source: WaveformInspectionRequest) -> list[str]:
    return [
        "waveform",
        "inspect",
        "--preamble-before",
        str(source.preamble_before),
        "--data",
        str(source.waveform),
        "--preamble-after",
        str(source.preamble_after),
        "--actual-rate-hz",
        "4000000000",
        "--memory-points",
        "3",
        "--start",
        "1",
        "--stop",
        "3",
    ]


def test_cli_and_delegate_agree_without_sample_or_path_disclosure(tmp_path: Path) -> None:
    source = request(tmp_path)
    delegated = inspect_waveform(source)
    assert isinstance(delegated, RawQualified)
    result = CliRunner().invoke(main, arguments(source))
    assert result.exit_code == 0, result.output
    document = tomllib.loads(result.output)
    assert document["result"] == "accepted"
    assert document["points"] == 3
    assert document["waveform_sha256"] == delegated.waveform.evidence.waveform_sha256
    assert document["ascii_volts_rescaled"] is False
    assert document["voltage_max_v"] == 0.125
    assert document["voltage_min_v"] == -0.25
    assert document["physical_origin_proven"] is False
    assert document["calibrated_rf_gain_proven"] is False
    assert str(tmp_path) not in result.output
    assert document["record_duration_s"] == pytest.approx(7.5e-10)
    assert document["first_to_last_span_s"] == pytest.approx(5e-10)


def test_display_export_is_a_toml_rejection(tmp_path: Path) -> None:
    source = request(tmp_path, PREAMBLE.replace(b"2,2,3", b"2,0,3"))
    result = CliRunner().invoke(main, arguments(source))
    assert result.exit_code == 1
    document = tomllib.loads(result.output)
    assert document["result"] == "rejected"
    assert document["code"] == "not-raw"


@pytest.mark.parametrize("rate", ["0", "nan", "inf", "9.9e37"])
def test_invalid_observations_are_typed_toml_before_file_io(tmp_path: Path, rate: str) -> None:
    source = request(tmp_path)
    command = arguments(source)
    command[command.index("4000000000")] = rate
    source.waveform.unlink()
    result = CliRunner().invoke(main, command)
    assert result.exit_code == 1
    document = tomllib.loads(result.output)
    assert document["code"] == "invalid-contract"
    assert str(tmp_path) not in result.output


@pytest.mark.parametrize("kind", ["missing", "symlink", "fifo", "oversized"])
def test_files_are_bounded_regular_and_do_not_leak_paths(tmp_path: Path, kind: str) -> None:
    source = request(tmp_path)
    source.waveform.unlink()
    if kind == "symlink":
        source.waveform.symlink_to(source.preamble_before)
    elif kind == "fifo":
        os.mkfifo(source.waveform)
    elif kind == "oversized":
        with source.waveform.open("wb") as stream:
            stream.truncate(source.limits.max_waveform_bytes + 1)
    delegated = inspect_waveform(source)
    assert isinstance(delegated, WaveformInputRejected)
    result = CliRunner().invoke(main, arguments(source))
    assert result.exit_code == 1
    document = tomllib.loads(result.output)
    assert document["code"] == "input-files"
    assert str(tmp_path) not in result.output


def test_unknown_numeric_payload_is_not_rendered_on_failure(tmp_path: Path) -> None:
    source = request(tmp_path)
    source.waveform.write_bytes(b"PRIVATE-PAYLOAD,.2,.3\n")
    result = CliRunner().invoke(main, arguments(source))
    assert result.exit_code == 1
    document = tomllib.loads(result.output)
    assert document["code"] == "numeric-token"
    assert document["token_index"] == 0
    assert "PRIVATE-PAYLOAD" not in result.output


def test_delegate_revalidates_unchecked_request_before_reading(tmp_path: Path) -> None:
    source = request(tmp_path)
    unchecked = source.model_copy(update={"limits": None})
    result = inspect_waveform(unchecked)
    assert isinstance(result, WaveformInputRejected)
    assert result.message == "inspection request violates the contract"
