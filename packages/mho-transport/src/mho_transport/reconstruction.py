"""Classic Ethernet PCAP parsing and bounded captured-byte reconstruction.

No network operations are performed. Checksums and ACK delivery semantics are
not verified. Nonselected frames are counted, not classified as safe traffic.
"""

import hashlib
import os
import stat
from dataclasses import dataclass, field
from ipaddress import IPv4Address
from typing import BinaryIO, Literal

from .models import (
    CaptureLimits,
    TranscriptAccepted,
    TranscriptMetadata,
    TranscriptRejected,
    TranscriptRequest,
    TransportIssue,
)

MODULUS = 1 << 32


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
class Segment:
    sequence: int
    payload: bytes


@dataclass
class Direction:
    syns: set[int] = field(default_factory=set)
    fins: set[int] = field(default_factory=set)
    segments: list[Segment] = field(default_factory=list)


@dataclass(frozen=True)
class RecoveredDirection:
    payload: bytes
    retransmitted_bytes: int
    syn: int
    fin_extent: int


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


def recover(direction: Direction, limit: int) -> RecoveredDirection:
    require(len(direction.syns) == 1, "syn-origin", "missing or ambiguous SYN sequence origin")
    require(len(direction.fins) == 1, "fin-extent", "missing or ambiguous FIN sequence extent")
    syn = next(iter(direction.syns))
    origin = (syn + 1) % MODULUS
    extent = (next(iter(direction.fins)) - origin) % MODULUS
    require(extent <= limit, "direction-limit", "FIN exceeds bounded direction extent")
    data = bytearray(extent)
    coverage = bytearray(extent)
    repeated = 0
    for segment in direction.segments:
        offset = (segment.sequence - origin) % MODULUS
        require(offset + len(segment.payload) <= extent, "fin-extent", "payload lies outside FIN")
        for index, value in enumerate(segment.payload, start=offset):
            if coverage[index]:
                require(
                    data[index] == value, "conflicting-retransmission", "overlapping bytes differ"
                )
                repeated += 1
            else:
                data[index] = value
                coverage[index] = 1
    require(all(coverage), "sequence-gap", "capture does not cover every byte before FIN")
    return RecoveredDirection(
        payload=bytes(data), retransmitted_bytes=repeated, syn=syn, fin_extent=extent
    )


@dataclass
class Connection:
    request: Direction = field(default_factory=Direction)
    reply: Direction = field(default_factory=Direction)
    selected_frames: int = 0
    selected_payload_bytes: int = 0

    def frame(self, raw: bytes, number: int, request: TranscriptRequest) -> bool:
        require(len(raw) >= 14, "short-ethernet", "short Ethernet header", number)
        ethertype = int.from_bytes(raw[12:14], "big")
        require(
            ethertype not in (0x8100, 0x88A8, 0x9100),
            "unsupported-vlan",
            "VLAN-tagged captures are outside this profile",
            number,
        )
        if ethertype != 0x0800:
            return False
        require(len(raw) >= 34 and raw[14] >> 4 == 4, "invalid-ipv4", "short IPv4 header", number)
        header = (raw[14] & 15) * 4
        length = int.from_bytes(raw[16:18], "big")
        require(
            header >= 20 and length >= header and 14 + length <= len(raw),
            "invalid-ipv4",
            "invalid IPv4 header or total length",
            number,
        )
        if raw[23] != 6:
            return False
        source = IPv4Address(raw[26:30])
        destination = IPv4Address(raw[30:34])
        candidate = (
            source == request.client.address and destination == request.server.address
        ) or (source == request.server.address and destination == request.client.address)
        if not candidate:
            return False
        # Noninitial fragments do not expose ports; endpoint-address fragments
        # cannot safely be declared unrelated to the explicitly selected flow.
        require(
            int.from_bytes(raw[20:22], "big") & 0x3FFF == 0,
            "unsupported-fragmentation",
            "TCP fragmentation between selected endpoint addresses is unsupported",
            number,
        )
        tcp = 14 + header
        require(length >= header + 20, "invalid-tcp", "short TCP header", number)
        source_port = int.from_bytes(raw[tcp : tcp + 2], "big")
        destination_port = int.from_bytes(raw[tcp + 2 : tcp + 4], "big")
        if (
            source == request.client.address
            and source_port == request.client.port
            and destination == request.server.address
            and destination_port == request.server.port
        ):
            direction = self.request
        elif (
            source == request.server.address
            and source_port == request.server.port
            and destination == request.client.address
            and destination_port == request.client.port
        ):
            direction = self.reply
        else:
            return False
        self.selected_frames += 1
        require(
            self.selected_frames <= request.limits.max_selected_frames,
            "selected-frame-limit",
            "selected TCP frame limit exceeded",
            number,
        )
        size = (raw[tcp + 12] >> 4) * 4
        flags = raw[tcp + 13]
        require(size >= 20 and header + size <= length, "invalid-tcp", "invalid TCP length", number)
        require(not flags & 4, "tcp-reset", "selected TCP connection contains RST", number)
        require(not flags & 32, "unsupported-urgent", "urgent-data semantics unsupported", number)
        require(flags & 3 != 3, "invalid-tcp", "simultaneous SYN and FIN unsupported", number)
        sequence = int.from_bytes(raw[tcp + 4 : tcp + 8], "big")
        payload = raw[tcp + size : 14 + length]
        if flags & 2:
            direction.syns.add(sequence)
            require(len(direction.syns) == 1, "syn-origin", "ambiguous SYN origins", number)
        payload_sequence = (sequence + bool(flags & 2)) % MODULUS
        if payload:
            self.selected_payload_bytes += len(payload)
            require(
                self.selected_payload_bytes <= request.limits.max_selected_payload_bytes,
                "payload-limit",
                "selected payload storage budget exceeded",
                number,
            )
            direction.segments.append(Segment(sequence=payload_sequence, payload=payload))
        if flags & 1:
            direction.fins.add((payload_sequence + len(payload)) % MODULUS)
            require(len(direction.fins) == 1, "fin-extent", "ambiguous FIN extents", number)
        return True


