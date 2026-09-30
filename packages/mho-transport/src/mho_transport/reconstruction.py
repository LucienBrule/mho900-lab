"""One selected IPv4 TCP flow; record decoding is shared with capture inspection."""

from dataclasses import dataclass, field
from ipaddress import IPv4Address
from typing import BinaryIO

from .models import (
    CaptureLimits,
    Endpoint,
    TranscriptAccepted,
    TranscriptMetadata,
    TranscriptRejected,
    TranscriptRequest,
    TransportIssue,
)
from .pcap import CapturedFrame, Rejection, capture_source, require, scan_records

MODULUS = 1 << 32


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
    connection = Connection()

    def consume(frame: CapturedFrame) -> None:
        connection.frame(frame.data, frame.number, request)

    metadata = scan_records(stream, request.limits, consume)
    client = recover(connection.request, request.limits.max_direction_bytes)
    server = recover(connection.reply, request.limits.max_direction_bytes)
    return TranscriptAccepted(
        request=client.payload,
        reply=server.payload,
        metadata=TranscriptMetadata(
            capture_sha256=metadata.capture_sha256,
            capture_bytes=metadata.capture_bytes,
            capture_frames=metadata.capture_frames,
            selected_tcp_frames=connection.selected_frames,
            ignored_frames=metadata.capture_frames - connection.selected_frames,
            retransmitted_bytes=client.retransmitted_bytes + server.retransmitted_bytes,
            client_syn=client.syn,
            server_syn=server.syn,
            client_fin_extent=client.fin_extent,
            server_fin_extent=server.fin_extent,
            timestamp_resolution=metadata.timestamp_resolution,
            byte_order=metadata.byte_order,
        ),
    )


def reconstruct(request: TranscriptRequest) -> TranscriptAccepted | TranscriptRejected:
    """Recover captured bytes only, with no delivery/device-execution conclusion."""
    try:
        request = TranscriptRequest(
            request.capture,
            Endpoint.model_validate(request.client),
            Endpoint.model_validate(request.server),
            CaptureLimits.model_validate(request.limits),
        )
    except ValueError:
        return TranscriptRejected(
            TransportIssue("invalid-contract", "endpoints or capture limits violate the contract")
        )
    try:
        require(request.client != request.server, "same-endpoint", "client and server must differ")
        with capture_source(request.capture, request.limits) as stream:
            result = parse(stream, request)
        return result
    except Rejection as error:
        return TranscriptRejected(issue=error.issue)
    except (OSError, ValueError) as error:
        return TranscriptRejected(issue=TransportIssue(code="input-error", message=str(error)))
