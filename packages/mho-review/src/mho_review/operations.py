"""Bind consumers to a pinned exact inventory before accepting their composition."""

import hashlib

from mho_evidence import (
    Artifact,
    ArtifactPath,
    VerificationAccepted,
    VerificationLimits,
    VerifyRequest,
    load_manifest,
    verify,
)
from mho_scpi import CodecLimits, ExchangeAccepted
from mho_scpi import decode_exchange as decode_exchange
from mho_transport import (
    CaptureAssessmentAccepted,
    CaptureAssessmentRequest,
    CaptureInspectionAccepted,
    CaptureInspectionRequest,
    CaptureLimits,
    TcpdumpStatisticsParsed,
    TranscriptAccepted,
    TranscriptRequest,
    assess_capture,
    parse_tcpdump_statistics,
    reconstruct,
)
from mho_transport import inspect_capture as inspect_capture

from .inputs import read_bounded
from .models import ReviewAccepted, ReviewIssue, ReviewRejected, ReviewRequest


class ReviewFailure(Exception):
    def __init__(self, stage: str, code: str, message: str) -> None:
        self.issue = ReviewIssue(stage, code, message)
        super().__init__(message)


def require(condition: bool, stage: str, code: str, message: str) -> None:
    if not condition:
        raise ReviewFailure(stage, code, message)


def bound_digest(raw: bytes, artifact: Artifact, stage: str) -> None:
    require(
        len(raw) == artifact.size_bytes and hashlib.sha256(raw).hexdigest() == artifact.sha256.root,
        stage,
        "member-binding",
        "consumer bytes differ from pinned member",
    )


def member(artifacts: tuple[Artifact, ...], path: ArtifactPath) -> Artifact:
    for artifact in artifacts:
        if artifact.path == path:
            return artifact
    raise ReviewFailure("roles", "missing-member", "role is not an exact inventory member")


