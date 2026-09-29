"""Synthetic foreground children only: no sockets, recorder interfaces or devices."""

import os
import signal
import sys
import time
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

import mho_capture.lifecycle as lifecycle
from mho_capture import (
    ReadyMarker,
    RecorderAbnormal,
    RecorderCleanupUncertain,
    RecorderEscalated,
    RecorderGraceful,
    RecorderOwnershipUncertain,
    RecorderReady,
    RecorderRequest,
    RecorderStartFailed,
    RecorderStartRejected,
    reap,
    start,
    stop,
)

CHILD = """
import os
import signal
import sys
mode = sys.argv[1]
def graceful(sig, frame):
    print("7 packets captured", file=sys.stderr, flush=True)
    print("7 packets received by filter", file=sys.stderr, flush=True)
    print("0 packets dropped by kernel", file=sys.stderr, flush=True)
    sys.exit(7 if mode == "abnormal" else 0)
def unexpected(sig, frame):
    sys.exit(0)
signal.signal(signal.SIGINT, graceful)
signal.signal(signal.SIGUSR1, unexpected)
if mode in ("ignore-int", "ignore-both"):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
if mode == "ignore-both":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
if mode == "exit-zero":
    sys.exit(0)
if mode == "wrong-marker":
    print("NOT-READY", flush=True)
elif mode == "incomplete-marker":
    sys.stdout.write("READY")
    sys.stdout.flush()
elif mode == "stderr":
    print("READY", file=sys.stderr, flush=True)
else:
    print("READY", flush=True)
while True:
    signal.pause()
"""


def request(tmp_path: Path, mode: str = "graceful") -> RecorderRequest:
    root = tmp_path.resolve()
    script = root / "synthetic.py"
    script.write_text(CHILD)
    return RecorderRequest(
        executable=Path(sys.executable).resolve(),
        arguments=(str(script), mode),
        evidence_directory=root / "run",
        ready=ReadyMarker(stream="stderr" if mode == "stderr" else "stdout", line="READY"),
        startup_timeout=2.0,
        graceful_timeout=0.15,
        terminate_timeout=0.15,
        kill_timeout=0.5,
    )


def ready(req: RecorderRequest) -> RecorderReady:
    result = start(req)
    assert isinstance(result, RecorderReady), result
    return result


@pytest.mark.parametrize("mode", ["graceful", "stderr"])
def test_graceful_retains_counts_and_idempotent_terminal(tmp_path: Path, mode: str) -> None:
    req = request(tmp_path, mode)
    child = ready(req)
    result = stop(child.handle)
    assert isinstance(result, RecorderGraceful)
    assert result.evidence.reaped and result.evidence.returncode == 0
    assert [s.name for s in result.evidence.signals] == ["SIGINT"]
    assert all(s.submitted for s in result.evidence.signals)
    assert b"0 packets dropped by kernel" in (req.evidence_directory / "stderr.bin").read_bytes()
    assert stop(child.handle) is result
    with pytest.raises(ChildProcessError):
        os.waitpid(child.handle.pid, os.WNOHANG)
    manifest = tomllib.loads((req.evidence_directory / "terminal.toml").read_text())
    assert manifest["intended_result"] == "recorder-graceful"
    assert manifest["publication_completion_proven"] is False


def test_inherited_masks_and_ignored_dispositions_are_child_only(tmp_path: Path) -> None:
    req = request(tmp_path)
    signals = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, signals)
    previous = {sig: signal.getsignal(sig) for sig in signals}
    try:
        for sig in signals:
            signal.signal(sig, signal.SIG_IGN)
        child = ready(req)
        result = stop(child.handle)
        assert isinstance(result, RecorderGraceful)
        witness = tomllib.loads((req.evidence_directory / "child-signals.toml").read_text())
        assert set(int(sig) for sig in signals) <= set(witness["blocked_before"])
        assert witness["blocked_after"] == []
        assert witness["dispositions_before"] == ["1", "1", "1"]
        assert witness["dispositions_after"] == [0, 0, 0]
        assert set(signals) <= signal.pthread_sigmask(signal.SIG_BLOCK, [])
        assert all(signal.getsignal(sig) == signal.SIG_IGN for sig in signals)
    finally:
        for sig, disposition in previous.items():
            signal.signal(sig, disposition)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


