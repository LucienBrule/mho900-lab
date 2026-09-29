#!/usr/bin/env python3
"""macOS privileged-path capture control, hard-coded to IPv4 loopback only.

Standard-library Python is used for subprocess signal control and owned UDP
sockets. No specimen interface is accepted. Run inside a private evidence area.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import signal
import socket
import struct
import subprocess
import sys
import time


def stamp():
    return datetime.now(timezone.utc).isoformat()


def wait_until(predicate, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise TimeoutError("control condition did not become true")


def parse_pcap(path):
    data = path.read_bytes()
    assert data[:4] in (b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4")
    endian = "<" if data[0] == 0xd4 else ">"
    cursor, frames = 24, []
    while cursor < len(data):
        assert len(data) - cursor >= 16
        _, _, included, original = struct.unpack(endian + "IIII", data[cursor:cursor + 16])
        assert included == original and cursor + 16 + included <= len(data)
        frames.append(data[cursor + 16:cursor + 16 + included])
        cursor += 16 + included
    assert cursor == len(data)
    return data, frames


def trial(args, name, mode, stop_signal):
    directory = args.output / name
    directory.mkdir()
    owner = pwd.getpwnam(args.drop_user)
    os.chown(directory, owner.pw_uid, owner.pw_gid)
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", 0))
    receiver.settimeout(2)
    port = receiver.getsockname()[1]
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender.bind(("127.0.0.1", 0))
    pcap = directory / "capture.pcap"
    errors = directory / "capture.stderr"
    command = [sys.executable, str(Path(__file__).with_name("recorder-exec.py")),
               "--mode", mode, "--signal-state", str(directory / "signals.toml"), "--",
               str(args.tcpdump), "-i", "lo0", "-s", "0", "-B", "4096", "-U", "-l",
               "--immediate-mode", "-n", "-e", "-tttt", "-vvv", "--print",
               "-Z", args.drop_user, "-w", str(pcap),
               "udp", "and", "dst", "port", str(port), "and", "dst", "host", "127.0.0.1"]
    (directory / "command.txt").write_text(repr(command) + "\n")
    proc = None
    try:
        with errors.open("w") as err, (directory / "live-decode.txt").open("w") as out:
            proc = subprocess.Popen(command, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                                    start_new_session=True, env=dict(os.environ, TZ="UTC"))
            wait_until(lambda: pcap.exists() and pcap.stat().st_size >= 24
                       and "listening on lo0" in errors.read_text(), 8)
            payloads = [f"mho900-host-recorder-control:{name}:{i}".encode() for i in range(3)]
            for payload in payloads:
                sender.sendto(payload, ("127.0.0.1", port))
                received, peer = receiver.recvfrom(4096)
                assert received == payload and peer[0] == "127.0.0.1"
            wait_until(lambda: all(x in pcap.read_bytes() for x in payloads), 5)
            started = time.monotonic()
            proc.send_signal(stop_signal)
            try:
                code = proc.wait(timeout=3)
                graceful = code == 0
            except subprocess.TimeoutExpired:
                graceful = False
                proc.kill()
                code = proc.wait(timeout=3)
            elapsed = time.monotonic() - started
        raw, frames = parse_pcap(pcap)
        assert all(any(payload in frame for frame in frames) for payload in payloads)
        statistics = {}
        text = errors.read_text()
        for label in ("packets captured", "packets received by filter", "packets dropped by kernel"):
            match = re.search(r"(?m)^(\d+) " + re.escape(label) + r"$", text)
            statistics[label.replace(" ", "_")] = int(match[1]) if match else -1
        passed = graceful and statistics["packets_captured"] == len(frames) and all(v >= 0 for v in statistics.values())
        result = dict(schema_version=1, recorded_utc=stamp(), mode=mode,
                      stop_signal=signal.Signals(stop_signal).name, graceful=graceful,
                      exit_code=code, stop_seconds=elapsed, full_frames=len(frames),
                      all_known_payloads_present=True, control_passed=passed,
                      capture_sha256=hashlib.sha256(raw).hexdigest(), **statistics)
        (directory / "result.toml").write_text("\n".join(f"{k} = {json.dumps(v)}" for k, v in result.items()) + "\n")
        print(stamp(), name, result, flush=True)
        return passed
    finally:
        sender.close()
        receiver.close()
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tcpdump", type=Path, required=True)
    parser.add_argument("--drop-user", required=True)
    args = parser.parse_args()
    assert sys.platform == "darwin" and os.geteuid() == 0
    assert args.output.is_absolute() and args.tcpdump.is_absolute()
    blocked = sorted(int(s) for s in signal.pthread_sigmask(signal.SIG_BLOCK, []))
    (args.output / "parent-signals.toml").write_text(f"blocked = {blocked}\n")
    print(stamp(), "parent blocked signals", blocked, flush=True)
    trial(args, "inherited-mask", "inherit", signal.SIGINT)
    for name, sig in [("normalized-int-1", signal.SIGINT),
                      ("normalized-term", signal.SIGTERM),
                      ("normalized-int-2", signal.SIGINT)]:
        assert trial(args, name, "normalize", sig), name + " failed; stop before physical acquisition"
    (args.output / "PASSED").write_text(stamp() + "\n")


if __name__ == "__main__":
    main()
