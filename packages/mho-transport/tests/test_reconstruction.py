"""Synthetic captures with exact selected endpoints and independently built headers."""

import hashlib
import os
from dataclasses import dataclass
from ipaddress import IPv4Address
from pathlib import Path
from typing import BinaryIO, Literal

import pytest
from pydantic import ValidationError

import mho_transport.reconstruction as parser
from mho_transport import (
    CaptureLimits,
    Endpoint,
    TranscriptAccepted,
    TranscriptRejected,
    TranscriptRequest,
    reconstruct,
)

CLIENT = Endpoint(address=IPv4Address("192.0.2.10"), port=41000)
SERVER = Endpoint(address=IPv4Address("198.51.100.20"), port=7654)


@dataclass(frozen=True)
class Packet:
    sequence: int
    flags: int = 0x10
    payload: bytes = b""
    reply: bool = False
    fragment: int = 0
    port_override: int | None = None


def frame(packet: Packet) -> bytes:
    source = SERVER if packet.reply else CLIENT
    destination = CLIENT if packet.reply else SERVER
    port = source.port if packet.port_override is None else packet.port_override
    tcp = (
        port.to_bytes(2, "big")
        + destination.port.to_bytes(2, "big")
        + (packet.sequence % (1 << 32)).to_bytes(4, "big")
        + bytes(4)
        + bytes([0x50, packet.flags])
        + bytes(6)
        + packet.payload
    )
    ip = (
        b"\x45\0"
        + (20 + len(tcp)).to_bytes(2, "big")
        + bytes(2)
        + packet.fragment.to_bytes(2, "big")
        + b"\x40\x06"
        + bytes(2)
        + source.address.packed
        + destination.address.packed
        + tcp
    )
    return bytes(12) + b"\x08\0" + ip


def pcap(
    frames: list[bytes],
    order: Literal["little", "big"] = "little",
    nano: bool = False,
) -> bytes:
    magic = 0xA1B23C4D if nano else 0xA1B2C3D4
    header = (
        magic.to_bytes(4, order)
        + (2).to_bytes(2, order)
        + (4).to_bytes(2, order)
        + bytes(8)
        + (262144).to_bytes(4, order)
        + (1).to_bytes(4, order)
    )
    records: list[bytes] = []
    for index, raw in enumerate(frames):
        records.append(
            (1700000000 + index).to_bytes(4, order)
            + (12345).to_bytes(4, order)
            + len(raw).to_bytes(4, order)
            + len(raw).to_bytes(4, order)
            + raw
        )
    return header + b"".join(records)


def packets(origin: int = 100) -> list[Packet]:
    return [
        Packet(sequence=origin, flags=2),
        Packet(sequence=500, flags=0x12, reply=True),
        Packet(sequence=origin + 1, payload=b"request"),
        Packet(sequence=501, payload=b"reply", reply=True),
        Packet(sequence=origin + 8, flags=0x11),
        Packet(sequence=506, flags=0x11, reply=True),
    ]


def run(
    tmp_path: Path,
    frames: list[bytes],
    limits: CaptureLimits | None = None,
) -> TranscriptAccepted | TranscriptRejected:
    capture = tmp_path / "capture.pcap"
    capture.write_bytes(pcap(frames))
    return reconstruct(
        TranscriptRequest(
            capture=capture,
            client=CLIENT,
            server=SERVER,
            limits=limits if limits is not None else CaptureLimits(),
        )
    )


@pytest.mark.parametrize("order", ["little", "big"])
@pytest.mark.parametrize("nano", [False, True])
def test_classic_formats(tmp_path: Path, order: Literal["little", "big"], nano: bool) -> None:
    capture = tmp_path / "capture.pcap"
    encoded = pcap([frame(packet) for packet in packets()], order, nano)
    capture.write_bytes(encoded)
    result = reconstruct(TranscriptRequest(capture=capture, client=CLIENT, server=SERVER))
    assert isinstance(result, TranscriptAccepted)
    assert result.request == b"request" and result.reply == b"reply"
    assert result.metadata.capture_sha256 == hashlib.sha256(encoded).hexdigest()
    assert result.metadata.capture_bytes == len(encoded)
    assert result.metadata.capture_frames == result.metadata.selected_tcp_frames == 6
    assert result.metadata.byte_order == order
    assert result.metadata.timestamp_resolution == ("nanosecond" if nano else "microsecond")
    assert result.metadata.checksums_verified is False


