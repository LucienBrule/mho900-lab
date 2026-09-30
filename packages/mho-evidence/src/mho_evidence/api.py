"""Named requests and outcomes; none asserts instrument provenance or atomicity."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True)
class SealRequest:
    root: Path
    output: Path
    allow_empty: bool = False


class VerificationLimits(BaseModel):
    """Optional byte/count/depth bounds; no blocking-filesystem deadline claim."""

    model_config = ConfigDict(
        frozen=True, strict=True, extra="forbid", revalidate_instances="always"
    )
    max_entries: int = Field(default=10000, ge=1, le=1000000)
    max_total_bytes: int = Field(default=1024**3, ge=1, le=1024**4)
    max_file_bytes: int = Field(default=1024**3, ge=1, le=1024**4)
    max_depth: int = Field(default=32, ge=0, le=128)
    max_manifest_bytes: int = Field(default=4 * 1024**2, ge=1, le=64 * 1024**2)


@dataclass(frozen=True)
class VerifyRequest:
    root: Path
    manifest: Path
    limits: VerificationLimits | None = None


@dataclass(frozen=True)
class EvidenceIssue:
    code: str
    message: str
    path: str | None = None


@dataclass(frozen=True)
class SealCreated:
    output: Path
    manifest_sha256: str
    artifact_count: int
    total_bytes: int
    kind: Literal["seal-created"] = field(default="seal-created", init=False)


@dataclass(frozen=True)
class SealRejected:
    issue: EvidenceIssue
    kind: Literal["seal-rejected"] = field(default="seal-rejected", init=False)


@dataclass(frozen=True)
class SealPublishedUncertain:
    output: Path
    manifest_sha256: str
    issue: EvidenceIssue
    kind: Literal["seal-published-uncertain"] = field(
        default="seal-published-uncertain", init=False
    )


@dataclass(frozen=True)
class VerificationAccepted:
    manifest_sha256: str
    artifact_count: int
    total_bytes: int
    kind: Literal["verification-accepted"] = field(default="verification-accepted", init=False)


@dataclass(frozen=True)
class VerificationRejected:
    issue: EvidenceIssue
    kind: Literal["verification-rejected"] = field(default="verification-rejected", init=False)
