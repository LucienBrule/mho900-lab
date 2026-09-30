"""Unchecked requests reject before setup; accepted snapshots use owned synthetic children."""

import math
import warnings
from pathlib import Path
from typing import Never

import pytest
from test_lifecycle import request

from mho_capture import (
    ReadyMarker,
    RecorderGraceful,
    RecorderReady,
    RecorderRequest,
    RecorderStartRejected,
    start,
    stop,
)


def unchecked(base: RecorderRequest, case: str) -> RecorderRequest:
    if case == "ready-stream":
        return base.model_copy(
            update={"ready": base.ready.model_copy(update={"stream": "PRIVATE"})}
        )
    if case == "ready-empty":
        return base.model_copy(update={"ready": base.ready.model_copy(update={"line": ""})})
    if case == "ready-newline":
        return base.model_copy(
            update={"ready": base.ready.model_copy(update={"line": "PRIVATE\n"})}
        )
    if case == "ready-surrogate":
        return base.model_copy(
            update={"ready": base.ready.model_copy(update={"line": "PRIVATE\ud800"})}
        )
    if case == "ready-object":
        return base.model_copy(update={"ready": "PRIVATE"})
    if case == "ready-subclass":

        class MarkerSubclass(ReadyMarker):
            pass

        return base.model_copy(update={"ready": MarkerSubclass(stream="stdout", line="READY")})
    if case == "relative-executable":
        return base.model_copy(update={"executable": Path("PRIVATE")})
    if case == "relative-directory":
        return base.model_copy(update={"evidence_directory": Path("PRIVATE")})
    if case == "string-directory":
        return base.model_copy(update={"evidence_directory": "/PRIVATE"})
    if case == "control-directory":
        return base.model_copy(update={"evidence_directory": base.evidence_directory / "PRIVATE\n"})
    if case == "list-arguments":
        return base.model_copy(update={"arguments": ["PRIVATE"]})
    if case == "non-string-argument":
        return base.model_copy(update={"arguments": (1,)})
    if case == "control-argument":
        return base.model_copy(update={"arguments": ("PRIVATE\0",)})
    if case == "missing-fields":
        incomplete = RecorderRequest.model_construct(
            executable=base.executable,
            evidence_directory=base.evidence_directory,
            ready=base.ready,
        )
        del incomplete.__dict__["ready"]
        return incomplete
    if case == "request-subclass":

        class RequestSubclass(RecorderRequest):
            pass

        return RequestSubclass(
            executable=base.executable,
            evidence_directory=base.evidence_directory,
            ready=base.ready,
        )
    raise AssertionError("unknown synthetic case")


@pytest.mark.parametrize(
    "case",
    [
        "ready-stream",
        "ready-empty",
        "ready-newline",
        "ready-surrogate",
        "ready-object",
        "ready-subclass",
        "relative-executable",
        "relative-directory",
        "string-directory",
        "control-directory",
        "list-arguments",
        "non-string-argument",
        "control-argument",
        "missing-fields",
        "request-subclass",
    ],
)
def test_malformed_request_has_no_setup_or_private_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    base = request(tmp_path)
    rejected_request = unchecked(base, case)

    def forbidden(*args: object, **kwargs: object) -> Never:
        raise AssertionError("invalid request reached filesystem setup or child launch")

    monkeypatch.setattr("pathlib.Path.mkdir", forbidden)
    monkeypatch.setattr("mho_capture.lifecycle.subprocess.Popen", forbidden)
    with warnings.catch_warnings(record=True) as caught:
        result = start(rejected_request)
    assert isinstance(result, RecorderStartRejected)
    assert result.directory is None
    assert result.reason == "request violates the bounded recorder contract"
    assert "PRIVATE" not in repr(result) and not caught
    assert not base.evidence_directory.exists()


@pytest.mark.parametrize(
    "field", ["startup_timeout", "graceful_timeout", "terminate_timeout", "kill_timeout"]
)
@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan, True, 0, -1, 61, "PRIVATE"])
def test_all_deadlines_revalidated_before_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    base = request(tmp_path)
    forged = base.model_copy(update={field: value})

    def forbidden(*args: object, **kwargs: object) -> Never:
        raise AssertionError("invalid deadline reached setup")

    monkeypatch.setattr("pathlib.Path.mkdir", forbidden)
    monkeypatch.setattr("mho_capture.lifecycle.subprocess.Popen", forbidden)
    with warnings.catch_warnings(record=True) as caught:
        result = start(forged)
    assert isinstance(result, RecorderStartRejected) and result.directory is None
    assert not base.evidence_directory.exists() and not caught
    assert "PRIVATE" not in repr(result)


def test_ready_handle_retains_independent_snapshot_for_bounded_cleanup(tmp_path: Path) -> None:
    original = request(tmp_path)
    result = start(original)
    assert isinstance(result, RecorderReady)
    try:
        snapshot = result.handle.request
        assert snapshot is not original and snapshot.ready is not original.ready
        assert snapshot == original
        # Pydantic exposes its backing mapping; changing the caller-owned values
        # must not alter the independently reconstructed ownership configuration.
        original.__dict__["graceful_timeout"] = math.inf
        original.ready.__dict__["line"] = "PRIVATE_CHANGED"
        assert snapshot.graceful_timeout == 0.15 and snapshot.ready.line == "READY"
        descriptor: object = vars(type(result.handle))["request"]
        assert isinstance(descriptor, property)
        assert descriptor.fset is None
    finally:
        terminal = stop(result.handle)
    assert isinstance(terminal, RecorderGraceful) and terminal.evidence.reaped
