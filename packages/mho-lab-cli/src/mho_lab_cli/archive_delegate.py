"""Offline archive operations delegated through named library outcomes."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from mho_evidence import (
    ArchiveAccepted,
    ArchiveRejected,
    ArchiveRequest,
    DeltaRejected,
    InventoryDelta,
    InventoryDiffRequest,
    Sha256,
    compare_inventory,
    inspect_archive,
)


@dataclass(frozen=True)
class ArchiveOperationRejected:
    stage: str
    code: str
    message: str


@dataclass(frozen=True)
class ArchiveDiffReport:
    before: ArchiveAccepted
    after: ArchiveAccepted
    delta: InventoryDelta


def inspect_retained_archive(path: Path, digest: str) -> ArchiveAccepted | ArchiveOperationRejected:
    try:
        expected = Sha256(digest)
    except ValidationError:
        return ArchiveOperationRejected("input", "digest", "expected a lowercase SHA-256 digest")
    result = inspect_archive(ArchiveRequest(path, expected))
    if isinstance(result, ArchiveRejected):
        return ArchiveOperationRejected("archive", result.issue.code, result.issue.message)
    return result


def compare_archives(
    before: Path, before_digest: str, after: Path, after_digest: str
) -> ArchiveDiffReport | ArchiveOperationRejected:
    first = inspect_retained_archive(before, before_digest)
    if isinstance(first, ArchiveOperationRejected):
        return ArchiveOperationRejected("before", first.code, first.message)
    second = inspect_retained_archive(after, after_digest)
    if isinstance(second, ArchiveOperationRejected):
        return ArchiveOperationRejected("after", second.code, second.message)
    delta = compare_inventory(InventoryDiffRequest(first.artifacts, second.artifacts))
    if isinstance(delta, DeltaRejected):
        return ArchiveOperationRejected("delta", delta.issue.code, delta.issue.message)
    return ArchiveDiffReport(first, second, delta)
