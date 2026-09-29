"""Typed boundaries for one explicitly selected IPv4 TCP connection."""

from dataclasses import dataclass, field
from ipaddress import IPv4Address
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Endpoint(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    address: IPv4Address
    port: int = Field(ge=1, le=65535)


class CaptureLimits(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    max_capture_bytes: int = Field(default=1024**3, ge=24, le=64 * 1024**3)
    max_frames: int = Field(default=1_000_000, ge=1, le=20_000_000)
    max_frame_bytes: int = Field(default=262144, ge=54, le=1024**2)
    max_selected_frames: int = Field(default=100_000, ge=1, le=1_000_000)
    max_direction_bytes: int = Field(default=1024**2, ge=1, le=64 * 1024**2)
    max_selected_payload_bytes: int = Field(default=8 * 1024**2, ge=1, le=256 * 1024**2)


@dataclass(frozen=True)
class TranscriptRequest:
    capture: Path
    client: Endpoint
    server: Endpoint
    limits: CaptureLimits = field(default_factory=CaptureLimits)


@dataclass(frozen=True)
class TransportIssue:
    code: str
    message: str
    frame_number: int | None = None


@dataclass(frozen=True)
class TranscriptMetadata:
    capture_sha256: str
    capture_bytes: int
    capture_frames: int
    selected_tcp_frames: int
    ignored_frames: int
    retransmitted_bytes: int
    client_syn: int
    server_syn: int
    client_fin_extent: int
    server_fin_extent: int
    timestamp_resolution: Literal["microsecond", "nanosecond"]
    byte_order: Literal["little", "big"]
    checksums_verified: Literal[False] = False
    scope: Literal["one-explicit-ipv4-tcp-connection"] = "one-explicit-ipv4-tcp-connection"


@dataclass(frozen=True)
class TranscriptAccepted:
    request: bytes
    reply: bytes
    metadata: TranscriptMetadata
    kind: Literal["transcript-accepted"] = field(default="transcript-accepted", init=False)


@dataclass(frozen=True)
class TranscriptRejected:
    issue: TransportIssue
    kind: Literal["transcript-rejected"] = field(default="transcript-rejected", init=False)
