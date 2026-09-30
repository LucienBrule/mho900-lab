"""Reconstruct caller-owned configuration before any recorder side effect."""

from pydantic import ValidationError

from .models import ReadyMarker, RecorderRequest


def checked_request(request: RecorderRequest) -> RecorderRequest | None:
    """Return an independent validated snapshot, without serializing unchecked values."""
    try:
        if type(request) is not RecorderRequest or type(request.ready) is not ReadyMarker:
            return None
        ready = ReadyMarker(stream=request.ready.stream, line=request.ready.line)
        return RecorderRequest(
            executable=request.executable,
            arguments=request.arguments,
            evidence_directory=request.evidence_directory,
            ready=ready,
            startup_timeout=request.startup_timeout,
            graceful_timeout=request.graceful_timeout,
            terminate_timeout=request.terminate_timeout,
            kill_timeout=request.kill_timeout,
        )
    except (AttributeError, ValidationError):
        return None