def review(request: ReviewRequest) -> ReviewAccepted | ReviewRejected:
    """Offline content consistency, never physical provenance or an atomic snapshot."""
    stage = "manifest"
    try:
        raw_manifest = read_bounded(request.manifest, request.limits.max_manifest_bytes)
        pinned = request.expected_manifest_sha256.root
        require(
            hashlib.sha256(raw_manifest).hexdigest() == pinned,
            stage,
            "manifest-pin",
            "manifest does not match caller pin",
        )
        manifest = load_manifest(raw_manifest)
        limits = VerificationLimits(
            max_entries=request.limits.max_inventory_entries,
            max_total_bytes=request.limits.max_inventory_bytes,
            max_file_bytes=request.limits.max_file_bytes,
            max_depth=request.limits.max_depth,
            max_manifest_bytes=request.limits.max_manifest_bytes,
        )
        verification_request = VerifyRequest(request.root, request.manifest, limits=limits)
        stage = "inventory-before"
        initial = verify(verification_request)
        require(
            isinstance(initial, VerificationAccepted),
            stage,
            "inventory-rejected",
            "initial inventory verification rejected",
        )
        if not isinstance(initial, VerificationAccepted):
            raise RuntimeError("inventory outcome did not narrow")
        require(
            initial.manifest_sha256 == pinned,
            stage,
            "manifest-pin",
            "verified manifest differs from caller pin",
        )
        stage = "roles"
        capture_member = member(manifest.artifacts, request.profile.capture)
        stats_member = member(manifest.artifacts, request.profile.statistics)
        for pair in request.profile.transcripts:
            member(manifest.artifacts, pair.request)
            member(manifest.artifacts, pair.reply)
        capture_limits = CaptureLimits(
            max_capture_bytes=request.limits.max_file_bytes,
            max_frames=request.limits.max_capture_frames,
            max_direction_bytes=1024**2,
        )
        capture_path = request.root / request.profile.capture.root
        stage = "capture"
        capture = inspect_capture(CaptureInspectionRequest(capture_path, limits=capture_limits))
        require(
            isinstance(capture, CaptureInspectionAccepted),
            stage,
            "capture-rejected",
            "capture structural inspection rejected",
        )
        if not isinstance(capture, CaptureInspectionAccepted):
            raise RuntimeError("capture outcome did not narrow")
        require(
            capture.metadata.capture_sha256 == capture_member.sha256.root
            and capture.metadata.capture_bytes == capture_member.size_bytes,
            stage,
            "member-binding",
            "capture consumer differs from pinned member",
        )
        stage = "statistics"
        stats_raw = read_bounded(request.root / request.profile.statistics.root, 1024**2)
        bound_digest(stats_raw, stats_member, stage)
        parsed = parse_tcpdump_statistics(stats_raw)
        require(
            isinstance(parsed, TcpdumpStatisticsParsed),
            stage,
            "statistics-rejected",
            "terminal capture statistics rejected",
        )
        if not isinstance(parsed, TcpdumpStatisticsParsed):
            raise RuntimeError("statistics outcome did not narrow")
        require(
            parsed.statistics.raw_sha256 == stats_member.sha256.root
            and parsed.statistics.raw_bytes == stats_member.size_bytes,
            stage,
            "member-binding",
            "statistics consumer differs from pinned member",
        )
        stage = "assessment"
        assessment = assess_capture(CaptureAssessmentRequest(capture.metadata, parsed.statistics))
        require(
            isinstance(assessment, CaptureAssessmentAccepted),
            stage,
            "assessment-rejected",
            "capture and statistics assessment rejected",
        )
        if not isinstance(assessment, CaptureAssessmentAccepted):
            raise RuntimeError("assessment outcome did not narrow")
        stage = "tcp"
        transcript = reconstruct(
            TranscriptRequest(
                capture_path, request.profile.client, request.profile.server, limits=capture_limits
            )
        )
        require(
            isinstance(transcript, TranscriptAccepted),
            stage,
            "tcp-rejected",
            "selected TCP reconstruction rejected",
        )
        if not isinstance(transcript, TranscriptAccepted):
            raise RuntimeError("transcript outcome did not narrow")
        require(
            transcript.metadata.capture_sha256 == capture_member.sha256.root
            and transcript.metadata.capture_bytes == capture_member.size_bytes,
            stage,
            "member-binding",
            "TCP consumer differs from pinned capture",
        )
        require(
            transcript.metadata.capture_frames == capture.metadata.capture_frames,
            stage,
            "capture-count",
            "capture consumers disagree on frame count",
        )
        stage = "transcripts"
        requests: list[bytes] = []
        replies: list[bytes] = []
        codec_limits = CodecLimits()
        total = 0
        for pair in request.profile.transcripts:
            query = read_bounded(request.root / pair.request.root, codec_limits.max_line_bytes)
            reply = read_bounded(request.root / pair.reply.root, codec_limits.max_line_bytes)
            bound_digest(query, member(manifest.artifacts, pair.request), stage)
            bound_digest(reply, member(manifest.artifacts, pair.reply), stage)
            require(
                query.count(b"\n") == 1
                and query.endswith(b"\n")
                and reply.count(b"\n") == 1
                and reply.endswith(b"\n"),
                stage,
                "role-framing",
                "each transcript role must contain one complete line",
            )
            total += len(query) + len(reply)
            require(
                total <= codec_limits.max_exchange_bytes,
                stage,
                "transcript-limit",
                "combined transcript extent exceeds bound",
            )
            requests.append(query)
            replies.append(reply)
        wire_request = b"".join(requests)
        wire_reply = b"".join(replies)
        require(
            transcript.request == wire_request and transcript.reply == wire_reply,
            stage,
            "tcp-transcript-mismatch",
            "TCP and ordered transcript bytes differ",
        )
        stage = "scpi"
        exchange = decode_exchange(wire_request, wire_reply, codec_limits)
        require(
            isinstance(exchange, ExchangeAccepted),
            stage,
            "scpi-rejected",
            "canonical read-only SCPI decoding rejected",
        )
        if not isinstance(exchange, ExchangeAccepted):
            raise RuntimeError("exchange outcome did not narrow")
        stage = "inventory-after"
        final = verify(verification_request)
        require(
            isinstance(final, VerificationAccepted),
            stage,
            "inventory-rejected",
            "final inventory verification rejected",
        )
        if not isinstance(final, VerificationAccepted):
            raise RuntimeError("inventory outcome did not narrow")
        require(
            final == initial and final.manifest_sha256 == pinned,
            stage,
            "inventory-changed",
            "inventory verification changed during review",
        )
        return ReviewAccepted(pinned, request.profile, final, assessment, transcript, exchange)
    except ReviewFailure as error:
        return ReviewRejected(error.issue)
    except (OSError, ValueError, NotImplementedError, RecursionError):
        return ReviewRejected(
            ReviewIssue(stage, "input-rejected", "bounded unchanged input required")
        )
