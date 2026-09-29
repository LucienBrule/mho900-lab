"""Supplied-stream contracts and named partial evidence; no connection setup."""

from dataclasses import dataclass, field
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .models import Query, ReplyAccepted


class ByteStream(Protocol):
    """Exclusive stream; timeout is a maximum budget for this one operation.

    Backends must honor the deadline, return actual progress, and not prefetch
    bytes beyond size. Exceptions without progress cannot establish submission.
    """

    def write(self, data: bytes, timeout: float) -> int: ...

    def read(self, size: int, timeout: float) -> bytes: ...


class SessionLimits(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    max_response_bytes: int = Field(default=4096, ge=2, le=4096)
    max_queries: int = Field(default=32, ge=1, le=128)


class SessionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    queries: tuple[Annotated[Query, Field(discriminator="kind")], ...]
    limits: SessionLimits = Field(default_factory=SessionLimits)


@dataclass(frozen=True)
class WriteProgress:
    count: int


@dataclass(frozen=True)
class ReadProgress:
    data: bytes


type StreamProgress = WriteProgress | ReadProgress


class StreamFailure(OSError):
    """An operation failed, optionally after observable progress was returned."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        progress: StreamProgress | None = None,
        operation_started: bool = True,
        timeout_restoration_failed: bool = False,
    ) -> None:
        self.code = code
        self.progress = progress
        self.operation_started = operation_started
        self.timeout_restoration_failed = timeout_restoration_failed
        super().__init__(message)


@dataclass(frozen=True)
class SessionIssue:
    code: str
    message: str
    query_index: int | None = None


@dataclass(frozen=True)
class CompletedExchange:
    query: Query
    request: bytes = field(repr=False)
    reply: ReplyAccepted = field(repr=False)


@dataclass(frozen=True)
class PartialExchange:
    query: Query
    request: bytes = field(repr=False)
    submitted_bytes: int
    received_prefix: bytes = field(repr=False)
    write_progress_unknown: bool
    read_progress_unknown: bool
    timeout_restoration_failed: bool
    omitted_response_bytes: int = 0
    backend_diagnostic: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class SessionComplete:
    exchanges: tuple[CompletedExchange, ...]
    elapsed_seconds: float
    peer_delivery_proven: Literal[False] = False
    device_execution_proven: Literal[False] = False
    stream_exhaustion_proven: Literal[False] = False
    response_causality_proven: Literal[False] = False
    kind: Literal["scpi-session-complete"] = field(default="scpi-session-complete", init=False)


@dataclass(frozen=True)
class SessionIncomplete:
    completed: tuple[CompletedExchange, ...]
    current: PartialExchange | None
    issue: SessionIssue
    elapsed_seconds: float
    peer_delivery_proven: Literal[False] = False
    device_execution_proven: Literal[False] = False
    stream_exhaustion_proven: Literal[False] = False
    response_causality_proven: Literal[False] = False
    kind: Literal["scpi-session-incomplete"] = field(default="scpi-session-incomplete", init=False)
