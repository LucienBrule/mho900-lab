"""Supported recorder strings retain their value through actual child records."""

import signal
import sys
import tomllib
from pathlib import Path

import pytest

from mho_capture import (
    ReadyMarker,
    RecorderCleanupUncertain,
    RecorderGraceful,
    RecorderReady,
    RecorderRequest,
    lifecycle,
    reap,
    start,
    stop,
)
from mho_capture._toml import string, strings


@pytest.mark.parametrize(
    "value", ["", "\x7f", 'quote" slash\\', "café 🕯", "".join(chr(n) for n in range(128))]
)
def test_scalar_and_array_roundtrips(value: str) -> None:
    assert tomllib.loads("value = " + string(value))["value"] == value
    assert tomllib.loads("value = " + strings((value, "suffix")))["value"] == [value, "suffix"]


def test_del_bearing_arguments_readiness_and_paths_roundtrip(tmp_path: Path) -> None:
    parent = (tmp_path / "synthetic\x7fparent").resolve()
    parent.mkdir()
    script = parent / "child.py"
    script.write_text(
        "import signal,sys\n"
        "signal.signal(signal.SIGINT, lambda number, frame: sys.exit(0))\n"
        "print(sys.argv[1], flush=True)\n"
        "while True: signal.pause()\n"
    )
    marker = "READY\x7fMARKER 🕯"
    request = RecorderRequest(
        executable=Path(sys.executable).resolve(),
        arguments=(str(script), marker),
        evidence_directory=parent / "record",
        ready=ReadyMarker(stream="stdout", line=marker),
    )
    result = start(request)
    assert isinstance(result, RecorderReady)
    try:
        terminal = stop(result.handle)
        assert isinstance(terminal, RecorderGraceful) and terminal.evidence.reaped
    finally:
        stop(result.handle)
        reap(result.handle)
    root = request.evidence_directory
    launch = tomllib.loads((root / "launch.toml").read_text())
    ready = tomllib.loads((root / "ready.toml").read_text())
    terminal_record = tomllib.loads((root / "terminal.toml").read_text())
    assert launch["arguments"] == [str(script), marker]
    assert launch["witness"] == str(root / "child-signals.toml")
    assert ready["marker"] == marker
    assert terminal_record["reaped"] is True


def test_terminal_and_reconciliation_preserve_diagnostic_strings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "child.py"
    script.write_text(
        "import signal,sys\n"
        "signal.signal(signal.SIGINT, lambda number, frame: sys.exit(0))\n"
        "print('READY', flush=True)\n"
        "while True: signal.pause()\n"
    )
    request = RecorderRequest(
        executable=Path(sys.executable).resolve(),
        arguments=(str(script),),
        evidence_directory=tmp_path / "record",
        ready=ReadyMarker(stream="stdout", line="READY"),
    )
    result = start(request)
    assert isinstance(result, RecorderReady)
    diagnostic = "synthetic diagnostic\x7f 🕯"

    def not_waited(handle: lifecycle.RecorderHandle, timeout: float) -> bool:
        return False

    def not_signaled(handle: lifecycle.RecorderHandle, sig: signal.Signals) -> None:
        return None

    try:
        with monkeypatch.context() as patch:
            patch.setattr(lifecycle, "_wait", not_waited)
            patch.setattr(lifecycle, "_signal", not_signaled)
            terminal = lifecycle._stop(result.handle, diagnostic)
        assert isinstance(terminal, RecorderCleanupUncertain)
        assert not terminal.evidence.reaped
        root = request.evidence_directory
        original = (root / "terminal.toml").read_bytes()
        assert tomllib.loads(original.decode())["reason"] == diagnostic
        result.handle._process.send_signal(signal.SIGINT)
        reconciled = reap(result.handle)
        assert isinstance(reconciled, RecorderCleanupUncertain)
        assert reconciled.evidence.reaped
        assert (root / "terminal.toml").read_bytes() == original
        record = tomllib.loads((root / "reap-1.toml").read_text())
        assert record["reason"] == diagnostic + "; subsequently reaped"
    finally:
        if result.handle._process.poll() is None:
            result.handle._process.kill()
            result.handle._process.wait(timeout=2)
