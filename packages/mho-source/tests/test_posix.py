import os
import pty
import select
import termios
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from mho_source import (
    Command,
    FactoryPointCommand,
    PointCommand,
    PosixPort,
    Rejected,
    TransportComplete,
    encode_command,
    execute,
)


@dataclass
class Peer:
    received: bytes = b""
    error: str = ""


@pytest.mark.parametrize("reply", [b"", b"PTY response"])
@pytest.mark.parametrize(
    "command",
    [
        PointCommand(frequency_hz=100_000_000, reference_hz=25_000_000, power_code=4),
        FactoryPointCommand(frequency_hz=100_000_000, power_code=0),
    ],
)
def test_real_posix_pty_exchange(reply: bytes, command: Command) -> None:
    master, slave = pty.openpty()
    target = Path(os.ttyname(slave))
    peer = Peer()

    def respond() -> None:
        try:
            ready, _, _ = select.select([master], [], [], 4.0)
            if not ready:
                peer.error = "no command"
                return
            peer.received = os.read(master, 64)
            if reply:
                os.write(master, reply)
        except OSError:
            peer.error = "peer IO failed"

    worker = threading.Thread(target=respond)
    worker.start()
    start = time.monotonic()
    try:
        # PTYs have no modem lines; real CLI always requires modem-line readback.
        result = execute(command, PosixPort(target, require_modem_lines=False), lambda: None)
        assert isinstance(result, TransportComplete), result
        assert result.transcript.response == reply
        worker.join(4.0)
        assert not worker.is_alive() and peer.error == ""
        assert peer.received == encode_command(command)
        assert time.monotonic() - start < 6.0
    finally:
        os.close(slave)
        os.close(master)
        worker.join(4.0)


def test_queued_input_survives_configuration() -> None:
    master, slave = pty.openpty()
    target = Path(os.ttyname(slave))
    # Queue a complete canonical line before preparing the sender.
    os.write(master, b"BOOT\n")
    port = PosixPort(target, require_modem_lines=False)
    try:
        result = execute(
            PointCommand(frequency_hz=100_000_000, reference_hz=25_000_000, power_code=4),
            port,
            lambda: None,
        )
        assert isinstance(result, Rejected)
        assert b"BOOT" in result.transcript.before and not result.transcript.write_attempted
    finally:
        os.close(slave)
        os.close(master)


def test_actual_receive_cap() -> None:
    master, slave = pty.openpty()
    port = PosixPort(Path(os.ttyname(slave)), require_modem_lines=False)
    try:
        port.prepare()
        os.write(master, b"0123456789")
        result = port.read_window(0.2, 5)
        assert result.overflow and result.data == b"012345"
    finally:
        port.close()
        os.close(slave)
        os.close(master)


def test_termios_failure_becomes_closed_prewrite_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    master, slave = pty.openpty()

    def fail(*args: object) -> None:
        raise termios.error(22, "synthetic termios failure")

    monkeypatch.setattr(termios, "tcsetattr", fail)
    port = PosixPort(Path(os.ttyname(slave)), require_modem_lines=False)
    try:
        result = execute(
            PointCommand(frequency_hz=100_000_000, reference_hz=25_000_000, power_code=4),
            port,
            lambda: None,
        )
        assert isinstance(result, Rejected) and not result.transcript.write_attempted
        assert port.fd is None
    finally:
        os.close(slave)
        os.close(master)
