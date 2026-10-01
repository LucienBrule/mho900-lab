from pathlib import Path

import pytest
from pydantic import ValidationError

from mho_source import (
    PointCommand,
    ReadWindow,
    Rejected,
    TransportComplete,
    Uncertain,
    encode_point,
    execute,
)


def candidate() -> PointCommand:
    return PointCommand(frequency_hz=100_000_000, reference_hz=25_000_000, power_code=4)


def test_known_frames() -> None:
    assert encode_point(candidate()) == bytes.fromhex("AD 01 01 04 03 D0 90 01 86 A0 3D")
    example = PointCommand(frequency_hz=2_000_456_000, reference_hz=10_000_000, power_code=1)
    assert encode_point(example) == bytes.fromhex("AD 01 01 01 01 86 A0 1E 86 48 C3")


@pytest.mark.parametrize(
    "field,value",
    [
        ("frequency_hz", "100000000"),
        ("frequency_hz", True),
        ("frequency_hz", 100_000_001),
        ("frequency_hz", 6_000_001_000),
        ("reference_hz", 25_000_001),
        ("power_code", 0),
        ("power_code", 5),
        ("unknown", 1),
    ],
)
def test_invalid_external_input(field: str, value: object) -> None:
    values: dict[str, object] = dict(
        frequency_hz=100_000_000, reference_hz=25_000_000, power_code=4
    )
    values[field] = value
    with pytest.raises(ValidationError):
        PointCommand.model_validate(values)


class FakePort:
    def __init__(self) -> None:
        self.pre = ReadWindow()
        self.post = ReadWindow()
        self.fail = ""
        self.count = 11
        self.reads = 0
        self.writes: list[bytes] = []
        self.closed = False
        self.prepared = False

    def prepare(self) -> None:
        self.prepared = True
        if self.fail == "setup":
            raise OSError("test setup error")

    def read_window(self, seconds: float, limit: int) -> ReadWindow:
        self.reads += 1
        return self.pre if self.reads == 1 else self.post

    def write_once(self, data: bytes) -> int:
        self.writes.append(data)
        if self.fail == "write":
            raise OSError("test write error")
        return self.count

    def close(self) -> None:
        self.closed = True
        if self.fail == "close":
            raise OSError("test close error")


def noop() -> None:
    pass


@pytest.mark.parametrize("reply", [b"", b"arbitrary reply, not an ACK"])
def test_complete_is_not_device_acceptance(reply: bytes) -> None:
    port = FakePort()
    port.post = ReadWindow(reply)
    result = execute(candidate(), port, noop)
    assert isinstance(result, TransportComplete)
    assert result.transcript.response == reply
    assert port.writes == [encode_point(candidate())] and port.closed


@pytest.mark.parametrize("failure", ["setup", "write", "close"])
def test_errors_never_retry(failure: str) -> None:
    port = FakePort()
    port.fail = failure
    result = execute(candidate(), port, noop)
    assert isinstance(result, Rejected if failure == "setup" else Uncertain)
    assert len(port.writes) == (0 if failure == "setup" else 1)
    assert port.closed


def test_short_write_is_not_completed() -> None:
    port = FakePort()
    port.count = 3
    result = execute(candidate(), port, noop)
    assert isinstance(result, Uncertain)
    assert result.transcript.bytes_written == 3
    assert len(port.writes) == 1 and port.reads == 1 and port.closed


@pytest.mark.parametrize(
    "window", [ReadWindow(b"BOOT"), ReadWindow(error=True), ReadWindow(b"x", overflow=True)]
)
def test_pre_input_stops_before_write(window: ReadWindow) -> None:
    port = FakePort()
    port.pre = window
    result = execute(candidate(), port, noop)
    assert isinstance(result, Rejected) and result.transcript.before == window.data
    assert not port.writes and port.closed


@pytest.mark.parametrize(
    "window", [ReadWindow(b"partial", error=True), ReadWindow(b"x" * 4097, overflow=True)]
)
def test_post_errors_retain_bytes(window: ReadWindow) -> None:
    port = FakePort()
    port.post = window
    result = execute(candidate(), port, noop)
    assert isinstance(result, Uncertain) and result.transcript.response == window.data
    assert len(port.writes) == 1 and port.closed


def test_intent_durability_failure_stops_write(tmp_path: Path) -> None:
    port = FakePort()

    def fail() -> None:
        raise OSError("test evidence failure")

    result = execute(candidate(), port, fail)
    assert isinstance(result, Rejected) and result.transcript.issue == "write-intent-evidence"
    assert not port.writes and port.closed


def test_unchecked_model_rejected_before_open() -> None:
    port = FakePort()
    altered = candidate().model_copy(update={"power_code": 7})
    with pytest.raises(ValidationError):
        execute(altered, port, noop)
    assert not port.prepared