def test_wrap_out_of_order_overlap_retransmission(tmp_path: Path) -> None:
    origin = 0xFFFFFFFC
    pieces = [
        Packet(sequence=origin + 4, payload=b"uest"),
        Packet(sequence=origin, flags=2),
        Packet(sequence=origin + 1, payload=b"requ"),
        Packet(sequence=origin + 3, payload=b"quest"),
        Packet(sequence=origin, flags=2),
        Packet(sequence=origin + 8, flags=0x11),
        Packet(sequence=506, flags=0x11, reply=True),
        Packet(sequence=501, payload=b"reply", reply=True),
        Packet(sequence=500, flags=0x12, reply=True),
    ]
    result = run(tmp_path, [frame(packet) for packet in pieces])
    assert isinstance(result, TranscriptAccepted)
    assert result.request == b"request" and result.reply == b"reply"
    assert result.metadata.retransmitted_bytes == 6
    assert result.metadata.client_syn == origin and result.metadata.client_fin_extent == 7


def test_syn_payload_fin_payload_and_empty_reply(tmp_path: Path) -> None:
    pieces = [
        Packet(sequence=100, flags=2, payload=b"first"),
        Packet(sequence=106, flags=0x11, payload=b"last"),
        Packet(sequence=500, flags=0x12, reply=True),
        Packet(sequence=501, flags=0x11, reply=True),
    ]
    result = run(tmp_path, [frame(packet) for packet in pieces])
    assert isinstance(result, TranscriptAccepted)
    assert result.request == b"firstlast" and result.reply == b""


@pytest.mark.parametrize(
    "mutation",
    [
        "gap",
        "conflict",
        "reset",
        "missing-syn",
        "missing-fin",
        "second-syn",
        "second-fin",
        "fragment",
    ],
)
def test_selected_connection_rejects_uncertain_stream(tmp_path: Path, mutation: str) -> None:
    pieces = packets()
    if mutation == "gap":
        pieces[2] = Packet(sequence=102, payload=b"equest")
    elif mutation == "conflict":
        pieces.append(Packet(sequence=101, payload=b"X"))
    elif mutation == "reset":
        pieces.append(Packet(sequence=108, flags=4))
    elif mutation == "missing-syn":
        pieces.pop(0)
    elif mutation == "missing-fin":
        pieces.pop(4)
    elif mutation == "second-syn":
        pieces.append(Packet(sequence=999, flags=2))
    elif mutation == "second-fin":
        pieces.append(Packet(sequence=109, flags=1))
    else:
        pieces[2] = Packet(sequence=101, payload=b"request", fragment=0x2000)
    assert isinstance(run(tmp_path, [frame(packet) for packet in pieces]), TranscriptRejected)


@pytest.mark.parametrize(
    "mutation", ["header", "record", "frame", "snap-truncated", "pcapng", "timestamp", "vlan"]
)
def test_capture_shape_rejections(tmp_path: Path, mutation: str) -> None:
    encoded = pcap([frame(packet) for packet in packets()])
    if mutation == "header":
        encoded = encoded[:10]
    elif mutation == "record":
        encoded += b"bad"
    elif mutation == "frame":
        encoded = encoded[:-1]
    elif mutation == "snap-truncated":
        raw = bytearray(encoded)
        raw[36:40] = (999).to_bytes(4, "little")
        encoded = bytes(raw)
    elif mutation == "pcapng":
        encoded = b"\x0a\x0d\x0d\x0a" + encoded[4:]
    elif mutation == "timestamp":
        raw = bytearray(encoded)
        raw[28:32] = (1_000_000).to_bytes(4, "little")
        encoded = bytes(raw)
    else:
        raw = bytearray(encoded)
        raw[52:54] = b"\x81\0"
        encoded = bytes(raw)
    capture = tmp_path / "bad.pcap"
    capture.write_bytes(encoded)
    assert isinstance(
        reconstruct(TranscriptRequest(capture=capture, client=CLIENT, server=SERVER)),
        TranscriptRejected,
    )


