"""Public CLI controls with a tiny independent synthetic capture writer."""

import hashlib
from ipaddress import IPv4Address
from pathlib import Path

from click.testing import CliRunner

from mho_lab_cli.cli import main


def captured_frame(sequence: int, flags: int, payload: bytes, *, reverse: bool = False) -> bytes:
    source = IPv4Address("192.0.2.2" if reverse else "192.0.2.1")
    destination = IPv4Address("192.0.2.1" if reverse else "192.0.2.2")
    sport = 5555 if reverse else 41000
    dport = 41000 if reverse else 5555
    tcp = (
        sport.to_bytes(2, "big")
        + dport.to_bytes(2, "big")
        + sequence.to_bytes(4, "big")
        + bytes(4)
        + bytes([0x50, flags])
        + bytes(6)
        + payload
    )
    ip = (
        b"\x45\x00"
        + (20 + len(tcp)).to_bytes(2, "big")
        + bytes(4)
        + b"\x40\x06"
        + bytes(2)
        + source.packed
        + destination.packed
        + tcp
    )
    ethernet = bytes(12) + b"\x08\x00" + ip
    return bytes(8) + len(ethernet).to_bytes(4, "little") * 2 + ethernet


def write_capture(path: Path) -> None:
    header = (
        b"\xd4\xc3\xb2\xa1\x02\x00\x04\x00"
        + bytes(8)
        + (65535).to_bytes(4, "little")
        + (1).to_bytes(4, "little")
    )
    path.write_bytes(
        header
        + captured_frame(100, 2, b"")
        + captured_frame(200, 18, b"", reverse=True)
        + captured_frame(101, 24, b"*IDN?\n")
        + captured_frame(201, 24, b"SYNTHETIC,MODEL,PRIVATE,VERSION\n", reverse=True)
        + captured_frame(107, 17, b"")
        + captured_frame(233, 17, b"", reverse=True)
    )


def arguments(path: Path) -> list[str]:
    return [
        "transport",
        "inspect",
        str(path),
        "--client-address",
        "192.0.2.1",
        "--client-port",
        "41000",
        "--server-address",
        "192.0.2.2",
        "--server-port",
        "5555",
    ]


def test_private_payload_not_rendered(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.pcap"
    write_capture(path)
    result = CliRunner().invoke(main, arguments(path))
    assert result.exit_code == 0, result.output
    assert "capture_frames = 6\n" in result.output
    expected_digest = hashlib.sha256(b"*IDN?\n").hexdigest()
    assert f'request_sha256 = "{expected_digest}"\n' in result.output
    assert "peer_delivery_proven = false\n" in result.output
    assert "device_execution_proven = false\n" in result.output
    assert "PRIVATE" not in result.output
    assert "*IDN?" not in result.output


def test_incomplete_capture_rejected(tmp_path: Path) -> None:
    path = tmp_path / "truncated.pcap"
    write_capture(path)
    path.write_bytes(path.read_bytes()[:-1])
    result = CliRunner().invoke(main, arguments(path))
    assert result.exit_code == 1
    assert 'result = "accepted"' not in result.output


def test_hostname_is_not_resolved(tmp_path: Path) -> None:
    args = arguments(tmp_path / "not-opened.pcap")
    args[4] = "instrument.invalid"
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 2
    assert "literal IPv4 address" in result.output
