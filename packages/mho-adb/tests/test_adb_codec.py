"""Synthetic framing controls; no ADB executable or connection is invoked."""

import hashlib
from dataclasses import dataclass
from typing import Never

import pytest
from pydantic import ValidationError

from mho_adb import (
    AuthFrame,
    CloseFrame,
    ConnectFrame,
    DecodeAccepted,
    DecodeLimits,
    DecodeRejected,
    OkayFrame,
    OpenFrame,
    WriteFrame,
    decode,
)


def wire(
    command: bytes, arg0: int, arg1: int, payload: bytes = b"", *, checksum: int | None = None
) -> bytes:
    return (
        command
        + arg0.to_bytes(4, "little")
        + arg1.to_bytes(4, "little")
        + len(payload).to_bytes(4, "little")
        + ((sum(payload) & 0xFFFFFFFF) if checksum is None else checksum).to_bytes(4, "little")
        + (int.from_bytes(command, "little") ^ 0xFFFFFFFF).to_bytes(4, "little")
        + payload
    )


def test_six_variants_exact_bytes_offsets_and_properties() -> None:
    packets = [
        wire(b"CNXN", 0x1000000, 4096, b"host::PRIVATE_BANNER\0"),
        wire(b"AUTH", 1, 0, bytes(range(20))),
        wire(b"OPEN", 100, 0, b"shell:PRIVATE_COMMAND\0"),
        wire(b"OKAY", 200, 100),
        wire(b"WRTE", 100, 200, b"\x00\xffPRIVATE_BODY\n"),
        wire(b"CLSE", 0, 100),
    ]
    raw = b"".join(packets)
    result = decode(raw)
    assert isinstance(result, DecodeAccepted)
    assert result.raw == raw and result.raw_bytes == len(raw)
    assert result.raw_sha256 == hashlib.sha256(raw).hexdigest()
    assert b"".join(frame.wire for frame in result.frames) == raw
    offset = 0
    for frame, packet in zip(result.frames, packets, strict=True):
        assert frame.offset == offset and frame.wire == packet and frame.payload == packet[24:]
        offset += len(packet)
    connect, auth, opened, okay, written, closed = result.frames
    assert (
        isinstance(connect, ConnectFrame)
        and connect.version == 0x1000000
        and connect.maxdata == 4096
    )
    assert isinstance(auth, AuthFrame)
    assert isinstance(opened, OpenFrame) and opened.local_id == 100
    assert isinstance(okay, OkayFrame) and okay.local_id == 200 and okay.remote_id == 100
    assert isinstance(written, WriteFrame) and written.local_id == 100 and written.remote_id == 200
    assert isinstance(closed, CloseFrame) and closed.local_id == 0 and closed.remote_id == 100
    assert "PRIVATE" not in repr(result)
    assert (
        result.handshake_compatibility_proven is False and result.state_machine_validated is False
    )
    assert result.physical_origin_proven is False and result.device_execution_proven is False


@pytest.mark.parametrize("size", range(1, 24))
def test_truncated_header_preserves_prefix_and_offset(size: int) -> None:
    first = wire(b"OKAY", 1, 2)
    raw = first + wire(b"WRTE", 1, 2, b"PRIVATE")[:size]
    result = decode(raw)
    assert isinstance(result, DecodeRejected)
    assert result.issue.code == "truncated-header" and result.issue.byte_offset == len(first)
    assert len(result.prefix) == 1 and result.prefix[0].wire == first
    assert result.raw == raw and "PRIVATE" not in repr(result)


def test_truncated_payload_and_corruption_rejected() -> None:
    raw = wire(b"WRTE", 1, 2, b"data")
    result = decode(raw[:-1])
    assert isinstance(result, DecodeRejected) and result.issue.code == "truncated-payload"
    changed = decode(raw[:-1] + b"X")
    assert isinstance(changed, DecodeRejected) and changed.issue.code == "payload-checksum"
    changed = decode(raw[:20] + bytes(4) + raw[24:])
    assert isinstance(changed, DecodeRejected) and changed.issue.code == "command-complement"


@pytest.mark.parametrize("command", [b"SYNC", b"XXXX", b"open", b"\0\0\0\0"])
def test_unknown_and_internal_commands_rejected(command: bytes) -> None:
    result = decode(wire(command, 1, 2))
    assert isinstance(result, DecodeRejected) and result.issue.code == "unsupported-command"


def test_checksum_is_additive_not_crc_and_zero_is_not_omission() -> None:
    rejected = decode(wire(b"WRTE", 1, 2, b"PRIVATE", checksum=0))
    assert isinstance(rejected, DecodeRejected) and rejected.issue.code == "payload-checksum"
    assert isinstance(decode(wire(b"WRTE", 1, 2, b"\0\0\0")), DecodeAccepted)
    assert isinstance(decode(wire(b"WRTE", 1, 2, b"\xff\x80\x01", checksum=384)), DecodeAccepted)