@pytest.mark.parametrize("mode", ["wrong-marker", "incomplete-marker"])
def test_explicit_readiness_required_and_timeout_reaped(tmp_path: Path, mode: str) -> None:
    req = request(tmp_path, mode).model_copy(update={"startup_timeout": 0.25})
    result = start(req)
    assert isinstance(result, RecorderStartFailed)
    assert "timed out" in result.reason
    assert isinstance(result.terminal, RecorderAbnormal)
    assert result.terminal.evidence.reaped
    assert result.terminal.evidence.returncode == 0
    assert (req.evidence_directory / "stdout.bin").read_bytes()


def test_exit_zero_before_ready_is_failure(tmp_path: Path) -> None:
    result = start(request(tmp_path, "exit-zero"))
    assert isinstance(result, RecorderStartFailed)
    assert result.terminal.evidence.returncode == 0
    assert isinstance(result.terminal, RecorderAbnormal)


def test_exit_after_ready_before_requested_stop_is_not_graceful(tmp_path: Path) -> None:
    child = ready(request(tmp_path))
    os.kill(child.handle.pid, signal.SIGUSR1)
    deadline = time.monotonic() + 2
    while child.handle._process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.005)
    result = stop(child.handle)
    assert isinstance(result, RecorderAbnormal)
    assert result.evidence.returncode == 0
    assert result.evidence.signals == ()


def test_nonzero_requested_stop_is_abnormal(tmp_path: Path) -> None:
    result = stop(ready(request(tmp_path, "abnormal")).handle)
    assert isinstance(result, RecorderAbnormal)
    assert result.evidence.returncode == 7


@pytest.mark.parametrize("mode", ["ignore-int", "ignore-both"])
def test_escalation_is_not_success(tmp_path: Path, mode: str) -> None:
    result = stop(ready(request(tmp_path, mode)).handle)
    assert isinstance(result, RecorderEscalated)
    assert result.evidence.reaped
    expected = ["SIGINT", "SIGTERM"] + (["SIGKILL"] if mode == "ignore-both" else [])
    assert [s.name for s in result.evidence.signals] == expected
    assert result.evidence.returncode == -(
        signal.SIGKILL if mode == "ignore-both" else signal.SIGTERM
    )


def test_exclusive_run_directory_is_preserved(tmp_path: Path) -> None:
    req = request(tmp_path)
    req.evidence_directory.mkdir()
    sentinel = req.evidence_directory / "sentinel"
    sentinel.write_bytes(b"original")
    result = start(req)
    assert isinstance(result, RecorderStartRejected)
    assert sentinel.read_bytes() == b"original"
    assert list(req.evidence_directory.iterdir()) == [sentinel]


def test_no_shell_interpretation(tmp_path: Path) -> None:
    req = request(tmp_path)
    victim = tmp_path / "shell-created"
    req = req.model_copy(update={"arguments": (*req.arguments, f"; touch {victim}")})
    result = stop(ready(req).handle)
    assert isinstance(result, RecorderGraceful)
    assert not victim.exists()


def test_bad_executable_keeps_bootstrap_failure(tmp_path: Path) -> None:
    req = request(tmp_path).model_copy(update={"executable": tmp_path.resolve() / "missing"})
    result = start(req)
    assert isinstance(result, RecorderStartFailed)
    assert result.terminal.evidence.reaped
    assert result.terminal.evidence.returncode != 0
    assert b"FileNotFoundError" in (req.evidence_directory / "stderr.bin").read_bytes()
    assert (req.evidence_directory / "child-signals.toml").exists()


