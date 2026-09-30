"""Retained record structure and terminal statistics are separate observations."""

import hashlib
import re
from dataclasses import dataclass
from typing import Literal

from .models import (
    CaptureAssessmentAccepted,
    CaptureAssessmentRejected,
    CaptureAssessmentRequest,
    CaptureInspectionAccepted,
    CaptureInspectionRejected,
    CaptureInspectionRequest,
    CaptureLimits,
    TcpdumpStatistics,
    TcpdumpStatisticsParsed,
    TcpdumpStatisticsRejected,
    TransportIssue,
)
from .pcap import Rejection, capture_source, require, scan_records

MAX_STATISTICS_BYTES = 1024**2
MAX_COUNTER = (1 << 64) - 1
INLINE = re.compile(
    r"tcpdump: ([0-9]{1,20}) packets? captured, ([0-9]{1,20}) packets? received by filter, "
    r"([0-9]{1,20}) packets? dropped by kernel"
)
COUNTER_WORDS = re.compile(r"\bpackets? (?:captured|received by filter|dropped by kernel)\b")


@dataclass(frozen=True)
class Counts:
    captured: int
    received: int
    dropped: int


def inspect_capture(
    request: CaptureInspectionRequest,
) -> CaptureInspectionAccepted | CaptureInspectionRejected:
    """Inspect all Ethernet records; deliberately do not interpret their protocols."""
    try:
        request = CaptureInspectionRequest(
            request.capture, CaptureLimits.model_validate(request.limits)
        )
    except ValueError:
        return CaptureInspectionRejected(
            TransportIssue("invalid-limits", "capture limits violate the bounded contract")
        )
    try:
        with capture_source(request.capture, request.limits) as stream:
            metadata = scan_records(stream, request.limits)
        return CaptureInspectionAccepted(metadata=metadata)
    except Rejection as error:
        return CaptureInspectionRejected(issue=error.issue)
    except (OSError, ValueError) as error:
        return CaptureInspectionRejected(
            issue=TransportIssue(code="input-error", message=str(error))
        )


def counter(
    line: str, category: Literal["captured", "received by filter", "dropped by kernel"]
) -> int:
    match = re.fullmatch(r"([0-9]{1,20}) packets? " + category, line)
    require(match is not None, "statistics-format", "incomplete or malformed counter group")
    if match is None:
        raise AssertionError("require must reject absent match")
    value = int(match[1])
    require(value <= MAX_COUNTER, "statistics-range", "counter exceeds unsigned 64-bit range")
    return value


def counts_from_inline(match: re.Match[str]) -> Counts:
    counts = Counts(captured=int(match[1]), received=int(match[2]), dropped=int(match[3]))
    require(
        max(counts.captured, counts.received, counts.dropped) <= MAX_COUNTER,
        "statistics-range",
        "counter exceeds unsigned 64-bit range",
    )
    return counts


def parse_tcpdump_statistics(raw: bytes) -> TcpdumpStatisticsParsed | TcpdumpStatisticsRejected:
    """Parse tcpdump-terminal-counts/1; raw bytes are hashed, never rewritten.

    Permit startup text followed by cumulative inline or three-line interim
    groups. Require a final complete newline-terminated three-line group, with
    only blank lines following. Unknown text after counts, malformed groups and
    regressing counters are rejected. This profile does not prove process exit.
    """
    try:
        require(
            0 < len(raw) <= MAX_STATISTICS_BYTES, "statistics-size", "statistics size outside bound"
        )
        require(raw.endswith(b"\n"), "statistics-truncated", "statistics must end with a newline")
        text = raw.decode("utf-8")
        require("\x00" not in text, "statistics-format", "NUL is not valid statistics text")
        lines = [line.removesuffix("\r") for line in text.split("\n")]
        while lines and not lines[-1].strip():
            lines.pop()
        previous: Counts | None = None
        groups = 0
        any_drops = False
        terminal = False
        index = 0
        while index < len(lines):
            line = lines[index]
            inline = INLINE.fullmatch(line)
            current: Counts
            if inline is not None:
                current = counts_from_inline(inline)
                terminal = False
                index += 1
            elif re.fullmatch(r"[0-9]{1,20} packets? captured", line) is not None:
                require(index + 2 < len(lines), "statistics-truncated", "incomplete terminal group")
                current = Counts(
                    captured=counter(line, "captured"),
                    received=counter(lines[index + 1], "received by filter"),
                    dropped=counter(lines[index + 2], "dropped by kernel"),
                )
                index += 3
                terminal = index == len(lines)
            else:
                require(
                    COUNTER_WORDS.search(line) is None,
                    "statistics-format",
                    "malformed or out-of-order statistics line",
                )
                require(
                    previous is None or not line.strip(),
                    "statistics-suffix",
                    "unexpected text after statistics began",
                )
                index += 1
                continue
            if previous is not None:
                require(
                    current.captured >= previous.captured
                    and current.received >= previous.received
                    and current.dropped >= previous.dropped,
                    "statistics-regression",
                    "cumulative counters regressed across groups",
                )
            groups += 1
            any_drops = any_drops or current.dropped != 0
            previous = current
        require(
            previous is not None and terminal,
            "statistics-terminal",
            "complete terminal group missing",
        )
        if previous is None:
            raise AssertionError("require must reject missing statistics")
        return TcpdumpStatisticsParsed(
            statistics=TcpdumpStatistics(
                captured=previous.captured,
                received_by_filter=previous.received,
                dropped_by_kernel=previous.dropped,
                raw_sha256=hashlib.sha256(raw).hexdigest(),
                raw_bytes=len(raw),
                group_count=groups,
                any_observed_drops=any_drops,
            )
        )
    except Rejection as error:
        return TcpdumpStatisticsRejected(issue=error.issue)
    except ValueError as error:
        return TcpdumpStatisticsRejected(
            issue=TransportIssue(code="statistics-format", message=str(error))
        )


def assess_capture(
    request: CaptureAssessmentRequest,
) -> CaptureAssessmentAccepted | CaptureAssessmentRejected:
    """Compare observations only, not termination or losslessness.

    A zero kernel-drop report can also mean the backend does not support the
    statistic. Reporting support and wire completeness remain unestablished.
    """
    try:
        request = CaptureAssessmentRequest(
            request.capture, TcpdumpStatistics.model_validate(request.statistics)
        )
    except ValueError:
        return CaptureAssessmentRejected(
            TransportIssue("invalid-statistics", "statistics violate the supported contract")
        )
    if request.statistics.any_observed_drops or request.statistics.dropped_by_kernel != 0:
        return CaptureAssessmentRejected(
            issue=TransportIssue(code="observed-drops", message="recorder reported kernel drops")
        )
    if request.capture.capture_frames != request.statistics.captured:
        return CaptureAssessmentRejected(
            issue=TransportIssue(
                code="frame-count-mismatch",
                message="retained frames differ from terminal captured count",
            )
        )
    return CaptureAssessmentAccepted(capture=request.capture, statistics=request.statistics)
