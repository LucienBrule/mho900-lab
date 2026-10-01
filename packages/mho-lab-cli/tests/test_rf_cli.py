"""Offline RF endpoint/delegate agreement, failures and no private path/sample disclosure."""

import hashlib
import math
import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

from mho_lab_cli.cli import main
from mho_lab_cli.rf_delegate import ReceiveInspectionRequest, inspect_receive
from mho_rf import ReceiveQualified, ReceiveRejected, profile_hash
from mho_waveform import RawAcquisition

POINTS = 100_000
PREAMBLE = b"2,2,100000,1,2.5e-10,0,0,6e-6,0,32768\n"


def source(directory: Path, frequency: float = 600e6) -> ReceiveInspectionRequest:
    before, data, after = directory / "before.txt", directory / "data.txt", directory / "after.txt"
    before.write_bytes(PREAMBLE)
    after.write_bytes(PREAMBLE)
    data.write_text(
        ",".join(
            f"{0.12 * math.sin(2 * math.pi * frequency * n / 4e9):.16e}" for n in range(POINTS)
        )
        + "\n"
    )
    return ReceiveInspectionRequest(
        preamble_before=before,
        waveform=data,
        preamble_after=after,
        command_frequency_hz=600e6,
        acquisition=RawAcquisition(
            actual_sample_rate_hz=4e9, memory_points=POINTS, start=1, stop=POINTS
        ),
    )


def arguments(request: ReceiveInspectionRequest) -> list[str]:
    return [
        "rf",
        "receive-inspect",
        "--preamble-before",
        str(request.preamble_before),
        "--data",
        str(request.waveform),
        "--preamble-after",
        str(request.preamble_after),
        "--actual-rate-hz",
        "4000000000",
        "--memory-points",
        "100000",
        "--start",
        "1",
        "--stop",
        "100000",
        "--command-frequency-hz",
        "600000000",
    ]


def test_cli_qualified_schema_library_agreement_and_disclosure(tmp_path: Path) -> None:
    request = source(tmp_path)
    library = inspect_receive(request)
    assert isinstance(library, ReceiveQualified)
    result = CliRunner().invoke(main, arguments(request))
    assert result.exit_code == 0, result.output
    document = tomllib.loads(result.output)
    assert document["schema_version"] == "mho-rf.receive-inspection/1"
    assert document["result"] == "receive-qualified"
    assert document["selected_peak_frequency_hz"] == library.spectrum.selected_peak_frequency_hz
    assert document["global_peak_frequency_hz"] == library.spectrum.global_peak_frequency_hz
    assert document["energy_fraction"] == library.spectrum.energy_fraction
    assert document["profile_sha256"] == profile_hash(library.profile)
    assert document["waveform_sha256"] == hashlib.sha256(request.waveform.read_bytes()).hexdigest()
    assert document["profile"]["peak_tie_relative_tolerance"] == 1e-12
    assert document["input"]["points"] == POINTS
    assert document["physical_origin_proven"] is False
    assert document["calibrated_amplitude_proven"] is False
    assert document["final_fit_validity_proven"] is False
    assert str(tmp_path) not in result.output
    assert "volts =" not in result.output


def test_receive_rejection_retains_computed_spectrum(tmp_path: Path) -> None:
    request = source(tmp_path, 571.43e6)
    delegated = inspect_receive(request)
    assert isinstance(delegated, ReceiveRejected)
    assert delegated.spectrum is not None
    result = CliRunner().invoke(main, arguments(request))
    assert result.exit_code == 1
    document = tomllib.loads(result.output)
    assert document["result"] == "receive-rejected"
    assert document["code"] == "band-peak-frequency"
    assert document["selected_peak_frequency_hz"] == delegated.spectrum.selected_peak_frequency_hz
    assert document["energy_fraction"] == delegated.spectrum.energy_fraction
    assert str(tmp_path) not in result.output


@pytest.mark.parametrize("case", ["display", "truncated", "changed-preamble", "nonfinite"])
def test_malformed_raw_record_cannot_be_received(tmp_path: Path, case: str) -> None:
    request = source(tmp_path)
    if case == "display":
        request.preamble_before.write_bytes(PREAMBLE.replace(b"2,2,", b"2,0,"))
        request.preamble_after.write_bytes(request.preamble_before.read_bytes())
    elif case == "truncated":
        request.waveform.write_bytes(request.waveform.read_bytes()[:-10])
    elif case == "changed-preamble":
        request.preamble_after.write_bytes(PREAMBLE.replace(b"32768", b"32769"))
    else:
        request.waveform.write_bytes(
            b"PRIVATE-NONFINITE," + request.waveform.read_bytes().split(b",", 1)[1]
        )
    result = CliRunner().invoke(main, arguments(request))
    assert result.exit_code == 1
    document = tomllib.loads(result.output)
    assert document["result"] == "receive-rejected"
    assert "selected_peak_frequency_hz" not in document
    assert document["profile_sha256"] == profile_hash(request.profile)
    assert document["waveform_sha256"] == hashlib.sha256(request.waveform.read_bytes()).hexdigest()
    assert "PRIVATE-NONFINITE" not in result.output
    assert str(tmp_path) not in result.output


@pytest.mark.parametrize("value", ["0", "nan", "inf"])
def test_invalid_command_rejected_before_file_reads(tmp_path: Path, value: str) -> None:
    request = source(tmp_path)
    command = arguments(request)
    command[-1] = value
    request.waveform.unlink()
    result = CliRunner().invoke(main, command)
    assert result.exit_code == 1
    document = tomllib.loads(result.output)
    assert document["code"] == "invalid-contract"


def test_delegate_revalidates_unchecked_profile_before_file_reads(tmp_path: Path) -> None:
    request = source(tmp_path)
    request.waveform.unlink()
    result = inspect_receive(request.model_copy(update={"profile": None}))
    assert isinstance(result, ReceiveRejected)
    assert result.issue.code == "invalid-contract"
