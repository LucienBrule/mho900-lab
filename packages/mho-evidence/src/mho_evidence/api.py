"""Named requests and outcomes; none asserts instrument provenance or atomicity."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class SealRequest:
    root: Path
    output: Path
    allow_empty: bool = False


@dataclass(frozen=True)
class VerifyRequest:
    root: Path
    manifest: Path


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
