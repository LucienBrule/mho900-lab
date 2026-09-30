"""Invalid typed limits and endpoints reject before opening a capture."""

from ipaddress import IPv4Address
from pathlib import Path
from typing import BinaryIO

import pytest

import mho_transport.capture as capture_module
import mho_transport.reconstruction as reconstruction
from mho_transport import (
    CaptureInspectionRejected,
    CaptureInspectionRequest,
    CaptureLimits,
    Endpoint,
    TranscriptRejected,
    TranscriptRequest,
    inspect_capture,
    reconstruct,
)


def no_capture(path: Path, limits: CaptureLimits) -> BinaryIO:
    raise AssertionError("invalid model reached capture input")


@pytest.mark.parametrize("value", [None, float("inf"), True, -1, "PRIVATE-LIMIT"])
def test_capture_limits_are_revalidated_before_inspection_or_reconstruction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: object
) -> None:
    monkeypatch.setattr(capture_module, "capture_source", no_capture)
    monkeypatch.setattr(reconstruction, "capture_source", no_capture)
    limits = CaptureLimits().model_copy(update={"max_frames": value})
    source = tmp_path / "not-opened"
    inspected = inspect_capture(CaptureInspectionRequest(source, limits))
    assert isinstance(inspected, CaptureInspectionRejected)
    assert inspected.issue.code == "invalid-limits"
    transcript = reconstruct(
        TranscriptRequest(
            source,
            Endpoint(address=IPv4Address("192.0.2.1"), port=41000),
            Endpoint(address=IPv4Address("192.0.2.2"), port=5555),
            limits,
        )
    )
    assert isinstance(transcript, TranscriptRejected)
    assert transcript.issue.code == "invalid-contract"
    assert "PRIVATE" not in repr(inspected) + repr(transcript)


def test_unchecked_endpoint_rejected_before_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(reconstruction, "capture_source", no_capture)
    client = Endpoint(address=IPv4Address("192.0.2.1"), port=41000)
    server = Endpoint(address=IPv4Address("192.0.2.2"), port=5555)
    bad = client.model_copy(update={"port": True})
    result = reconstruct(TranscriptRequest(tmp_path / "unused", bad, server))
    assert isinstance(result, TranscriptRejected) and result.issue.code == "invalid-contract"
