"""Record-structure and recorder-counter evidence without a TCP-flow requirement."""

import hashlib
from pathlib import Path
from typing import Literal

import pytest

from mho_transport import (
    CaptureAssessmentAccepted,
    CaptureAssessmentRejected,
    CaptureAssessmentRequest,
    CaptureInspectionAccepted,
    CaptureInspectionRejected,
    CaptureInspectionRequest,
    TcpdumpStatisticsParsed,
    TcpdumpStatisticsRejected,
    assess_capture,
    inspect_capture,
    parse_tcpdump_statistics,
)


def structural_pcap(order: Literal["little", "big"], nano: bool, frames: int) -> bytes:
    # A bare Ethernet frame with an unknown EtherType: structural evidence only.
    raw = bytes(12) + b"\x12\x34"
    magic = 0xA1B23C4D if nano else 0xA1B2C3D4
    header = (
        magic.to_bytes(4, order)
        + (2).to_bytes(2, order)
        + (4).to_bytes(2, order)
        + bytes(8)
        + (262144).to_bytes(4, order)
        + (1).to_bytes(4, order)
    )
    record = (
        (1700000000).to_bytes(4, order)
        + (42).to_bytes(4, order)
        + len(raw).to_bytes(4, order)
        + len(raw).to_bytes(4, order)
        + raw
    )
    return header + record * frames


def statistics(captured: int, received: int, dropped: int) -> bytes:
    return (
        f"{captured} packets captured\n"
        f"{received} packets received by filter\n"
        f"{dropped} packets dropped by kernel\n"
    ).encode()


def inspection(tmp_path: Path, frames: int = 2) -> CaptureInspectionAccepted:
    path = tmp_path / "capture.pcap"
    path.write_bytes(structural_pcap("little", False, frames))
    outcome = inspect_capture(CaptureInspectionRequest(capture=path))
    assert isinstance(outcome, CaptureInspectionAccepted)
    return outcome


@pytest.mark.parametrize("order", ["little", "big"])
@pytest.mark.parametrize("nano", [False, True])
@pytest.mark.parametrize("frames", [0, 2])
def test_generic_records_without_tcp(
    tmp_path: Path, order: Literal["little", "big"], nano: bool, frames: int
) -> None:
    raw = structural_pcap(order, nano, frames)
    path = tmp_path / "capture.pcap"
    path.write_bytes(raw)
    result = inspect_capture(CaptureInspectionRequest(capture=path))
    assert isinstance(result, CaptureInspectionAccepted)
    assert result.metadata.capture_frames == frames
    assert result.metadata.capture_bytes == len(raw)
    assert result.metadata.capture_sha256 == hashlib.sha256(raw).hexdigest()
    assert result.metadata.protocols_validated is False
    assert result.metadata.snapshot_length == 262144
    assert result.metadata.byte_order == order


@pytest.mark.parametrize("mutation", ["tail", "header", "pcapng", "record-truncation"])
def test_inspection_rejects_structural_damage(tmp_path: Path, mutation: str) -> None:
    raw = structural_pcap("little", False, 2)
    if mutation == "tail":
        raw = raw[:-1]
    elif mutation == "header":
        raw = raw[:20]
    elif mutation == "pcapng":
        raw = b"\x0a\x0d\x0d\x0a" + raw[4:]
    else:
        raw = raw[:24] + b"x"
    path = tmp_path / "damaged.pcap"
    path.write_bytes(raw)
    assert isinstance(
        inspect_capture(CaptureInspectionRequest(capture=path)), CaptureInspectionRejected
    )


def test_inline_interim_and_terminal_counts(tmp_path: Path) -> None:
    raw = (
        b"tcpdump: listening on example0, link-type EN10MB (Ethernet), "
        b"snapshot length 262144 bytes\n"
        b"tcpdump: 0 packets captured, 0 packets received by filter, 0 packets dropped by kernel\n"
        + statistics(2, 1, 0)
    )
    parsed = parse_tcpdump_statistics(raw)
    assert isinstance(parsed, TcpdumpStatisticsParsed)
    assert parsed.statistics.captured == 2
    assert parsed.statistics.received_by_filter == 1  # No cross-counter ordering assumption.
    assert parsed.statistics.group_count == 2
    assert parsed.statistics.raw_bytes == len(raw)
    assert parsed.statistics.raw_sha256 == hashlib.sha256(raw).hexdigest()
    result = assess_capture(
        CaptureAssessmentRequest(
            capture=inspection(tmp_path).metadata, statistics=parsed.statistics
        )
    )
    assert isinstance(result, CaptureAssessmentAccepted)
    assert result.process_exit_proven is False and result.wire_completeness_proven is False
    assert result.drop_reporting_support_established is False


