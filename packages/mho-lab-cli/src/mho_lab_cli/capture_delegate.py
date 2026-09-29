"""Compose preserved capture structure and recorder counts without acquisition."""

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from mho_transport import (
    CaptureAssessmentAccepted,
    CaptureAssessmentRejected,
    CaptureAssessmentRequest,
    CaptureInspectionRejected,
    CaptureInspectionRequest,
    TcpdumpStatisticsRejected,
    TransportIssue,
    assess_capture,
    inspect_capture,
    parse_tcpdump_statistics,
)


@dataclass(frozen=True)
class CaptureReportRejected:
    stage: Literal["capture", "statistics", "assessment", "input"]
    issue: TransportIssue


@dataclass(frozen=True)
class LogIdentity:
    device: int
    inode: int
    mode: int
    size: int
    modified_ns: int
    changed_ns: int

    @classmethod
    def read(cls, state: os.stat_result) -> "LogIdentity":
        return cls(
            state.st_dev,
            state.st_ino,
            state.st_mode,
            state.st_size,
            state.st_mtime_ns,
            state.st_ctime_ns,
        )


def read_statistics(path: Path) -> bytes:
    """Bound a local regular-file read and reject observable changes."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = LogIdentity.read(os.fstat(descriptor))
        if not stat.S_ISREG(before.mode) or before.size > 1024 * 1024:
            raise ValueError("recorder log must be a regular file no larger than 1 MiB")
        chunks: list[bytes] = []
        total = 0
        while chunk := os.read(descriptor, min(65536, 1024 * 1024 + 1 - total)):
            chunks.append(chunk)
            total += len(chunk)
            if total > 1024 * 1024:
                raise ValueError("recorder log grew beyond the 1 MiB limit")
        after = LogIdentity.read(os.fstat(descriptor))
        named = LogIdentity.read(os.stat(path, follow_symlinks=False))
        if before != after or before != named or total != before.size:
            raise ValueError("recorder log changed during the read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def inspect_capture_report(
    capture: Path, stderr: Path
) -> CaptureAssessmentAccepted | CaptureReportRejected:
    inspected = inspect_capture(CaptureInspectionRequest(capture=capture))
    if isinstance(inspected, CaptureInspectionRejected):
        return CaptureReportRejected(stage="capture", issue=inspected.issue)
    try:
        raw = read_statistics(stderr)
    except (OSError, ValueError) as error:
        return CaptureReportRejected(
            stage="input", issue=TransportIssue(code="input-error", message=str(error))
        )
    statistics = parse_tcpdump_statistics(raw)
    if isinstance(statistics, TcpdumpStatisticsRejected):
        return CaptureReportRejected(stage="statistics", issue=statistics.issue)
    assessment = assess_capture(
        CaptureAssessmentRequest(capture=inspected.metadata, statistics=statistics.statistics)
    )
    if isinstance(assessment, CaptureAssessmentRejected):
        return CaptureReportRejected(stage="assessment", issue=assessment.issue)
    return assessment
