"""Exercise the public script and data through the same installed command surface."""

import hashlib
import os
import subprocess
import sys
import tomllib
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[3] / "examples" / "sealed-review"
PIN = "b049d958172b0b013aa9934c66e029d2a33559e13aed9d3e362719e8ce9672f6"


def test_public_walkthrough_and_existing_output_refusal(tmp_path: Path) -> None:
    destination = tmp_path / "public walkthrough"
    environment = dict(os.environ)
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment["PATH"]
    command = ["sh", str(FIXTURE / "walkthrough.sh"), str(destination)]
    completed = subprocess.run(
        command, cwd=tmp_path, env=environment, capture_output=True, timeout=30
    )
    assert completed.returncode == 0, completed.stderr.decode()
    assert hashlib.sha256((destination / "manifest.toml").read_bytes()).hexdigest() == PIN
    raw = (destination / "accepted.toml").read_text()
    accepted = tomllib.loads(raw)
    assert accepted["result"] == "accepted"
    assert accepted["inventory_files"] == 6 and accepted["capture_frames"] == 6
    assert accepted["query_count"] == 2 and accepted["inventory_bytes"] == 702
    assert accepted["physical_origin_proven"] is False
    assert accepted["device_execution_proven"] is False
    assert accepted["process_exit_proven"] is False
    assert "SYNTHETIC-UNIT" not in raw and str(destination) not in raw
    changed = tomllib.loads((destination / "changed.toml").read_text())
    mixed = tomllib.loads((destination / "mixed.toml").read_text())
    assert changed["stage"] == "inventory-before"
    assert mixed["stage"] == "transcripts" and mixed["code"] == "tcp-transcript-mismatch"
    before = {
        str(p.relative_to(destination)): p.read_bytes()
        for p in destination.rglob("*")
        if p.is_file()
    }
    repeated = subprocess.run(
        command, cwd=tmp_path, env=environment, capture_output=True, timeout=30
    )
    assert repeated.returncode != 0
    after = {
        str(p.relative_to(destination)): p.read_bytes()
        for p in destination.rglob("*")
        if p.is_file()
    }
    assert before == after


def internet_sum(raw: bytes) -> int:
    padded = raw + (b"\0" if len(raw) % 2 else b"")
    total = sum(int.from_bytes(padded[n : n + 2], "big") for n in range(0, len(padded), 2))
    while total >> 16:
        total = (total & 65535) + (total >> 16)
    return total


def test_public_packets_have_independently_checked_ip_and_tcp_checksums() -> None:
    raw = (FIXTURE / "bundle" / "capture.pcap").read_bytes()
    offset = 24
    count = 0
    while offset < len(raw):
        size = int.from_bytes(raw[offset + 8 : offset + 12], "little")
        frame = raw[offset + 16 : offset + 16 + size]
        assert size >= 60 and len(frame) == size
        assert frame[12:14] == b"\x08\x00"
        ip = frame[14:]
        assert ip[0] == 0x45 and ip[9] == 6
        length = int.from_bytes(ip[2:4], "big")
        assert internet_sum(ip[:20]) == 65535
        tcp = ip[20:length]
        pseudo = ip[12:20] + b"\x00\x06" + len(tcp).to_bytes(2, "big")
        assert internet_sum(pseudo + tcp) == 65535
        assert not any(ip[length:])
        offset += 16 + size
        count += 1
    assert offset == len(raw) and count == 6
