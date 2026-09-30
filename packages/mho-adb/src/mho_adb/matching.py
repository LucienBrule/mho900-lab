"""Offline identifier matching within two independently retained ADB streams."""

import hashlib
from dataclasses import dataclass, field
from typing import Literal

from pydantic import ValidationError

from mho_evidence import Sha256

from .codec import decode
from .models import DecodeAccepted, DecodeIssue, DecodeLimits, OkayFrame, OpenFrame


@dataclass(frozen=True)
class MatchOpenRequest:
    client: DecodeAccepted = field(repr=False)
    server: DecodeAccepted = field(repr=False)
    expected_payload_sha256: Sha256


@dataclass(frozen=True)
class _ObservationLimits:
    total_order_proven: Literal[False] = field(default=False, init=False)
    tcp_delivery_proven: Literal[False] = field(default=False, init=False)
    device_execution_proven: Literal[False] = field(default=False, init=False)
    physical_origin_proven: Literal[False] = field(default=False, init=False)


@dataclass(frozen=True)
class StreamReadyMatched(_ObservationLimits):
    request: MatchOpenRequest = field(repr=False)
    open_frame: OpenFrame = field(repr=False)
    ready_frames: tuple[OkayFrame, ...] = field(repr=False)
    client_local_id: int
    server_local_id: int
    kind: Literal["stream-ready-matched"] = field(default="stream-ready-matched", init=False)


@dataclass(frozen=True)
class StreamReadyMissing(_ObservationLimits):
    request: MatchOpenRequest = field(repr=False)
    reason: Literal["open-not-found", "ready-not-found"]
    selected_open: OpenFrame | None = field(default=None, repr=False)
    kind: Literal["stream-ready-missing"] = field(default="stream-ready-missing", init=False)


@dataclass(frozen=True)
class StreamReadyRejected(_ObservationLimits):
    request: MatchOpenRequest = field(repr=False)
    issue: DecodeIssue
    kind: Literal["stream-ready-rejected"] = field(default="stream-ready-rejected", init=False)


def _validated_stream(stream: object) -> bool:
    """Bind supplied typed records back to their exact retained bytes."""
    if not isinstance(stream, DecodeAccepted):
        return False
    if (
        type(stream.raw) is not bytes
        or type(stream.raw_bytes) is not int
        or type(stream.raw_sha256) is not str
        or type(stream.frames) is not tuple
        or not isinstance(stream.limits, DecodeLimits)
        or stream.handshake_compatibility_proven is not False
        or stream.state_machine_validated is not False
        or stream.physical_origin_proven is not False
        or stream.device_execution_proven is not False
    ):
        return False
    try:
        limits = DecodeLimits(
            max_stream_bytes=stream.limits.max_stream_bytes,
            max_frames=stream.limits.max_frames,
            max_payload_bytes=stream.limits.max_payload_bytes,
        )
    except (ValidationError, TypeError, ValueError):
        return False
    # Decode enforces its byte/frame limits before producing a second inventory.
    # Do not concatenate caller-supplied frame.wire values to construct evidence.
    checked = decode(stream.raw, limits)
    if not isinstance(checked, DecodeAccepted) or checked != stream:
        return False
    for frame in stream.frames:
        # bool compares equal to 0/1 in Python but is not a wire integer.
        if (
            type(frame.offset) is not int
            or type(frame.arg0) is not int
            or type(frame.arg1) is not int
            or type(frame.checksum) is not int
            or type(frame.payload) is not bytes
            or type(frame.wire) is not bytes
        ):
            return False
    return True


def _rejected(request: MatchOpenRequest, code: str, message: str) -> StreamReadyRejected:
    return StreamReadyRejected(request=request, issue=DecodeIssue(code, message, 0))


def match_open(
    request: MatchOpenRequest,
) -> StreamReadyMatched | StreamReadyMissing | StreamReadyRejected:
    """Match one exact OPEN payload and consistent server OKAY identifiers.

    Repeated OKAY records with the same identifier pair are retained, not treated
    as another OPEN. Selected client-ID reuse is rejected even after CLSE because
    separate directional streams cannot establish the required event ordering.
    Inputs must retain the decoder's exact frame/output model classes. This is
    neither a complete ADB state machine nor a device-action witness.
    """
    try:
        expected = Sha256(request.expected_payload_sha256.root).root
    except (ValidationError, AttributeError, TypeError):
        return _rejected(request, "expected-payload-digest", "Expected payload digest is invalid")
    if not _validated_stream(request.client) or not _validated_stream(request.server):
        return _rejected(request, "decoded-stream", "Decoded stream does not match retained bytes")
    selected = tuple(
        frame
        for frame in request.client.frames
        if isinstance(frame, OpenFrame) and hashlib.sha256(frame.payload).hexdigest() == expected
    )
    if not selected:
        return StreamReadyMissing(request=request, reason="open-not-found")
    if len(selected) != 1:
        return _rejected(
            request, "ambiguous-open", "Expected payload matches multiple OPEN records"
        )
    opened = selected[0]
    if (
        sum(
            isinstance(frame, OpenFrame) and frame.arg0 == opened.arg0
            for frame in request.client.frames
        )
        != 1
    ):
        return _rejected(
            request, "client-id-reused", "Selected client identifier has multiple OPENs"
        )
    replies = tuple(
        frame
        for frame in request.server.frames
        if isinstance(frame, OkayFrame) and frame.arg1 == opened.arg0
    )
    if not replies:
        return StreamReadyMissing(request=request, reason="ready-not-found", selected_open=opened)
    if len({frame.arg0 for frame in replies}) != 1:
        return _rejected(
            request,
            "responder-id-changed",
            "Selected stream has inconsistent responder identifiers",
        )
    return StreamReadyMatched(
        request=request,
        open_frame=opened,
        ready_frames=replies,
        client_local_id=opened.arg0,
        server_local_id=replies[0].arg0,
    )
