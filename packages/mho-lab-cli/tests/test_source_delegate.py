from pathlib import Path

import pytest
from click.testing import CliRunner

from mho_lab_cli import source_delegate
from mho_lab_cli.cli import main
from mho_lab_cli.source_delegate import PointEvidenceFailed, PointRecorded, point_once
from mho_source import PointCommand, ReadWindow


class SilentPort:
    def __init__(self, path: Path) -> None:
        self.writes: list[bytes] = []
        self.closed = False

    def prepare(self) -> None:
        pass

    def read_window(self, seconds: float, limit: int) -> ReadWindow:
        return ReadWindow()

    def write_once(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def close(self) -> None:
        self.closed = True


def test_evidence_and_existing_run_refusal(tmp_path: Path) -> None:
    output = tmp_path / "run"
    command = PointCommand(frequency_hz=100_000_000, reference_hz=25_000_000, power_code=4)
    result = point_once(command, Path("synthetic"), output, SilentPort)
    assert isinstance(result, PointRecorded)
    assert (output / "data/request.bin").read_bytes() == bytes.fromhex(
        "AD 01 01 04 03 D0 90 01 86 A0 3D"
    )
    assert (output / "data/driver-accepted.bin").read_bytes() == (
        output / "data/request.bin"
    ).read_bytes()
    assert (output / "data/write-intent.toml").is_file()
    assert (output / "data/response.bin").read_bytes() == b""
    before = (output / "artifacts.toml").read_bytes()
    rejected = point_once(command, Path("synthetic"), output, SilentPort)
    assert isinstance(rejected, PointEvidenceFailed) and not rejected.execution_started
    assert (output / "artifacts.toml").read_bytes() == before


def test_post_write_filesystem_failure_keeps_uncertainty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = source_delegate.durable
    port = SilentPort(Path("synthetic"))

    def fail_response(path: Path, data: bytes) -> None:
        if path.name == "response.bin":
            raise OSError("synthetic disk failure")
        real(path, data)

    monkeypatch.setattr(source_delegate, "durable", fail_response)
    result = point_once(
        PointCommand(frequency_hz=100_000_000, reference_hz=25_000_000, power_code=4),
        Path("synthetic"),
        tmp_path / "run",
        lambda _: port,
    )
    assert isinstance(result, PointEvidenceFailed) and result.execution_started
    assert result.outcome is not None and result.outcome.transcript.bytes_written == 11
    assert len(port.writes) == 1 and port.closed
    assert (tmp_path / "run/data/write-intent.toml").is_file()
    assert not (tmp_path / "run/artifacts.toml").exists()


def test_offline_cli_and_invalid_request(tmp_path: Path) -> None:
    runner = CliRunner()
    frame = runner.invoke(
        main,
        [
            "source",
            "frame",
            "--frequency-hz",
            "100000000",
            "--reference-hz",
            "25000000",
            "--power-code",
            "4",
        ],
    )
    assert frame.exit_code == 0 and frame.output.strip() == "AD 01 01 04 03 D0 90 01 86 A0 3D"
    rejected = runner.invoke(
        main,
        [
            "source",
            "point-once",
            "--frequency-hz",
            "100000000",
            "--reference-hz",
            "25000000",
            "--power-code",
            "5",
            "--device",
            "synthetic",
            "--output",
            str(tmp_path / "bad"),
        ],
    )
    assert rejected.exit_code == 1 and not (tmp_path / "bad").exists()
