"""Single-owner foreground child lifecycle. Descendants are not managed.

Only stop() may signal the retained Popen child. Calls on a handle must be
serialized by its owner. A successful lifecycle is not a complete capture verdict.
"""

import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import (
    RecorderAbnormal,
    RecorderCleanupUncertain,
    RecorderEscalated,
    RecorderGraceful,
    RecorderRequest,
    RecorderStartRejected,
    RecorderTerminal,
    SignalAttempt,
    TerminalEvidence,
)
from .preflight import checked_request


class SignalWitness(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    signal_schema: Literal["mho-capture.child-signals/1"] = Field(alias="schema")
    pid: int
    blocked_before: tuple[int, ...]
    blocked_after: tuple[int, ...]
    signal_names: tuple[str, ...]
    dispositions_before: tuple[str, ...]
    dispositions_after: tuple[int, ...]

    @field_validator(
        "blocked_before",
        "blocked_after",
        "signal_names",
        "dispositions_before",
        "dispositions_after",
        mode="before",
    )
    @classmethod
    def arrays(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value


@dataclass(frozen=True)
class FileStamp:
    device: int
    inode: int
    size: int
    mode: int
    mtime_ns: int
    ctime_ns: int

    @classmethod
    def read(cls, value: os.stat_result) -> "FileStamp":
        return cls(
            value.st_dev,
            value.st_ino,
            value.st_size,
            value.st_mode,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )


def _read_witness(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = FileStamp.read(os.fstat(descriptor))
        if not stat.S_ISREG(before.mode) or not 0 < before.size <= 16384:
            raise ValueError("signal witness must be a bounded regular file")
        raw = os.read(descriptor, before.size + 1)
        after = FileStamp.read(os.fstat(descriptor))
        named = FileStamp.read(os.stat(path, follow_symlinks=False))
        if len(raw) != before.size or before != after or before != named:
            raise ValueError("signal witness changed while reading")
        return raw
    finally:
        os.close(descriptor)


def _write_new(path: Path, content: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _log(path: Path) -> BinaryIO:
    return os.fdopen(os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600), "w+b")


class RecorderHandle:
    """Opaque ownership token. Use stop(); do not manipulate the child externally."""

    def __init__(
        self,
        request: RecorderRequest,
        process: subprocess.Popen[bytes],
        stdout: BinaryIO,
        stderr: BinaryIO,
    ) -> None:
        self._request = request
        self._process = process
        self._stdout = stdout
        self._stderr = stderr
        self._witness_digest: str | None = None
        self._terminal: RecorderTerminal | None = None
        self._signals: list[SignalAttempt] = []
        self._reconciliations = 0

    @property
    def request(self) -> RecorderRequest:
        """Validated immutable snapshot used by readiness and bounded cleanup."""
        return self._request

    @property
    def pid(self) -> int:
        return self._process.pid


@dataclass(frozen=True)
class OutputStream:
    stream: BinaryIO
    filename: str


def _signal(handle: RecorderHandle, sig: signal.Signals) -> None:
    submitted = False
    timestamp = time.monotonic_ns()
    try:
        handle._process.send_signal(sig)
        submitted = handle._process.returncode is None
    finally:
        handle._signals.append(SignalAttempt(sig.name, timestamp, submitted))


def _wait(handle: RecorderHandle, timeout: float) -> bool:
    try:
        handle._process.wait(timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        return False


def _finish(handle: RecorderHandle, kind: str, reason: str) -> RecorderTerminal:
    process = handle._process
    errors: list[str] = []
    outputs = [
        OutputStream(handle._stdout, "stdout.bin"),
        OutputStream(handle._stderr, "stderr.bin"),
    ]
    for output in outputs:
        stream = output.stream
        try:
            stream.flush()
            os.fsync(stream.fileno())
            observed = os.fstat(stream.fileno())
            named = os.stat(
                handle.request.evidence_directory / output.filename, follow_symlinks=False
            )
            if observed.st_dev != named.st_dev or observed.st_ino != named.st_ino:
                errors.append("retained output path identity changed")
        except (OSError, ValueError, KeyboardInterrupt, SystemExit) as error:
            errors.append(str(error))
        finally:
            try:
                stream.close()
            except (OSError, ValueError, KeyboardInterrupt, SystemExit) as error:
                errors.append(str(error))
    if handle._witness_digest is not None:
        try:
            current = _read_witness(handle.request.evidence_directory / "child-signals.toml")
            if hashlib.sha256(current).hexdigest() != handle._witness_digest:
                errors.append("signal witness changed")
        except (OSError, ValueError, KeyboardInterrupt, SystemExit) as error:
            errors.append(str(error))
    if errors:
        kind = "uncertain"
        reason += "; " + "; ".join(errors)
    evidence = TerminalEvidence(
        pid=process.pid,
        returncode=process.returncode,
        reaped=process.returncode is not None,
        signals=tuple(handle._signals),
        directory=handle.request.evidence_directory,
        reason=reason,
    )
    result: RecorderTerminal
    if kind == "graceful":
        result = RecorderGraceful(evidence)
    elif kind == "escalated":
        result = RecorderEscalated(evidence)
    elif kind == "uncertain":
        result = RecorderCleanupUncertain(evidence)
    else:
        result = RecorderAbnormal(evidence)
    lines = [
        'schema = "mho-capture.terminal/1"',
        "intended_result = " + json.dumps(result.kind),
        "publication_completion_proven = false",
        f"pid = {evidence.pid}",
        "reaped = " + str(evidence.reaped).lower(),
        "reason = " + json.dumps(reason, ensure_ascii=False),
    ]
    if evidence.returncode is not None:
        lines.append(f"returncode = {evidence.returncode}")
    for attempt in evidence.signals:
        lines.extend(
            [
                "",
                "[[signals]]",
                "name = " + json.dumps(attempt.name),
                f"monotonic_ns = {attempt.monotonic_ns}",
                "submitted = " + str(attempt.submitted).lower(),
            ]
        )
    try:
        _write_new(handle.request.evidence_directory / "terminal.toml", "\n".join(lines) + "\n")
        directory_fd = os.open(handle.request.evidence_directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except (OSError, ValueError, KeyboardInterrupt, SystemExit) as error:
        result = RecorderCleanupUncertain(
            TerminalEvidence(
                pid=evidence.pid,
                returncode=evidence.returncode,
                reaped=evidence.reaped,
                signals=evidence.signals,
                directory=evidence.directory,
                reason=reason + "; terminal publication failed: " + str(error),
            )
        )
    handle._terminal = result
    return result


def _stop(handle: RecorderHandle, failure: str | None) -> RecorderTerminal:
    if handle._terminal is not None:
        return handle._terminal
    process = handle._process
    escalated = False
    errors: list[str] = []
    if process.poll() is not None:
        return _finish(handle, "abnormal", failure or "unexpected exit before stop request")
    steps = [
        SignalStage(signal.SIGINT, handle.request.graceful_timeout),
        SignalStage(signal.SIGTERM, handle.request.terminate_timeout),
        SignalStage(signal.SIGKILL, handle.request.kill_timeout),
    ]
    for index, stage in enumerate(steps):
        escalated = index > 0
        try:
            _signal(handle, stage.sig)
            if _wait(handle, stage.timeout):
                if errors:
                    return _finish(handle, "uncertain", "; ".join(errors))
                if escalated:
                    return _finish(handle, "escalated", failure or "graceful termination timed out")
                graceful = (
                    failure is None and process.returncode == 0 and handle._signals[-1].submitted
                )
                return _finish(
                    handle,
                    "graceful" if graceful else "abnormal",
                    failure
                    or ("graceful requested stop" if graceful else "abnormal requested stop"),
                )
        except (OSError, KeyboardInterrupt, SystemExit) as error:
            errors.append(str(error))
    return _finish(
        handle, "uncertain", failure or "; ".join(errors) or "child not reaped after escalation"
    )


@dataclass(frozen=True)
class SignalStage:
    sig: signal.Signals
    timeout: float


@dataclass(frozen=True)
class RecorderReady:
    handle: RecorderHandle
    kind: Literal["recorder-ready"] = field(default="recorder-ready", init=False)


@dataclass(frozen=True)
class RecorderStartFailed:
    reason: str
    terminal: RecorderTerminal
    handle: RecorderHandle
    kind: Literal["recorder-start-failed"] = field(default="recorder-start-failed", init=False)


class RecorderOwnershipUncertain(RuntimeError):
    """Startup cancellation could not reap its child; caller retains ownership."""

    def __init__(self, handle: RecorderHandle, terminal: RecorderTerminal) -> None:
        self.handle = handle
        self.terminal = terminal
        super().__init__(f"Recorder child ownership remains unresolved for PID {handle.pid}")


def stop(handle: RecorderHandle) -> RecorderTerminal:
    """Request SIGINT, then bounded TERM/KILL cleanup. Escalation never succeeds."""
    return _stop(handle, None)


def reap(handle: RecorderHandle) -> RecorderTerminal:
    """Bounded reconciliation of retained unreaped ownership; sends no signals."""
    previous = handle._terminal
    if previous is None:
        raise ValueError("stop must establish a terminal attempt before reconciliation")
    if previous.evidence.reaped:
        return previous
    reason = previous.evidence.reason
    try:
        waited = _wait(handle, handle.request.kill_timeout)
        reason += "; subsequently reaped" if waited else "; reconciliation wait timed out"
    except (OSError, KeyboardInterrupt, SystemExit) as error:
        reason += "; reconciliation wait failed: " + type(error).__name__ + ": " + str(error)
    handle._reconciliations += 1
    evidence = TerminalEvidence(
        pid=handle.pid,
        returncode=handle._process.returncode,
        reaped=handle._process.returncode is not None,
        signals=tuple(handle._signals),
        directory=handle.request.evidence_directory,
        reason=reason,
    )
    try:
        _write_new(
            evidence.directory / f"reap-{handle._reconciliations}.toml",
            "\n".join(
                [
                    'schema = "mho-capture.reconciliation/1"',
                    'intended_result = "recorder-cleanup-uncertain"',
                    "publication_completion_proven = false",
                    f"pid = {evidence.pid}",
                    "reaped = " + str(evidence.reaped).lower(),
                    "signals_sent = 0",
                    "reason = " + json.dumps(reason, ensure_ascii=False),
                    *(
                        [f"returncode = {evidence.returncode}"]
                        if evidence.returncode is not None
                        else []
                    ),
                ]
            )
            + "\n",
        )
    except (OSError, ValueError, KeyboardInterrupt, SystemExit) as error:
        evidence = TerminalEvidence(
            pid=evidence.pid,
            returncode=evidence.returncode,
            reaped=evidence.reaped,
            signals=evidence.signals,
            directory=evidence.directory,
            reason=reason + "; reconciliation publication failed: " + str(error),
        )
    result = RecorderCleanupUncertain(evidence)
    handle._terminal = result
    return result


def _ready(handle: RecorderHandle) -> bool:
    stream = handle._stdout if handle.request.ready.stream == "stdout" else handle._stderr
    size = os.fstat(stream.fileno()).st_size
    if size > 1024 * 1024:
        raise ValueError("readiness output exceeds 1 MiB bound")
    raw = os.pread(stream.fileno(), size, 0)
    expected = handle.request.ready.line.encode("utf-8")
    return expected in raw.split(b"\n")[:-1]


def _witness(handle: RecorderHandle) -> None:
    path = handle.request.evidence_directory / "child-signals.toml"
    raw = _read_witness(path)
    witness = SignalWitness.model_validate(tomllib.loads(raw.decode("utf-8")))
    if (
        witness.pid != handle.pid
        or witness.blocked_after != ()
        or witness.signal_names != ("SIGINT", "SIGTERM", "SIGHUP")
        or witness.dispositions_after != (0, 0, 0)
    ):
        raise ValueError("child signal normalization not established")
    handle._witness_digest = hashlib.sha256(raw).hexdigest()


def start(request: RecorderRequest) -> RecorderReady | RecorderStartRejected | RecorderStartFailed:
    """Start exactly one foreground child and wait for an explicit complete line."""
    checked = checked_request(request)
    if checked is None:
        return RecorderStartRejected("request violates the bounded recorder contract", None)
    request = checked
    stdout: BinaryIO | None = None
    stderr: BinaryIO | None = None
    try:
        request.evidence_directory.mkdir(mode=0o700)
        launch_path = request.evidence_directory / "launch.toml"
        _write_new(
            launch_path,
            "\n".join(
                [
                    "executable = " + json.dumps(str(request.executable), ensure_ascii=False),
                    "arguments = " + json.dumps(list(request.arguments), ensure_ascii=False),
                    "witness = "
                    + json.dumps(
                        str(request.evidence_directory / "child-signals.toml"), ensure_ascii=False
                    ),
                ]
            )
            + "\n",
        )
        stdout = _log(request.evidence_directory / "stdout.bin")
        stderr = _log(request.evidence_directory / "stderr.bin")
        process = subprocess.Popen(
            [sys.executable, "-I", "-m", "mho_capture._child", str(launch_path)],
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            close_fds=True,
            restore_signals=False,
            start_new_session=True,
        )
    except OSError as error:
        for stream in (stdout, stderr):
            if stream is not None:
                stream.close()
        return RecorderStartRejected(str(error), request.evidence_directory)
    handle = RecorderHandle(request, process, stdout, stderr)
    deadline = time.monotonic() + request.startup_timeout
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                reason = "child exited before readiness"
                return RecorderStartFailed(reason, _stop(handle, reason), handle)
            if _ready(handle):
                _witness(handle)
                if process.poll() is None:
                    _write_new(
                        request.evidence_directory / "ready.toml",
                        "\n".join(
                            [
                                'schema = "mho-capture.readiness/1"',
                                f"pid = {handle.pid}",
                                f"monotonic_ns = {time.monotonic_ns()}",
                                "stream = " + json.dumps(request.ready.stream),
                                "marker = " + json.dumps(request.ready.line, ensure_ascii=False),
                                "signal_witness_sha256 = " + json.dumps(handle._witness_digest),
                            ]
                        )
                        + "\n",
                    )
                    return RecorderReady(handle)
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        reason = "startup readiness timed out"
    except (OSError, ValueError) as error:
        reason = "startup evidence failed: " + str(error)
    except BaseException as error:
        terminal = _stop(handle, "startup cancelled: " + type(error).__name__)
        if not terminal.evidence.reaped:
            raise RecorderOwnershipUncertain(handle, terminal) from error
        error.add_note(
            f"Recorder cleanup: pid={terminal.evidence.pid}, "
            f"reaped={terminal.evidence.reaped}, result={terminal.kind}"
        )
        raise
    return RecorderStartFailed(reason, _stop(handle, reason), handle)
