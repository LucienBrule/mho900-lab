"""One bounded classic-PCAP record decoder shared by all offline consumers."""

import hashlib
import os
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Literal

from .models import CaptureLimits, CaptureMetadata, TransportIssue


class Rejection(Exception):
    def __init__(self, code: str, message: str, frame: int | None = None) -> None:
        self.issue = TransportIssue(code=code, message=message, frame_number=frame)
        super().__init__(message)


def require(condition: bool, code: str, message: str, frame: int | None = None) -> None:
    if not condition:
        raise Rejection(code, message, frame)


@dataclass(frozen=True)
class CaptureFormat:
    byte_order: Literal["little", "big"]
    timestamp_resolution: Literal["microsecond", "nanosecond"]
    fraction_limit: int
    snapshot_length: int


@dataclass(frozen=True)
class FileIdentity:
    device: int
    inode: int
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int

    @classmethod
    def read(cls, value: os.stat_result) -> "FileIdentity":
        return cls(
            device=value.st_dev,
            inode=value.st_ino,
            mode=value.st_mode,
            size=value.st_size,
            mtime_ns=value.st_mtime_ns,
            ctime_ns=value.st_ctime_ns,
        )


class Reader:
    def __init__(self, stream: BinaryIO, limits: CaptureLimits) -> None:
        self.stream = stream
        self.limits = limits
        self.bytes_read = 0
        self.digest = hashlib.sha256()

    def read(self, length: int) -> bytes:
        require(
            self.bytes_read + length <= self.limits.max_capture_bytes,
            "capture-limit",
            "capture byte limit exceeded",
        )
        value = self.stream.read(length)
        self.bytes_read += len(value)
        self.digest.update(value)
        return value


def capture_format(raw: bytes, limits: CaptureLimits) -> CaptureFormat:
    require(len(raw) == 24, "truncated-header", "classic PCAP requires a complete 24-byte header")
    magic = raw[:4]
    order: Literal["little", "big"]
    resolution: Literal["microsecond", "nanosecond"]
    if magic == b"\xd4\xc3\xb2\xa1":
        order = "little"
        resolution = "microsecond"
    elif magic == b"\xa1\xb2\xc3\xd4":
        order = "big"
        resolution = "microsecond"
    elif magic == b"\x4d\x3c\xb2\xa1":
        order = "little"
        resolution = "nanosecond"
    elif magic == b"\xa1\xb2\x3c\x4d":
        order = "big"
        resolution = "nanosecond"
    else:
        raise Rejection(
            "unsupported-format", "only classic PCAP is supported; PCAPNG is unsupported"
        )
    require(
        int.from_bytes(raw[4:6], order) == 2 and int.from_bytes(raw[6:8], order) == 4,
        "unsupported-version",
        "only classic PCAP version 2.4 is supported",
    )
    require(int.from_bytes(raw[20:24], order) == 1, "unsupported-linktype", "Ethernet required")
    snapshot = int.from_bytes(raw[16:20], order)
    require(14 <= snapshot <= limits.max_frame_bytes, "snapshot-limit", "invalid snapshot length")
    return CaptureFormat(
        byte_order=order,
        timestamp_resolution=resolution,
        fraction_limit=1_000_000 if resolution == "microsecond" else 1_000_000_000,
        snapshot_length=snapshot,
    )


@dataclass(frozen=True)
class CapturedFrame:
    number: int
    data: bytes


def scan_records(
    stream: BinaryIO,
    limits: CaptureLimits,
    consume: Callable[[CapturedFrame], None] | None = None,
) -> CaptureMetadata:
    reader = Reader(stream, limits)
    format_value = capture_format(reader.read(24), limits)
    frames = 0
    while True:
        # A one-byte EOF probe permits captures exactly at the declared byte cap.
        prefix = stream.read(1)
        if not prefix:
            break
        require(
            reader.bytes_read + 16 <= limits.max_capture_bytes,
            "capture-limit",
            "record exceeds byte limit",
        )
        reader.bytes_read += 1
        reader.digest.update(prefix)
        record = prefix + reader.read(15)
        require(len(record) == 16, "truncated-record", "incomplete PCAP record header", frames + 1)
        frames += 1
        require(
            frames <= limits.max_frames,
            "frame-limit",
            "capture frame limit exceeded",
            frames,
        )
        order = format_value.byte_order
        fraction = int.from_bytes(record[4:8], order)
        captured = int.from_bytes(record[8:12], order)
        original = int.from_bytes(record[12:16], order)
        require(
            fraction < format_value.fraction_limit,
            "invalid-timestamp",
            "timestamp fraction out of range",
            frames,
        )
        require(
            captured == original, "truncated-frame", "capture truncation cannot be accepted", frames
        )
        require(
            14 <= captured <= format_value.snapshot_length,
            "frame-length",
            "frame extent outside snapshot length",
            frames,
        )
        raw = reader.read(captured)
        require(len(raw) == captured, "truncated-frame", "incomplete captured packet bytes", frames)
        if consume is not None:
            consume(CapturedFrame(number=frames, data=raw))
    return CaptureMetadata(
        capture_sha256=reader.digest.hexdigest(),
        capture_bytes=reader.bytes_read,
        capture_frames=frames,
        timestamp_resolution=format_value.timestamp_resolution,
        byte_order=format_value.byte_order,
        snapshot_length=format_value.snapshot_length,
    )


@contextmanager
def capture_source(path: Path, limits: CaptureLimits) -> Iterator[BinaryIO]:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = FileIdentity.read(os.fstat(descriptor))
        require(stat.S_ISREG(before.mode), "not-regular", "capture must be a regular file")
        require(
            before.size <= limits.max_capture_bytes, "capture-limit", "capture exceeds byte limit"
        )
        stream = os.fdopen(descriptor, "rb")
        descriptor = None
        with stream:
            yield stream
            after = FileIdentity.read(os.fstat(stream.fileno()))
            named = FileIdentity.read(os.stat(path, follow_symlinks=False))
            require(before == after == named, "capture-changed", "capture changed during reading")
            require(
                stream.tell() == before.size,
                "capture-changed",
                "read size differs from file extent",
            )
    finally:
        if descriptor is not None:
            os.close(descriptor)