def test_multiple_standalone_groups_are_preserved() -> None:
    raw = statistics(0, 0, 0) + statistics(1, 0, 0) + statistics(2, 1, 0) + b"\n"
    parsed = parse_tcpdump_statistics(raw)
    assert isinstance(parsed, TcpdumpStatisticsParsed)
    assert parsed.statistics.group_count == 3 and parsed.statistics.captured == 2


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"listening only\n",
        b"0 packets captured\n0 packets received by filter\n",
        b"0 packets received by filter\n0 packets dropped by kernel\n",
        b"tcpdump: 0 packets captured, 0 packets received by filter, 0 packets dropped by kernel\n",
        b"-1 packets captured\n0 packets received by filter\n0 packets dropped by kernel\n",
        b"0 packets captured\n0 packets dropped by kernel\n0 packets received by filter\n",
        b"0 packets captured\n0 packets received by filter\n0 packets dropped by kernel",
        b"0 packets captured\n0 packets received by filter\n0 packets dropped by kernel\nerror\n",
        (
            b"0 packets captured\n0 packets received by filter\n"
            b"0 packets dropped by kernel\n0 packets captured\n"
        ),
        (
            b"18446744073709551616 packets captured\n"
            b"0 packets received by filter\n0 packets dropped by kernel\n"
        ),
        b"\xff\n",
        b"\x00\n",
    ],
)
def test_incomplete_ambiguous_or_malformed_statistics(raw: bytes) -> None:
    assert isinstance(parse_tcpdump_statistics(raw), TcpdumpStatisticsRejected)


@pytest.mark.parametrize("regression", ["captured", "received", "dropped"])
def test_regressing_counters_rejected(regression: str) -> None:
    first = statistics(3, 4, 1)
    if regression == "captured":
        last = statistics(2, 4, 1)
    elif regression == "received":
        last = statistics(3, 3, 1)
    else:
        last = statistics(3, 4, 0)
    parsed = parse_tcpdump_statistics(first + last)
    assert isinstance(parsed, TcpdumpStatisticsRejected)
    assert parsed.issue.code == "statistics-regression"


def test_nonzero_drops_are_not_lost_in_interim_text(tmp_path: Path) -> None:
    raw = (
        b"tcpdump: 1 packet captured, 1 packet received by filter, 1 packet dropped by kernel\n"
        + statistics(2, 2, 1)
    )
    parsed = parse_tcpdump_statistics(raw)
    assert isinstance(parsed, TcpdumpStatisticsParsed)
    assert parsed.statistics.any_observed_drops is True
    result = assess_capture(
        CaptureAssessmentRequest(
            capture=inspection(tmp_path).metadata, statistics=parsed.statistics
        )
    )
    assert isinstance(result, CaptureAssessmentRejected)
    assert result.issue.code == "observed-drops"


def test_frame_count_mismatch_rejected(tmp_path: Path) -> None:
    parsed = parse_tcpdump_statistics(statistics(3, 3, 0))
    assert isinstance(parsed, TcpdumpStatisticsParsed)
    result = assess_capture(
        CaptureAssessmentRequest(
            capture=inspection(tmp_path).metadata, statistics=parsed.statistics
        )
    )
    assert isinstance(result, CaptureAssessmentRejected)
    assert result.issue.code == "frame-count-mismatch"


def test_statistics_resource_limit() -> None:
    assert isinstance(parse_tcpdump_statistics(b"x" * (1024**2 + 1)), TcpdumpStatisticsRejected)


def test_crlf_and_singular_profile() -> None:
    raw = b"1 packet captured\r\n1 packet received by filter\r\n0 packets dropped by kernel\r\n"
    assert isinstance(parse_tcpdump_statistics(raw), TcpdumpStatisticsParsed)