def test_checksum_wrap_and_recorded_custom_limits() -> None:
    payload = b"\xff" * 17_000_000
    limits = DecodeLimits(max_payload_bytes=len(payload))
    result = decode(wire(b"WRTE", 1, 2, payload), limits)
    assert isinstance(result, DecodeAccepted)
    assert result.frames[0].checksum == (255 * len(payload)) % 2**32
    assert result.limits == limits


@dataclass(frozen=True)
class InvalidFields:
    command: bytes
    first: int
    second: int
    payload: bytes = b""


@pytest.mark.parametrize(
    "case",
    [
        InvalidFields(b"CNXN", 0x1000000, 0),
        InvalidFields(b"AUTH", 0, 0),
        InvalidFields(b"AUTH", 4, 0),
        InvalidFields(b"AUTH", 1, 1),
        InvalidFields(b"OPEN", 0, 0),
        InvalidFields(b"OPEN", 1, 1),
        InvalidFields(b"OKAY", 0, 1),
        InvalidFields(b"OKAY", 1, 0),
        InvalidFields(b"OKAY", 1, 2, b"x"),
        InvalidFields(b"CLSE", 1, 0),
        InvalidFields(b"CLSE", 0, 1, b"x"),
        InvalidFields(b"WRTE", 0, 1),
        InvalidFields(b"WRTE", 1, 0),
    ],
)
def test_supported_command_fields_rejected_when_invalid(case: InvalidFields) -> None:
    result = decode(wire(case.command, case.first, case.second, case.payload))
    assert isinstance(result, DecodeRejected) and result.issue.code.endswith("-fields")


@pytest.mark.parametrize("subtype", [1, 2, 3])
def test_auth_bodies_are_opaque_and_unverified(subtype: int) -> None:
    result = decode(wire(b"AUTH", subtype, 0, b"\xff\0PRIVATE"))
    assert isinstance(result, DecodeAccepted) and isinstance(result.frames[0], AuthFrame)
    assert result.frames[0].payload == b"\xff\0PRIVATE"
    assert result.handshake_compatibility_proven is False


def test_limits_reject_before_interpreting_extra_frames() -> None:
    raw = wire(b"OKAY", 1, 2) * 2
    count = decode(raw, DecodeLimits(max_frames=1))
    assert isinstance(count, DecodeRejected) and count.issue.code == "frame-limit"
    assert len(count.prefix) == 1 and count.issue.byte_offset == 24
    total = decode(raw, DecodeLimits(max_stream_bytes=24))
    assert isinstance(total, DecodeRejected) and total.issue.code == "stream-limit"
    assert total.prefix == () and total.issue.byte_offset == 0
    payload = decode(wire(b"WRTE", 1, 2, b"ab"), DecodeLimits(max_payload_bytes=1))
    assert isinstance(payload, DecodeRejected) and payload.issue.code == "payload-limit"
    with pytest.raises(ValidationError):
        DecodeLimits(max_frames=True)


def test_empty_stream_is_zero_frames_not_a_handshake() -> None:
    result = decode(b"")
    assert isinstance(result, DecodeAccepted) and result.frames == ()
    assert result.handshake_compatibility_proven is False


def test_opaque_connect_version_and_open_body_are_not_normalized() -> None:
    body = b"\xffNO_NUL\0MIDDLE\0"
    result = decode(wire(b"CNXN", 0xFFFFFFFF, 1, b"raw") + wire(b"OPEN", 1, 0, body))
    assert isinstance(result, DecodeAccepted)
    assert result.frames[1].payload == body
    assert result.handshake_compatibility_proven is False


def test_oversize_stream_does_not_hash_or_decode(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_hash(raw: bytes) -> Never:
        raise AssertionError("oversize input must not be hashed")

    monkeypatch.setattr("mho_adb.codec.hashlib.sha256", forbidden_hash)
    raw = b"PRIVATE_OVERSIZE"
    result = decode(raw, DecodeLimits(max_stream_bytes=1))
    assert isinstance(result, DecodeRejected)
    assert result.raw_sha256 is None and result.raw_bytes == len(raw)
    assert result.prefix == () and result.issue.byte_offset == 0
    assert result.raw is raw and "PRIVATE" not in repr(result)


def test_unchecked_limits_rejected_without_hash_or_private_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_hash(raw: bytes) -> Never:
        raise AssertionError("invalid limits must not reach hashing")

    monkeypatch.setattr("mho_adb.codec.hashlib.sha256", forbidden_hash)
    limits = DecodeLimits.model_construct(max_stream_bytes=10**12)
    result = decode(b"PRIVATE", limits)
    assert isinstance(result, DecodeRejected)
    assert result.issue.code == "invalid-limits" and result.raw_sha256 is None
    assert "PRIVATE" not in repr(result)


def test_bytes_subclasses_are_not_coerced_into_wire_evidence() -> None:
    class BytesSubclass(bytes):
        pass

    with pytest.raises(TypeError, match="requires immutable bytes"):
        decode(BytesSubclass(b"PRIVATE"))
