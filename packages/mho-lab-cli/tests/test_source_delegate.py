import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from mho_lab_cli import source_cli, source_delegate
from mho_lab_cli.cli import main
from mho_lab_cli.source_delegate import PointEvidenceFailed, PointRecorded, point_once
from mho_source import Command, FactoryPointCommand, PointCommand, ReadWindow


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


@pytest.mark.parametrize(
    "command",
    [
        PointCommand(frequency_hz=100_000_000, reference_hz=25_000_000, power_code=4),
        FactoryPointCommand(frequency_hz=100_000_000, power_code=0),
    ],
)
def test_post_write_filesystem_failure_keeps_uncertainty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: Command
) -> None:
    real = source_delegate.durable
    port = SilentPort(Path("synthetic"))

    def fail_response(path: Path, data: bytes) -> None:
        if path.name == "response.bin":
            raise OSError("synthetic disk failure")
        real(path, data)

    monkeypatch.setattr(source_delegate, "durable", fail_response)
    result = point_once(
        command,
        Path("synthetic"),
        tmp_path / "run",
        lambda _: port,
    )
    assert isinstance(result, PointEvidenceFailed) and result.execution_started
    assert result.outcome is not None
    assert result.outcome.transcript.bytes_written == len(port.writes[0])
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


def test_factory_cli_delegate_sealed_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    port = SilentPort(Path("synthetic"))

    def delegate(command: Command, device: Path, output: Path) -> source_delegate.PointRunResult:
        return point_once(command, device, output, lambda _: port)

    monkeypatch.setattr(source_cli, "point_once", delegate)
    runner = CliRunner()
    arguments = ["--frequency-hz", "100250000", "--power-code", "0"]
    offline = runner.invoke(main, ["source", "factory-frame", *arguments])
    assert offline.exit_code == 0
    assert offline.output.strip() == "55 55 00 64 00 19 00 0D 0A"
    assert not port.writes
    output = tmp_path / "factory"
    result = runner.invoke(
        main,
        [
            "source",
            "factory-point-once",
            *arguments,
            "--device",
            "synthetic",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0 and "device_acceptance_proven = false" in result.output
    assert port.writes == [bytes.fromhex("55 55 00 64 00 19 00 0D 0A")] and port.closed
    assert (output / "data/request.bin").read_bytes() == port.writes[0]
    fields = tomllib.loads((output / "data/request.toml").read_text())
    assert fields["protocol"] == "factory-point-crlf-hundredths/1"
    assert fields["schema"] == "mho-source.factory-point-attempt/1"
    assert fields["device_image_equivalence_proven"] is False
    assert fields["reference_image_sha256"] == (
        "a3111637e7cab47fd5045a04c0521c3f525016f1f15d83174cc5f67be8b0b60f"
    )
    assert "reference_hz" not in fields
    # Independently verify the delegate's retained manifest through the public CLI.
    checked = runner.invoke(
        main,
        ["evidence", "verify", str(output / "data"), "--manifest", str(output / "artifacts.toml")],
    )
    assert checked.exit_code == 0 and "Verified SHA-256" in checked.output


def test_factory_invalid_before_evidence_or_port(tmp_path: Path) -> None:
    command = FactoryPointCommand(frequency_hz=100_000_000, power_code=0)

    def unopened(device: Path) -> SilentPort:
        raise AssertionError("invalid command reached port construction")

    with pytest.raises(ValidationError):
        point_once(
            command.model_copy(update={"power_code": 4}),
            Path("synthetic"),
            tmp_path / "bad",
            unopened,
        )
    result = CliRunner().invoke(
        main,
        [
            "source",
            "factory-point-once",
            "--device",
            "synthetic",
            "--output",
            str(tmp_path / "bad"),
            "--frequency-hz",
            "100130000",
            "--power-code",
            "0",
        ],
    )
    assert result.exit_code == 1 and "CR delimiter" in result.output
    assert not (tmp_path / "bad").exists()
