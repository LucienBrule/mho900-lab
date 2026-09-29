"""Compose preserved capture structure and recorder counts without acquisition."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from mho_lab_cli.inputs import read_bounded_regular
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


def inspect_capture_report(
    capture: Path, stderr: Path
) -> CaptureAssessmentAccepted | CaptureReportRejected:
    inspected = inspect_capture(CaptureInspectionRequest(capture=capture))
    if isinstance(inspected, CaptureInspectionRejected):
        return CaptureReportRejected(stage="capture", issue=inspected.issue)
    try:
        raw = read_bounded_regular(stderr, 1024 * 1024)
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
