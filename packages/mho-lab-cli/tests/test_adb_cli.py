"""Offline debug-bridge reports expose structural facts without service or banner bytes."""

import hashlib
import tomllib
from pathlib import Path

from click.testing import CliRunner

from mho_lab_cli.cli import main


def frame(command: bytes, first: int, second: int, payload: bytes = b"") -> bytes:
    return (
        command
        + first.to_bytes(4, "little")
        + second.to_bytes(4, "little")
        + len(payload).to_bytes(4, "little")
        + (sum(payload) & 0xFFFFFFFF).to_bytes(4, "little")
        + (int.from_bytes(command, "little") ^ 0xFFFFFFFF).to_bytes(4, "little")
        + payload
    )


def test_inspection_redacts_banner_and_service(tmp_path: Path) -> None:
    path = tmp_path / "PRIVATE-PATH.bin"
    raw = frame(b"CNXN", 0x1000000, 262144, b"PRIVATE-BANNER\0") + frame(
        b"OPEN", 7, 0, b"PRIVATE-SERVICE\0"
    )
    path.write_bytes(raw)
    result = CliRunner().invoke(
        main, ["adb", "inspect", str(path), "--expected-sha256", hashlib.sha256(raw).hexdigest()]
    )
    assert result.exit_code == 0, result.output
    report = tomllib.loads(result.output)
    assert report["frame_count"] == 2
    assert report["device_execution_proven"] is False
    assert "PRIVATE" not in result.output


def test_matching_ready_is_distinct_from_missing_reply(tmp_path: Path) -> None:
    client = tmp_path / "client.bin"
    server = tmp_path / "server.bin"
    payload = b"PRIVATE-SERVICE\0"
    request = frame(b"OPEN", 7, 0, payload)
    response = frame(b"OKAY", 9, 7)
    client.write_bytes(request)
    server.write_bytes(response)
    arguments = [
        "adb",
        "match-open",
        "--client",
        str(client),
        "--client-sha256",
        hashlib.sha256(request).hexdigest(),
        "--server",
        str(server),
        "--server-sha256",
        hashlib.sha256(response).hexdigest(),
        "--payload-sha256",
        hashlib.sha256(payload).hexdigest(),
    ]
    matched = CliRunner().invoke(main, arguments)
    assert matched.exit_code == 0, matched.output
    report = tomllib.loads(matched.output)
    assert report["result"] == "matched" and report["ready_frames"] == 1
    assert report["tcp_delivery_proven"] is False
    assert report["total_order_proven"] is False
    assert "PRIVATE" not in matched.output
    # Empty captured server bytes are not evidence of a matching reply.
    server.write_bytes(b"")
    arguments[arguments.index("--server-sha256") + 1] = hashlib.sha256(b"").hexdigest()
    missing = CliRunner().invoke(main, arguments)
    assert missing.exit_code == 1
    assert tomllib.loads(missing.output)["result"] == "missing"


def test_checksum_failure_preserves_prefix_without_disclosure(tmp_path: Path) -> None:
    path = tmp_path / "PRIVATE-PATH.bin"
    prefix = frame(b"CNXN", 0x1000000, 262144, b"PRIVATE-BANNER\0")
    malformed = bytearray(frame(b"OPEN", 7, 0, b"PRIVATE-SERVICE\0"))
    malformed[16:20] = bytes(4)
    raw = prefix + malformed
    path.write_bytes(raw)
    result = CliRunner().invoke(
        main, ["adb", "inspect", str(path), "--expected-sha256", hashlib.sha256(raw).hexdigest()]
    )
    assert result.exit_code == 1
    report = tomllib.loads(result.output)
    assert report["parsed_prefix_frames"] == 1
    assert report["byte_offset"] == len(prefix)
    assert report["code"] == "payload-checksum"
    assert "PRIVATE" not in result.output


def test_wrong_pin_stops_before_parsing(tmp_path: Path) -> None:
    path = tmp_path / "PRIVATE-PATH.bin"
    path.write_bytes(b"PRIVATE-MALFORMED")
    result = CliRunner().invoke(main, ["adb", "inspect", str(path), "--expected-sha256", "0" * 64])
    assert result.exit_code == 1
    assert tomllib.loads(result.output)["code"] == "source-pin"
    assert "PRIVATE" not in result.output