def test_unselected_and_ipv6_frames_are_only_counted(tmp_path: Path) -> None:
    frames = [frame(packet) for packet in packets()]
    frames.extend([frame(Packet(sequence=0, flags=4, port_override=9999)), bytes(12) + b"\x86\xdd"])
    result = run(tmp_path, frames)
    assert isinstance(result, TranscriptAccepted)
    assert result.metadata.ignored_frames == 2


@pytest.mark.parametrize("limit", ["capture", "frames", "selected", "payload", "direction"])
def test_resource_limits(tmp_path: Path, limit: str) -> None:
    limits: CaptureLimits
    if limit == "capture":
        limits = CaptureLimits(max_capture_bytes=24)
    elif limit == "frames":
        limits = CaptureLimits(max_frames=2)
    elif limit == "selected":
        limits = CaptureLimits(max_selected_frames=2)
    elif limit == "payload":
        limits = CaptureLimits(max_selected_payload_bytes=2)
    else:
        limits = CaptureLimits(max_direction_bytes=2)
    assert isinstance(
        run(tmp_path, [frame(packet) for packet in packets()], limits), TranscriptRejected
    )


def test_strict_boundaries() -> None:
    with pytest.raises(ValidationError):
        Endpoint.model_validate({"address": "192.0.2.10", "port": "123"})
    with pytest.raises(ValidationError):
        CaptureLimits(max_frames=True)


def test_equal_exact_byte_limit(tmp_path: Path) -> None:
    frames = [frame(packet) for packet in packets()]
    result = run(tmp_path, frames, CaptureLimits(max_capture_bytes=len(pcap(frames))))
    assert isinstance(result, TranscriptAccepted)


def test_changed_capture_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_parse = parser.parse

    def modify_after_parse(stream: BinaryIO, request: TranscriptRequest) -> TranscriptAccepted:
        result = original_parse(stream, request)
        request.capture.write_bytes(request.capture.read_bytes() + b"changed")
        return result

    monkeypatch.setattr(parser, "parse", modify_after_parse)
    result = run(tmp_path, [frame(packet) for packet in packets()])
    assert isinstance(result, TranscriptRejected)
    assert result.issue.code == "capture-changed"


@pytest.mark.parametrize("kind", ["fifo", "directory", "symlink"])
def test_special_capture_is_not_read(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "capture"
    if kind == "fifo":
        os.mkfifo(path)
    elif kind == "directory":
        path.mkdir()
    else:
        target = tmp_path / "real.pcap"
        target.write_bytes(pcap([frame(packet) for packet in packets()]))
        path.symlink_to(target)
    result = reconstruct(TranscriptRequest(capture=path, client=CLIENT, server=SERVER))
    assert isinstance(result, TranscriptRejected)


def test_same_endpoint_rejected(tmp_path: Path) -> None:
    result = reconstruct(
        TranscriptRequest(capture=tmp_path / "not-opened.pcap", client=CLIENT, server=CLIENT)
    )
    assert isinstance(result, TranscriptRejected)
    assert result.issue.code == "same-endpoint"


@pytest.mark.parametrize("flags", [0x20, 0x03])
def test_unsupported_selected_flags(tmp_path: Path, flags: int) -> None:
    pieces = packets()
    pieces.append(Packet(sequence=108, flags=flags))
    assert isinstance(run(tmp_path, [frame(packet) for packet in pieces]), TranscriptRejected)
