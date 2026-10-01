"""Durable evidence around an explicitly requested physical source operation."""

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from mho_evidence import SealCreated, SealRequest, seal
from mho_source import (
    FACTORY_REFERENCE_SHA256,
    Command,
    Outcome,
    PointCommand,
    Port,
    PosixPort,
    encode_command,
    execute,
)


@dataclass(frozen=True)
class PointRecorded:
    outcome: Outcome
    manifest_sha256: str


@dataclass(frozen=True)
class PointEvidenceFailed:
    phase: str
    execution_started: bool
    outcome: Outcome | None = None


type PointRunResult = PointRecorded | PointEvidenceFailed


def durable(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def sync_directory(path: Path) -> None:
    directory = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def stamp() -> bytes:
    now = datetime.now(UTC)
    return (f'utc = "{now.isoformat()}"\nlocal = "{now.astimezone().isoformat()}"\n').encode()


def point_once(
    command: Command,
    device: Path,
    output: Path,
    port_factory: Callable[[Path], Port] = PosixPort,
) -> PointRunResult:
    frame = encode_command(command)
    if isinstance(command, PointCommand):
        protocol_fields = (
            'schema = "mho-source.point-attempt/1"\n'
            'protocol = "hawkrao-point-ad/1"\n'
            f"reference_hz = {command.reference_hz}\n"
        )
    else:
        protocol_fields = (
            'schema = "mho-source.factory-point-attempt/1"\n'
            'protocol = "factory-point-crlf-hundredths/1"\n'
            f'reference_image_sha256 = "{FACTORY_REFERENCE_SHA256}"\n'
            "device_image_equivalence_proven = false\n"
        )
    phase = "evidence-directory"
    started = False
    outcome: Outcome | None = None
    try:
        output.mkdir()  # Deliberately refuses an existing run, including failed runs.
        data = output / "data"
        data.mkdir()
        sync_directory(output)
        sync_directory(output.parent)
        phase = "request-evidence"
        durable(data / "request.bin", frame)
        durable(
            data / "request.toml",
            (
                protocol_fields + f"device = {json.dumps(str(device))}\n"
                f"frequency_hz = {command.frequency_hz}\n"
                f"power_code = {command.power_code}\n"
                "baud = 115200\ndata_bits = 8\nstop_bits = 1\n"
                'parity = "none"\nflow_control = "none"\n'
                'modem_lines = "clear-and-read-back-DTR-RTS"\n'
                "hupcl = false\nwrite_attempt_limit = 1\n"
                "pre_read_seconds = 0.5\npost_read_seconds = 2.0\n"
                "receive_limit_bytes = 4096\nopen_time_line_glitch_excluded = false\n"
                "device_acceptance_proven = false\n"
            ).encode(),
        )
        durable(data / "started.toml", stamp())
        phase = "execution"
        started = True
        outcome = execute(
            command, port_factory(device), lambda: durable(data / "write-intent.toml", stamp())
        )
        phase = "result-evidence"
        transcript = outcome.transcript
        durable(data / "pre-input.bin", transcript.before)
        durable(data / "response.bin", transcript.response)
        if transcript.bytes_written is not None:
            durable(data / "driver-accepted.bin", frame[: transcript.bytes_written])
        # An intent without a final result is uncertain, never safe to retry.
        lines = [
            f'result = "{outcome.kind}"',
            f'issue = "{transcript.issue}"',
            f"write_attempted = {str(transcript.write_attempted).lower()}",
            f"close_failed = {str(transcript.close_failed).lower()}",
            f'started_utc = "{transcript.started_utc}"',
            f'finished_utc = "{transcript.finished_utc}"',
            "device_acceptance_proven = false",
            "wire_delivery_proven = false",
        ]
        if transcript.bytes_written is not None:
            lines.append(f"bytes_written = {transcript.bytes_written}")
        durable(data / "result.toml", ("\n".join(lines) + "\n").encode())
        phase = "seal"
        sealed = seal(SealRequest(data, output / "artifacts.toml"))
        if not isinstance(sealed, SealCreated):
            return PointEvidenceFailed(phase, started, outcome)
        return PointRecorded(outcome, sealed.manifest_sha256)
    except OSError:
        return PointEvidenceFailed(phase, started, outcome)
