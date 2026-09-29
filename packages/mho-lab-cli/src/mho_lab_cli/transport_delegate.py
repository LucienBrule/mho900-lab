"""Offline transcript use case; endpoint values never open a connection."""

from pathlib import Path

from mho_transport import (
    Endpoint,
    TranscriptAccepted,
    TranscriptRejected,
    TranscriptRequest,
    reconstruct,
)


def inspect_transcript(
    capture: Path, client: Endpoint, server: Endpoint
) -> TranscriptAccepted | TranscriptRejected:
    return reconstruct(TranscriptRequest(capture=capture, client=client, server=server))