def test_output_fsync_failure_never_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = ready(request(tmp_path))

    def fail_fsync(descriptor: int) -> None:
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(os, "fsync", fail_fsync)
    result = stop(child.handle)
    assert isinstance(result, RecorderCleanupUncertain)
    assert result.evidence.reaped
    assert "fsync failure" in result.evidence.reason


def test_replaced_output_path_never_succeeds(tmp_path: Path) -> None:
    req = request(tmp_path)
    child = ready(req)
    output = req.evidence_directory / "stdout.bin"
    output.rename(req.evidence_directory / "stdout-original.bin")
    output.write_bytes(b"replacement")
    result = stop(child.handle)
    assert isinstance(result, RecorderCleanupUncertain)
    assert "identity changed" in result.evidence.reason


def test_signal_failure_attempts_bounded_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = ready(request(tmp_path))
    original = child.handle._process.send_signal

    def fail_first(sig: int) -> None:
        if sig == signal.SIGINT:
            raise PermissionError("synthetic signal failure")
        original(sig)

    monkeypatch.setattr(child.handle._process, "send_signal", fail_first)
    result = stop(child.handle)
    assert isinstance(result, RecorderCleanupUncertain)
    assert result.evidence.reaped
    assert result.evidence.signals[0].submitted is False


def test_unreaped_child_is_explicit_and_test_owner_cleans_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = ready(request(tmp_path))

    def not_waited(handle: lifecycle.RecorderHandle, timeout: float) -> bool:
        return False

    def not_signaled(sig: int) -> None:
        return None

    try:
        with monkeypatch.context() as patch:
            patch.setattr(lifecycle, "_wait", not_waited)
            patch.setattr(child.handle._process, "send_signal", not_signaled)
            result = stop(child.handle)
        assert isinstance(result, RecorderCleanupUncertain)
        assert not result.evidence.reaped
        assert result.evidence.returncode is None
        assert result.evidence.pid == child.handle.pid
    finally:
        child.handle._process.kill()
        child.handle._process.wait(timeout=2)


