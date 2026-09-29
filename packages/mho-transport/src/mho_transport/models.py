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


@dataclass(frozen=True)
class CaptureInspectionRequest:
    capture: Path
    limits: CaptureLimits = field(default_factory=CaptureLimits)


@dataclass(frozen=True)
class CaptureMetadata:
    capture_sha256: str
    capture_bytes: int
    capture_frames: int
    timestamp_resolution: Literal["microsecond", "nanosecond"]
    byte_order: Literal["little", "big"]
    snapshot_length: int
    scope: Literal["classic-ethernet-record-structure"] = "classic-ethernet-record-structure"
    protocols_validated: Literal[False] = False


@dataclass(frozen=True)
class CaptureInspectionAccepted:
    metadata: CaptureMetadata
    kind: Literal["capture-inspection-accepted"] = field(
        default="capture-inspection-accepted", init=False
    )


@dataclass(frozen=True)
class CaptureInspectionRejected:
    issue: TransportIssue
    kind: Literal["capture-inspection-rejected"] = field(
        default="capture-inspection-rejected", init=False
    )


class TcpdumpStatistics(BaseModel):
    """Observed cumulative counts under the explicit terminal text profile."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    captured: int = Field(ge=0, le=(1 << 64) - 1)
    received_by_filter: int = Field(ge=0, le=(1 << 64) - 1)
    dropped_by_kernel: int = Field(ge=0, le=(1 << 64) - 1)
    raw_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_bytes: int = Field(ge=1, le=1024**2)
    group_count: int = Field(ge=1)
    any_observed_drops: bool
    profile: Literal["tcpdump-terminal-counts/1"] = "tcpdump-terminal-counts/1"


@dataclass(frozen=True)
class TcpdumpStatisticsParsed:
    statistics: TcpdumpStatistics
    kind: Literal["tcpdump-statistics-parsed"] = field(
        default="tcpdump-statistics-parsed", init=False
    )


@dataclass(frozen=True)
class TcpdumpStatisticsRejected:
    issue: TransportIssue
    kind: Literal["tcpdump-statistics-rejected"] = field(
        default="tcpdump-statistics-rejected", init=False
    )


@dataclass(frozen=True)
class CaptureAssessmentRequest:
    capture: CaptureMetadata
    statistics: TcpdumpStatistics


@dataclass(frozen=True)
class CaptureAssessmentAccepted:
    capture: CaptureMetadata
    statistics: TcpdumpStatistics
    process_exit_proven: Literal[False] = False
    wire_completeness_proven: Literal[False] = False
    drop_reporting_support_established: Literal[False] = False
    kind: Literal["capture-assessment-accepted"] = field(
        default="capture-assessment-accepted", init=False
    )


@dataclass(frozen=True)
class CaptureAssessmentRejected:
    issue: TransportIssue
    kind: Literal["capture-assessment-rejected"] = field(
        default="capture-assessment-rejected", init=False
    )
