"""Serial query execution on a supplied stream; never opens a connection.

The backend must honor supplied remaining-time budgets. A synchronous library
cannot forcibly interrupt a backend that violates that contract; late returns
are rejected and their observable progress is retained.
"""

import time
from dataclasses import dataclass, field

from .codec import decode_reply, encode_query
from .models import CodecLimits, Query, ReplyRejected
from .session_models import (
    ByteStream,
    CompletedExchange,
    PartialExchange,
    ReadProgress,
    SessionComplete,
    SessionIncomplete,
    SessionIssue,
    SessionRequest,
    StreamFailure,
    WriteProgress,
)


@dataclass(frozen=True)
class PreparedQuery:
    query: Query
    wire: bytes


@dataclass
class Progress:
    prepared: PreparedQuery
    index: int
    submitted: int = 0
    response: bytearray = field(default_factory=bytearray)
    write_unknown: bool = False
    read_unknown: bool = False
    restoration_failed: bool = False
    omitted_response_bytes: int = 0
    backend_diagnostic: str | None = None

    def freeze(self) -> PartialExchange:
        return PartialExchange(
            query=self.prepared.query,
            request=self.prepared.wire,
            submitted_bytes=self.submitted,
            received_prefix=bytes(self.response),
            write_progress_unknown=self.write_unknown,
            read_progress_unknown=self.read_unknown,
            timeout_restoration_failed=self.restoration_failed,
            omitted_response_bytes=self.omitted_response_bytes,
            backend_diagnostic=self.backend_diagnostic,
        )


def _stream_code(error: StreamFailure) -> str:
    if error.code in {"stream-timeout", "stream-state", "invalid-timeout", "timeout-restoration"}:
        return error.code
    return "stream-error"


def _incomplete(
    completed: list[CompletedExchange],
    current: Progress | None,
    code: str,
    message: str,
    began: float,
) -> SessionIncomplete:
    return SessionIncomplete(
        completed=tuple(completed),
        current=current.freeze() if current is not None else None,
        issue=SessionIssue(code, message, current.index if current is not None else None),
        elapsed_seconds=max(0, time.monotonic() - began),
    )


def _write_progress(current: Progress, amount: object) -> bool:
    remaining = len(current.prepared.wire) - current.submitted
    if not isinstance(amount, int) or isinstance(amount, bool) or not 0 <= amount <= remaining:
        current.write_unknown = True
        return False
    current.submitted += amount
    return True


def _read_progress(current: Progress, raw: object, cap: int) -> bool:
    if not isinstance(raw, bytes):
        current.read_unknown = True
        return False
    retained = raw[: max(0, cap - len(current.response))]
    current.response.extend(retained)
    current.omitted_response_bytes += len(raw) - len(retained)
    return len(raw) <= 1


def execute(stream: ByteStream, request: SessionRequest) -> SessionComplete | SessionIncomplete:
    """Run only allowlisted typed queries, preserving confirmed prefixes on failure.

    No query is retried. Continuing a partial write sends only its unsubmitted
    suffix. Each next query starts after one complete validated response line.
    The caller must establish a clean, exclusively owned stream. Queued stale
    replies cannot be distinguished from current replies; surplus bytes remain
    unread. Completion proves neither response causality nor stream exhaustion.
    """
    began = time.monotonic()
    deadline = began + request.limits.timeout_seconds
    completed: list[CompletedExchange] = []
    if not request.queries or len(request.queries) > request.limits.max_queries:
        return _incomplete(
            completed, None, "query-limit", "query plan outside configured bounds", began
        )
    prepared = [PreparedQuery(query, encode_query(query)) for query in request.queries]
    codec_limits = CodecLimits(max_line_bytes=request.limits.max_response_bytes)
    for index, query in enumerate(prepared):
        current = Progress(prepared=query, index=index)
        while current.submitted < len(query.wire):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return _incomplete(
                    completed,
                    current,
                    "deadline",
                    "transaction deadline expired before write",
                    began,
                )
            try:
                written = stream.write(query.wire[current.submitted :], remaining)
            except StreamFailure as error:
                current.backend_diagnostic = str(error)
                current.restoration_failed = error.timeout_restoration_failed
                if isinstance(error.progress, WriteProgress):
                    valid = _write_progress(current, error.progress.count)
                    if not valid:
                        return _incomplete(
                            completed,
                            current,
                            "backend-write-count",
                            "backend returned invalid write progress",
                            began,
                        )
                else:
                    current.write_unknown = error.operation_started
                return _incomplete(
                    completed,
                    current,
                    _stream_code(error),
                    "supplied stream operation failed",
                    began,
                )
            except (OSError, ValueError) as error:
                current.backend_diagnostic = str(error)
                current.write_unknown = True
                code = "stream-timeout" if isinstance(error, TimeoutError) else "stream-error"
                return _incomplete(
                    completed, current, code, "supplied stream operation failed", began
                )
            if not _write_progress(current, written):
                return _incomplete(
                    completed,
                    current,
                    "backend-write-count",
                    "backend returned invalid write count",
                    began,
                )
            if written == 0:
                return _incomplete(
                    completed, current, "zero-write", "backend made no write progress", began
                )
            if time.monotonic() >= deadline:
                return _incomplete(
                    completed,
                    current,
                    "deadline",
                    "transaction deadline expired during write",
                    began,
                )
        while True:
            if len(current.response) >= request.limits.max_response_bytes:
                return _incomplete(
                    completed,
                    current,
                    "response-limit",
                    "response exceeds configured line limit",
                    began,
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return _incomplete(
                    completed,
                    current,
                    "deadline",
                    "transaction deadline expired before read",
                    began,
                )
            try:
                received = stream.read(1, remaining)
            except StreamFailure as error:
                current.backend_diagnostic = str(error)
                current.restoration_failed = error.timeout_restoration_failed
                if isinstance(error.progress, ReadProgress):
                    valid = _read_progress(
                        current, error.progress.data, request.limits.max_response_bytes
                    )
                    if not valid:
                        return _incomplete(
                            completed,
                            current,
                            "backend-read-size",
                            "backend exceeded requested read size",
                            began,
                        )
                else:
                    current.read_unknown = error.operation_started
                return _incomplete(
                    completed,
                    current,
                    _stream_code(error),
                    "supplied stream operation failed",
                    began,
                )
            except (OSError, ValueError) as error:
                current.backend_diagnostic = str(error)
                current.read_unknown = True
                code = "stream-timeout" if isinstance(error, TimeoutError) else "stream-error"
                return _incomplete(
                    completed, current, code, "supplied stream operation failed", began
                )
            if not _read_progress(current, received, request.limits.max_response_bytes):
                return _incomplete(
                    completed,
                    current,
                    "backend-read-size",
                    "backend exceeded requested read size",
                    began,
                )
            if not received:
                return _incomplete(
                    completed, current, "eof", "stream ended before complete reply", began
                )
            if time.monotonic() >= deadline:
                return _incomplete(
                    completed,
                    current,
                    "deadline",
                    "transaction deadline expired during read",
                    began,
                )
            if received == b"\n":
                break
        decoded = decode_reply(query.query, bytes(current.response), codec_limits)
        if isinstance(decoded, ReplyRejected):
            return _incomplete(completed, current, decoded.issue.code, decoded.issue.message, began)
        if time.monotonic() >= deadline:
            return _incomplete(
                completed, current, "deadline", "transaction deadline expired during decode", began
            )
        completed.append(CompletedExchange(query=query.query, request=query.wire, reply=decoded))
    return SessionComplete(
        exchanges=tuple(completed), elapsed_seconds=max(0, time.monotonic() - began)
    )
