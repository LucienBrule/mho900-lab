"""One write attempt, no retry, and explicit uncertainty after a write begins."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from .point import PointCommand, encode_point


@dataclass(frozen=True)
class ReadWindow:
    data: bytes = b""
    overflow: bool = False
    error: bool = False


class Port(Protocol):
    def prepare(self) -> None: ...
    def read_window(self, seconds: float, limit: int) -> ReadWindow: ...
    def write_once(self, data: bytes) -> int: ...
    def close(self) -> None: ...


@dataclass(frozen=True)
class Transcript:
    request: bytes
    before: bytes
    response: bytes
    write_attempted: bool
    bytes_written: int | None
    issue: str
    close_failed: bool
    started_utc: str
    finished_utc: str


@dataclass(frozen=True)
class Rejected:
    transcript: Transcript
    kind: Literal["rejected-before-write"] = "rejected-before-write"


@dataclass(frozen=True)
class Uncertain:
    transcript: Transcript
    kind: Literal["write-outcome-uncertain"] = "write-outcome-uncertain"


@dataclass(frozen=True)
class TransportComplete:
    transcript: Transcript
    kind: Literal["transport-complete-device-unconfirmed"] = "transport-complete-device-unconfirmed"


type Outcome = Rejected | Uncertain | TransportComplete


def execute(command: PointCommand, port: Port, before_write: Callable[[], None]) -> Outcome:
    """Preserve input, stop on pre-input, attempt one OS write, then observe for 2 s.

    The callback must durably record write intent. A complete OS write only
    establishes driver acceptance, not UART delivery or device interpretation.
    """
    frame = encode_point(command)  # Revalidate before any port operation.
    started = datetime.now(UTC).isoformat()
    before = b""
    response = b""
    attempted = False
    written: int | None = None
    issue = "setup"
    close_failed = False
    try:
        port.prepare()
        issue = "pre-read"
        pre = port.read_window(0.5, 4096)
        before = pre.data
        if pre.error or pre.overflow or before:
            issue = "unexpected-pre-input-or-read-failure"
        else:
            issue = "write-intent-evidence"
            before_write()
            issue = "write"
            attempted = True
            written = port.write_once(frame)
            if written != len(frame):
                issue = "short-write"
            else:
                issue = "post-read"
                post = port.read_window(2.0, 4096)
                response = post.data
                if post.error:
                    issue = "post-read-failure"
                elif post.overflow:
                    issue = "receive-limit"
                else:
                    issue = "none"
    except OSError:
        # Preserve the phase and any bytes already returned; never retry.
        pass
    finally:
        try:
            port.close()
        except OSError:
            close_failed = True
    transcript = Transcript(
        frame,
        before,
        response,
        attempted,
        written,
        issue,
        close_failed,
        started,
        datetime.now(UTC).isoformat(),
    )
    if not attempted:
        return Rejected(transcript)
    if issue != "none" or close_failed:
        return Uncertain(transcript)
    return TransportComplete(transcript)