def parse(stream: BinaryIO, request: TranscriptRequest) -> TranscriptAccepted:
    reader = Reader(stream, request.limits)
    format_value = capture_format(reader.read(24), request.limits)
    connection = Connection()
    frames = 0
    while True:
        # A one-byte EOF probe permits captures exactly at the declared byte cap.
        prefix = stream.read(1)
        if not prefix:
            break
        require(
            reader.bytes_read + 16 <= request.limits.max_capture_bytes,
            "capture-limit",
            "record exceeds byte limit",
        )
        reader.bytes_read += 1
        reader.digest.update(prefix)
        record = prefix + reader.read(15)
        require(len(record) == 16, "truncated-record", "incomplete PCAP record header", frames + 1)
        frames += 1
        require(
            frames <= request.limits.max_frames,
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
        connection.frame(raw, frames, request)
    client = recover(connection.request, request.limits.max_direction_bytes)
    server = recover(connection.reply, request.limits.max_direction_bytes)
    return TranscriptAccepted(
        request=client.payload,
        reply=server.payload,
        metadata=TranscriptMetadata(
            capture_sha256=reader.digest.hexdigest(),
            capture_bytes=reader.bytes_read,
            capture_frames=frames,
            selected_tcp_frames=connection.selected_frames,
            ignored_frames=frames - connection.selected_frames,
            retransmitted_bytes=client.retransmitted_bytes + server.retransmitted_bytes,
            client_syn=client.syn,
            server_syn=server.syn,
            client_fin_extent=client.fin_extent,
            server_fin_extent=server.fin_extent,
            timestamp_resolution=format_value.timestamp_resolution,
            byte_order=format_value.byte_order,
        ),
    )


def reconstruct(request: TranscriptRequest) -> TranscriptAccepted | TranscriptRejected:
    """Recover captured bytes only, with no delivery/device-execution conclusion."""
    descriptor: int | None = None
    try:
        require(request.client != request.server, "same-endpoint", "client and server must differ")
        descriptor = os.open(request.capture, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = FileIdentity.read(os.fstat(descriptor))
        require(stat.S_ISREG(before.mode), "not-regular", "capture must be a regular file")
        require(
            before.size <= request.limits.max_capture_bytes,
            "capture-limit",
            "capture exceeds byte limit",
        )
        stream = os.fdopen(descriptor, "rb")
        descriptor = None
        with stream:
            result = parse(stream, request)
            after = FileIdentity.read(os.fstat(stream.fileno()))
            named = FileIdentity.read(os.stat(request.capture, follow_symlinks=False))
            require(
                before == after == named, "capture-changed", "capture changed during reconstruction"
            )
            require(
                result.metadata.capture_bytes == before.size,
                "capture-changed",
                "read size differs from file extent",
            )
        return result
    except Rejection as error:
        return TranscriptRejected(issue=error.issue)
    except (OSError, ValueError) as error:
        return TranscriptRejected(issue=TransportIssue(code="input-error", message=str(error)))
    finally:
        if descriptor is not None:
            os.close(descriptor)
