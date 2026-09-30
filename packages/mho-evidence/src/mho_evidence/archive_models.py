"""Bounded archive inspection values; content is never extracted."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import Field

from .api import EvidenceIssue
from .contracts import EvidenceValue
from .manifest import Artifact, ArtifactPath, Sha256


class ArchiveLimits(EvidenceValue):
    max_source_bytes: int = Field(default=64 * 1024**2, ge=1024, le=1024**3)
    max_members: int = Field(default=10000, ge=1, le=100000)
    max_member_bytes: int = Field(default=64 * 1024**2, ge=0, le=1024**3)
    max_total_payload_bytes: int = Field(default=64 * 1024**2, ge=0, le=1024**3)
    max_path_depth: int = Field(default=32, ge=1, le=128)


@dataclass(frozen=True)
class ArchiveRequest:
    path: Path
    expected_sha256: Sha256
    limits: ArchiveLimits = field(default_factory=ArchiveLimits)


@dataclass(frozen=True)
class ArchiveAccepted:
    source_sha256: str
    source_bytes: int
    artifacts: tuple[Artifact, ...]
    directories: tuple[ArtifactPath, ...]
    member_count: int
    physical_origin_proven: Literal[False] = False
    atomic_snapshot_proven: Literal[False] = False
    kind: Literal["archive-accepted"] = field(default="archive-accepted", init=False)


@dataclass(frozen=True)
class ArchiveRejected:
    issue: EvidenceIssue
    kind: Literal["archive-rejected"] = field(default="archive-rejected", init=False)
