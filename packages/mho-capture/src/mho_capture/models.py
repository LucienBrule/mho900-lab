"""Named recorder requests and terminal evidence; no packet-loss claims."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReadyMarker(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    stream: Literal["stdout", "stderr"]
    line: str = Field(min_length=1, max_length=512)

    @field_validator("line")
    @classmethod
    def one_line(cls, value: str) -> str:
        if any(c in value for c in ("\n", "\r", "\0")):
            raise ValueError("readiness marker must be one complete nonempty line")
        return value


class RecorderRequest(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    executable: Path
    arguments: tuple[str, ...] = ()
    evidence_directory: Path
    ready: ReadyMarker
    startup_timeout: float = Field(default=5.0, gt=0, le=60)
    graceful_timeout: float = Field(default=5.0, gt=0, le=60)
    terminate_timeout: float = Field(default=2.0, gt=0, le=60)
    kill_timeout: float = Field(default=2.0, gt=0, le=60)

    @field_validator("executable", "evidence_directory")
    @classmethod
    def absolute_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("paths must be absolute")
        if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in str(value)):
            raise ValueError("paths contain unsupported characters")
        return value

    @field_validator("arguments")
    @classmethod
    def valid_arguments(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in arg) for arg in value):
            raise ValueError("arguments contain unsupported characters")
        return value


@dataclass(frozen=True)
class SignalAttempt:
    name: str
    monotonic_ns: int
    submitted: bool


@dataclass(frozen=True)
class TerminalEvidence:
    pid: int
    returncode: int | None
    reaped: bool
    signals: tuple[SignalAttempt, ...]
    directory: Path
    reason: str


@dataclass(frozen=True)
class RecorderGraceful:
    evidence: TerminalEvidence
    kind: Literal["recorder-graceful"] = field(default="recorder-graceful", init=False)


@dataclass(frozen=True)
class RecorderAbnormal:
    evidence: TerminalEvidence
    kind: Literal["recorder-abnormal"] = field(default="recorder-abnormal", init=False)


@dataclass(frozen=True)
class RecorderEscalated:
    evidence: TerminalEvidence
    kind: Literal["recorder-escalated"] = field(default="recorder-escalated", init=False)


@dataclass(frozen=True)
class RecorderCleanupUncertain:
    evidence: TerminalEvidence
    kind: Literal["recorder-cleanup-uncertain"] = field(
        default="recorder-cleanup-uncertain", init=False
    )


type RecorderTerminal = (
    RecorderGraceful | RecorderAbnormal | RecorderEscalated | RecorderCleanupUncertain
)


@dataclass(frozen=True)
class RecorderStartRejected:
    reason: str
    directory: Path
    kind: Literal["recorder-start-rejected"] = field(default="recorder-start-rejected", init=False)
