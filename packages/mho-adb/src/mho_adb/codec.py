"""Structural six-command ADB profile with mandatory additive payload checksum.

Based on the pinned Android 7.1.2 transport implementation, not the historical
protocol text's CRC32 label. No checksum omission fallback or state negotiation.
"""

import hashlib
from dataclasses import dataclass

from pydantic import ValidationError

from .models import (
    AuthFrame,
    CloseFrame,
    ConnectFrame,
    DecodeAccepted,
    DecodeIssue,
    DecodeLimits,
    DecodeRejected,
    Frame,
    OkayFrame,
    OpenFrame,
    WriteFrame,
)

DEFAULT_LIMITS = DecodeLimits()
COMMANDS = frozenset((b"CNXN", b"AUTH", b"OPEN", b"OKAY", b"CLSE", b"WRTE"))


class DecodeFailure(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise DecodeFailure(code, message)


@dataclass(frozen=True)
class Header:
    command: bytes
    arg0: int
    arg1: int
    payload_bytes: int
    checksum: int


def header(raw: bytes, offset: int, limits: DecodeLimits) -> Header:
    require(len(raw) - offset >= 24, "truncated-header", "incomplete 24-byte frame header")
    command = raw[offset : offset + 4]
    require(command in COMMANDS, "unsupported-command", "command is outside six-command profile")
    magic = int.from_bytes(raw[offset + 20 : offset + 24], "little")
    require(
        magic == (int.from_bytes(command, "little") ^ 0xFFFFFFFF),
        "command-complement",
        "header command complement does not match",
    )
    value = Header(
        command=command,
        arg0=int.from_bytes(raw[offset + 4 : offset + 8], "little"),
        arg1=int.from_bytes(raw[offset + 8 : offset + 12], "little"),
        payload_bytes=int.from_bytes(raw[offset + 12 : offset + 16], "little"),
        checksum=int.from_bytes(raw[offset + 16 : offset + 20], "little"),
    )
    require(
        value.payload_bytes <= limits.max_payload_bytes,
        "payload-limit",
        "declared frame payload exceeds configured bound",
    )
    require(
        value.payload_bytes <= len(raw) - offset - 24,
        "truncated-payload",
        "declared payload extends beyond retained bytes",
    )
    return value


def frame(value: Header, raw: bytes, offset: int) -> Frame:
    end = offset + 24 + value.payload_bytes
    payload = raw[offset + 24 : end]
    require(
        (sum(payload) & 0xFFFFFFFF) == value.checksum,
        "payload-checksum",
        "mandatory additive payload checksum does not match",
    )
    wire = raw[offset:end]
    first, second = value.arg0, value.arg1
    if value.command == b"CNXN":
        require(second != 0, "connect-fields", "CONNECT maximum payload must be nonzero")
        return ConnectFrame(offset, first, second, value.checksum, wire, payload)
    if value.command == b"AUTH":
        require(
            first in (1, 2, 3) and second == 0,
            "auth-fields",
            "AUTH requires known subtype and zero second argument",
        )
        return AuthFrame(offset, first, second, value.checksum, wire, payload)
    if value.command == b"OPEN":
        require(
            first != 0 and second == 0,
            "open-fields",
            "OPEN requires nonzero local identifier and zero remote identifier",
        )
        return OpenFrame(offset, first, second, value.checksum, wire, payload)
    if value.command == b"OKAY":
        require(
            first != 0 and second != 0 and not payload,
            "okay-fields",
            "OKAY requires nonzero identifiers and empty payload",
        )
        return OkayFrame(offset, first, second, value.checksum, wire, payload)
    if value.command == b"CLSE":
        require(
            second != 0 and not payload,
            "close-fields",
            "CLOSE requires nonzero remote identifier and empty payload",
        )
        return CloseFrame(offset, first, second, value.checksum, wire, payload)
    require(first != 0 and second != 0, "write-fields", "WRITE requires nonzero stream identifiers")
    return WriteFrame(offset, first, second, value.checksum, wire, payload)


def decode(raw: bytes, limits: DecodeLimits = DEFAULT_LIMITS) -> DecodeAccepted | DecodeRejected:
    """Decode exact retained bytes; accepted frames imply no handshake or action success."""
    if type(raw) is not bytes:
        raise TypeError("decoder requires immutable bytes")
    if not isinstance(limits, DecodeLimits):
        raise TypeError("decoder requires DecodeLimits")
    digest: str | None = None
    offset = 0
    frames: list[Frame] = []
    try:
        try:
            limits = DecodeLimits(
                max_stream_bytes=limits.max_stream_bytes,
                max_frames=limits.max_frames,
                max_payload_bytes=limits.max_payload_bytes,
            )
        except ValidationError as error:
            raise DecodeFailure(
                "invalid-limits", "decoder limits are outside supported bounds"
            ) from error
        require(
            len(raw) <= limits.max_stream_bytes,
            "stream-limit",
            "retained stream exceeds configured byte bound",
        )
        digest = hashlib.sha256(raw).hexdigest()
        while offset < len(raw):
            require(
                len(frames) < limits.max_frames,
                "frame-limit",
                "frame count exceeds configured bound",
            )
            value = header(raw, offset, limits)
            decoded = frame(value, raw, offset)
            frames.append(decoded)
            offset += len(decoded.wire)
        return DecodeAccepted(digest, len(raw), tuple(frames), raw, limits=limits)
    except DecodeFailure as error:
        return DecodeRejected(
            DecodeIssue(error.code, error.message, offset), tuple(frames), digest, len(raw), raw
        )
