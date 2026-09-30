"""Strict role configuration and named offline-review outcomes."""

from dataclasses import dataclass, field
from ipaddress import IPv4Address
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from mho_evidence import ArtifactPath, Sha256, VerificationAccepted
from mho_scpi import ExchangeAccepted
from mho_transport import CaptureAssessmentAccepted, Endpoint, TranscriptAccepted


class TranscriptMembers(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    request: ArtifactPath
    reply: ArtifactPath


class ProfileEndpoint(Endpoint):
    """TOML string addresses are explicitly parsed, never resolved."""

    @field_validator("address", mode="before")
    @classmethod
    def parse_address(cls, value: object) -> IPv4Address:
        if isinstance(value, IPv4Address):
            return value
        if isinstance(value, str):
            return IPv4Address(value)
        raise ValueError("address must be an IPv4 string")


class ReviewProfile(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    schema_version: Literal["mho-review.profile/1"]
    capture: ArtifactPath
    statistics: ArtifactPath
    client: Endpoint
    server: Endpoint
    transcripts: tuple[TranscriptMembers, ...] = Field(strict=False, min_length=1, max_length=128)

    @field_validator("client", "server", mode="before")
    @classmethod
    def endpoint_edge(cls, value: object) -> Endpoint:
        if isinstance(value, Endpoint):
            return value
        return ProfileEndpoint.model_validate(value)

    @model_validator(mode="after")
    def distinct_roles(self) -> Self:
        names = [self.capture.root, self.statistics.root]
        for pair in self.transcripts:
            names.extend((pair.request.root, pair.reply.root))
        if len(set(names)) != len(names):
            raise ValueError("every role must name a distinct member")
        if self.client.address == self.server.address and self.client.port == self.server.port:
            raise ValueError("client and server must differ")
        return self


class ReviewLimits(BaseModel):
    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    max_manifest_bytes: int = Field(default=4 * 1024**2, ge=1, le=16 * 1024**2)
    max_inventory_entries: int = Field(default=4096, ge=4, le=100_000)
    max_inventory_bytes: int = Field(default=128 * 1024**2, ge=1, le=1024**3)
    max_file_bytes: int = Field(default=64 * 1024**2, ge=24, le=1024**3)
    max_depth: int = Field(default=32, ge=1, le=128)
    max_capture_frames: int = Field(default=100_000, ge=1, le=1_000_000)


@dataclass(frozen=True)
class ReviewRequest:
    root: Path
    manifest: Path
    expected_manifest_sha256: Sha256
    profile: ReviewProfile
    limits: ReviewLimits = field(default_factory=ReviewLimits)


@dataclass(frozen=True)
class ReviewIssue:
    stage: str
    code: str
    message: str


@dataclass(frozen=True)
class ProfileAccepted:
    profile: ReviewProfile
    raw_sha256: str
    kind: Literal["profile-accepted"] = field(default="profile-accepted", init=False)


@dataclass(frozen=True)
class ProfileRejected:
    issue: ReviewIssue
    kind: Literal["profile-rejected"] = field(default="profile-rejected", init=False)


@dataclass(frozen=True)
class ReviewAccepted:
    manifest_sha256: str
    profile: ReviewProfile
    inventory: VerificationAccepted
    capture_assessment: CaptureAssessmentAccepted
    transcript: TranscriptAccepted = field(repr=False)
    exchange: ExchangeAccepted = field(repr=False)
    physical_origin_proven: Literal[False] = False
    atomic_snapshot_proven: Literal[False] = False
    peer_delivery_proven: Literal[False] = False
    device_execution_proven: Literal[False] = False
    kind: Literal["review-accepted"] = field(default="review-accepted", init=False)


@dataclass(frozen=True)
class ReviewRejected:
    issue: ReviewIssue
    kind: Literal["review-rejected"] = field(default="review-rejected", init=False)