def test_request_boundaries(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        RecorderRequest(
            executable=Path("relative"),
            evidence_directory=tmp_path,
            ready=ReadyMarker(stream="stdout", line="READY"),
        )
    with pytest.raises(ValidationError):
        ReadyMarker(stream="stdout", line="READY\n")
    with pytest.raises(ValidationError):
        RecorderRequest(
            executable=Path(sys.executable),
            evidence_directory=tmp_path,
            ready=ReadyMarker(stream="stdout", line="READY"),
            startup_timeout=0.0,
        )


@pytest.mark.parametrize("kind", ["fifo", "symlink", "oversized"])
def test_replaced_signal_witness_is_bounded_failure(tmp_path: Path, kind: str) -> None:
    req = request(tmp_path)
    child = ready(req)
    witness = req.evidence_directory / "child-signals.toml"
    witness.rename(req.evidence_directory / "original-signals.toml")
    if kind == "fifo":
        os.mkfifo(witness)
    elif kind == "symlink":
        witness.symlink_to(req.evidence_directory / "original-signals.toml")
    else:
        witness.write_bytes(b"x" * 16385)
    begin = time.monotonic()
    result = stop(child.handle)
    assert isinstance(result, RecorderCleanupUncertain)
    assert result.evidence.reaped
    assert time.monotonic() - begin < 2


def test_startup_cancellation_reaps_before_reraising(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    req = request(tmp_path)
    original = lifecycle._ready
    handles: list[lifecycle.RecorderHandle] = []

    def interrupt_at_readiness(handle: lifecycle.RecorderHandle) -> bool:
        if original(handle):
            handles.append(handle)
            raise KeyboardInterrupt("synthetic startup cancellation")
        return False

    monkeypatch.setattr(lifecycle, "_ready", interrupt_at_readiness)
    with pytest.raises(KeyboardInterrupt) as caught:
        start(req)
    assert len(handles) == 1
    assert handles[0]._process.returncode is not None
    assert any("reaped=True" in note for note in caught.value.__notes__)
    assert (req.evidence_directory / "terminal.toml").is_file()


def test_stop_cancellation_escalates_and_preserves_uncertainty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = ready(request(tmp_path, "ignore-int"))
    original = lifecycle._wait
    first = True

    def interrupt_first(handle: lifecycle.RecorderHandle, timeout: float) -> bool:
        nonlocal first
        if first:
            first = False
            raise KeyboardInterrupt("synthetic stop cancellation")
        return original(handle, timeout)

    monkeypatch.setattr(lifecycle, "_wait", interrupt_first)
    result = stop(child.handle)
    assert isinstance(result, RecorderCleanupUncertain)
    assert result.evidence.reaped
    assert [s.name for s in result.evidence.signals] == ["SIGINT", "SIGTERM"]


def test_finish_cancellation_retains_reaped_uncertainty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = ready(request(tmp_path))
    original = os.fsync
    first = True

    def interrupt_once(descriptor: int) -> None:
        nonlocal first
        if first:
            first = False
            raise KeyboardInterrupt("synthetic fsync cancellation")
        original(descriptor)

    monkeypatch.setattr(os, "fsync", interrupt_once)
    result = stop(child.handle)
    assert isinstance(result, RecorderCleanupUncertain)
    assert result.evidence.reaped
    assert child.handle._stdout.closed and child.handle._stderr.closed


def test_late_reap_preserves_previous_witness_without_resignaling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    req = request(tmp_path)
    child = ready(req)

    def not_waited(handle: lifecycle.RecorderHandle, timeout: float) -> bool:
        return False

    def not_signaled(sig: int) -> None:
        return None

    try:
        with monkeypatch.context() as patch:
            patch.setattr(lifecycle, "_wait", not_waited)
            patch.setattr(child.handle._process, "send_signal", not_signaled)
            result = stop(child.handle)
        assert isinstance(result, RecorderCleanupUncertain) and not result.evidence.reaped
        original_witness = (req.evidence_directory / "terminal.toml").read_bytes()
        os.kill(child.handle.pid, signal.SIGUSR1)
        reconciled = reap(child.handle)
        assert isinstance(reconciled, RecorderCleanupUncertain)
        assert reconciled.evidence.reaped and reconciled.evidence.returncode == 0
        assert reconciled.evidence.signals == result.evidence.signals
        assert (req.evidence_directory / "terminal.toml").read_bytes() == original_witness
        assert (req.evidence_directory / "reap-1.toml").is_file()
    finally:
        if child.handle._process.poll() is None:
            child.handle._process.kill()
            child.handle._process.wait(timeout=2)


def test_cancelled_unreaped_start_retains_typed_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    req = request(tmp_path)
    original = lifecycle._ready

    def interrupt_at_readiness(handle: lifecycle.RecorderHandle) -> bool:
        if original(handle):
            raise KeyboardInterrupt("synthetic startup cancellation")
        return False

    def not_waited(handle: lifecycle.RecorderHandle, timeout: float) -> bool:
        return False

    def not_signaled(handle: lifecycle.RecorderHandle, sig: signal.Signals) -> None:
        return None

    with monkeypatch.context() as patch:
        patch.setattr(lifecycle, "_ready", interrupt_at_readiness)
        patch.setattr(lifecycle, "_wait", not_waited)
        patch.setattr(lifecycle, "_signal", not_signaled)
        with pytest.raises(RecorderOwnershipUncertain) as caught:
            start(req)
    handle = caught.value.handle
    try:
        assert not caught.value.terminal.evidence.reaped
        assert isinstance(caught.value.__cause__, KeyboardInterrupt)
        os.kill(handle.pid, signal.SIGUSR1)
        assert reap(handle).evidence.reaped
    finally:
        if handle._process.poll() is None:
            handle._process.kill()
            handle._process.wait(timeout=2)
