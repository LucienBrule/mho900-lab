"""POSIX serial transport without input flushing, retries, or unbounded drain."""

import array
import fcntl
import os
import select
import stat
import termios
import time
from pathlib import Path

from .session import ReadWindow


class PosixPort:
    def __init__(self, device: Path, *, require_modem_lines: bool = True) -> None:
        self.device = device
        self.require_modem_lines = require_modem_lines
        self.fd: int | None = None

    def prepare(self) -> None:
        if self.fd is not None:
            raise OSError("port already opened")
        self.fd = os.open(self.device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_NOFOLLOW)
        fd = self.fd
        if not stat.S_ISCHR(os.fstat(fd).st_mode) or not os.isatty(fd):
            raise OSError("target must be a terminal character device")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.ioctl(fd, termios.TIOCEXCL)
        # Construct the native seven-element termios boundary in one place.
        # TCSANOW never deliberately flushes queued input. HUPCL and all flow
        # control flags are clear. Driver open-time control-line pulses remain possible.
        cc: list[bytes | int] = [b"\0"] * termios.NCCS
        cc[termios.VMIN] = 0
        cc[termios.VTIME] = 0
        attributes: list[int | list[bytes | int]] = [
            0,
            0,
            termios.CS8 | termios.CREAD | termios.CLOCAL,
            0,
            termios.B115200,
            termios.B115200,
            cc,
        ]
        try:
            termios.tcsetattr(fd, termios.TCSANOW, attributes)
            actual = termios.tcgetattr(fd)
        except termios.error as error:
            raise OSError("terminal setup failed") from error
        expected = [
            0,
            0,
            termios.CS8 | termios.CREAD | termios.CLOCAL,
            0,
            termios.B115200,
            termios.B115200,
        ]
        # Linux additionally encodes baud in cflag; compare that field separately.
        if actual[0:2] != expected[0:2] or actual[3:6] != expected[3:6]:
            raise OSError("terminal configuration did not stick")
        control = actual[2]
        if not isinstance(control, int):
            raise OSError("unexpected terminal control type")
        forbidden = termios.PARENB | termios.CSTOPB | termios.HUPCL | termios.CRTSCTS
        if control & forbidden or control & termios.CSIZE != termios.CS8:
            raise OSError("terminal parity, stop bits or flow control differs")
        if self.require_modem_lines:
            lines = array.array("i", [termios.TIOCM_DTR | termios.TIOCM_RTS])
            fcntl.ioctl(fd, termios.TIOCMBIC, lines)
            observed = array.array("i", [0])
            fcntl.ioctl(fd, termios.TIOCMGET, observed)
            if observed[0] & lines[0]:
                raise OSError("DTR/RTS did not clear")

    def descriptor(self) -> int:
        if self.fd is None:
            raise OSError("port not opened")
        return self.fd

    def read_window(self, seconds: float, limit: int) -> ReadWindow:
        data = bytearray()
        deadline = time.monotonic() + seconds
        try:
            fd = self.descriptor()
            while (remaining := deadline - time.monotonic()) > 0:
                ready, _, _ = select.select([fd], [], [], remaining)
                if not ready:
                    break
                chunk = os.read(fd, min(1024, limit + 1 - len(data)))
                if not chunk:
                    return ReadWindow(bytes(data), error=True)
                data.extend(chunk)
                if len(data) > limit:
                    return ReadWindow(bytes(data), overflow=True)
        except OSError:
            return ReadWindow(bytes(data), error=True)
        return ReadWindow(bytes(data))

    def write_once(self, data: bytes) -> int:
        fd = self.descriptor()
        _, ready, _ = select.select([], [fd], [], 1.0)
        if not ready:
            raise OSError("write readiness deadline")
        return os.write(fd, data)

    def close(self) -> None:
        if self.fd is not None:
            fd, self.fd = self.fd, None
            # No drain/flush, no restoration of unknown modem states, no second close.
            os.close(fd)
