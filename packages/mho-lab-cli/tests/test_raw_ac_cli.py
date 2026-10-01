"""Typed supplied-file/CLI statistics equivalence and rejection witnesses."""

import hashlib
import math
import tomllib
from pathlib import Path
from typing import Literal

import pytest
from click.testing import CliRunner
from pydantic import BaseModel, ConfigDict, Field

from mho_lab_cli.cli import main
from mho_lab_cli.raw_ac_delegate import inspect_raw_ac
from mho_lab_cli.waveform_delegate import WaveformInspectionRequest
from mho_rf import RawAcMetrics, RawAcStatistics, RawStatisticsGeometry, RawStatisticsRejected
from mho_waveform import RawAcquisition


class ReceiptBase(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", allow_inf_nan=False)
    schema_version: Literal["mho-rf.raw-ac-inspection/1"]
    classification: Literal["supplied original RAW sampled AC statistics"]
    method: Literal["unwindowed-demeaned-population"]
    physical_origin_proven: Literal[False]
    calibrated_amplitude_proven: Literal[False]
    receive_qualification_proven: Literal[False]


class AcceptedReceipt(ReceiptBase):
    result: Literal["raw-ac-statistics"]
    preamble_before_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    waveform_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    preamble_after_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    geometry: RawStatisticsGeometry
    metrics: RawAcMetrics


class RejectedReceipt(ReceiptBase):
    result: Literal["statistics-rejected"]
    stage: Literal["input", "raw", "numerical"]
    code: str
    message: str
    token_index: int | None = None
    preamble_before_sha256: str | None = None
    waveform_sha256: str | None = None
    preamble_after_sha256: str | None = None


def source(
    directory: Path, volts: tuple[float, ...] = (0.25, 0.5, 0.25, 0.5)
) -> WaveformInspectionRequest:
    before = directory / "before.txt"
    data = directory / "data.txt"
    after = directory / "after.txt"
    preamble = f"2,2,{len(volts)},1,2.5e-10,0,0,6e-6,0,32768\n".encode()
    before.write_bytes(preamble)
    after.write_bytes(preamble)
    data.write_text(",".join(f"{v:.17g}" for v in volts) + "\n")
    return WaveformInspectionRequest(
        preamble_before=before,
        waveform=data,
        preamble_after=after,
        acquisition=RawAcquisition(
            actual_sample_rate_hz=4e9, memory_points=len(volts), start=1, stop=len(volts)
        ),
    )


def arguments(request: WaveformInspectionRequest) -> list[str]:
    return [
        "rf",
        "raw-ac-inspect",
        "--preamble-before",
        str(request.preamble_before),
        "--data",
        str(request.waveform),
        "--preamble-after",
        str(request.preamble_after),
        "--actual-rate-hz",
        repr(request.acquisition.actual_sample_rate_hz),
        "--memory-points",
        str(request.acquisition.memory_points),
        "--start",
        str(request.acquisition.start),
        "--stop",
        str(request.acquisition.stop),
    ]


def test_typed_receipt_library_equivalence_and_input_preservation(tmp_path: Path) -> None:
    request = source(tmp_path)
    original = request.waveform.read_bytes()
    library = inspect_raw_ac(request)
    assert isinstance(library, RawAcStatistics)
    result = CliRunner().invoke(main, arguments(request))
    assert result.exit_code == 0, result.output
    receipt = AcceptedReceipt.model_validate(tomllib.loads(result.output))
    assert receipt.geometry == library.geometry and receipt.metrics == library.metrics
    assert receipt.waveform_sha256 == hashlib.sha256(original).hexdigest()
    assert receipt.preamble_before_sha256 == library.evidence.preamble_before_sha256
    assert receipt.metrics.dc_mean_v == 0.375 and receipt.metrics.ac_rms_v == 0.125
    assert request.waveform.read_bytes() == original
    assert str(tmp_path) not in result.output and "volts =" not in result.output


@pytest.mark.parametrize("kind", ["constant", "tiny"])
def test_zero_and_tiny_varying_receipts(tmp_path: Path, kind: str) -> None:
    volts = (0.1,) * 7 if kind == "constant" else (-1e-200, 1e-200) * 4
    request = source(tmp_path, volts)
    result = CliRunner().invoke(main, arguments(request))
    assert result.exit_code == 0
    receipt = AcceptedReceipt.model_validate(tomllib.loads(result.output))
    assert receipt.metrics.constant_samples == (kind == "constant")
    assert receipt.metrics.zero_sampled_ac == (kind == "constant")
    assert receipt.metrics.ac_rms_v == (0.0 if kind == "constant" else 1e-200)


@pytest.mark.parametrize(
    "kind", ["unrepresentable", "malformed", "display", "preamble", "symlink", "rate"]
)
def test_rejected_inputs_preserve_structural_evidence(tmp_path: Path, kind: str) -> None:
    request = source(tmp_path, (0.0, math.ulp(0.0)) if kind == "unrepresentable" else (0.1, -0.1))
    if kind == "malformed":
        request.waveform.write_bytes(b"PRIVATE-BAD-TOKEN,-0.1\n")
    elif kind == "display":
        preamble = request.preamble_before.read_bytes().replace(b"2,2,", b"2,0,")
        request.preamble_before.write_bytes(preamble)
        request.preamble_after.write_bytes(preamble)
    elif kind == "preamble":
        request.preamble_after.write_bytes(
            request.preamble_after.read_bytes().replace(b"32768", b"32769")
        )
    elif kind == "symlink":
        target = tmp_path / "target.txt"
        request.waveform.rename(target)
        request.waveform.symlink_to(target)
    elif kind == "rate":
        request = request.model_copy(
            update={
                "acquisition": request.acquisition.model_copy(update={"actual_sample_rate_hz": 2e9})
            }
        )
    result = CliRunner().invoke(main, arguments(request))
    assert result.exit_code == 1
    receipt = RejectedReceipt.model_validate(tomllib.loads(result.output))
    assert receipt.stage == (
        "numerical" if kind == "unrepresentable" else "input" if kind == "symlink" else "raw"
    )
    if kind != "symlink":
        assert receipt.waveform_sha256 == hashlib.sha256(request.waveform.read_bytes()).hexdigest()
    assert str(tmp_path) not in result.output and "PRIVATE-BAD-TOKEN" not in result.output


@pytest.mark.parametrize("value", ["0", "nan", "inf"])
def test_invalid_observations_precede_file_read(tmp_path: Path, value: str) -> None:
    request = source(tmp_path)
    command = arguments(request)
    command[command.index("--actual-rate-hz") + 1] = value
    request.waveform.unlink()
    result = CliRunner().invoke(main, command)
    assert result.exit_code == 1
    receipt = RejectedReceipt.model_validate(tomllib.loads(result.output))
    assert receipt.code == "invalid-contract" and receipt.waveform_sha256 is None


def test_delegate_revalidates_unchecked_contract(tmp_path: Path) -> None:
    request = source(tmp_path)
    request.waveform.unlink()
    result = inspect_raw_ac(request.model_copy(update={"limits": None}))
    assert isinstance(result, RawStatisticsRejected) and result.issue.code == "invalid-contract"
