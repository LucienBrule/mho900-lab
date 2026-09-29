"""Deterministic supplied streams and owned AF_UNIX socket pairs only."""

import socket
from dataclasses import dataclass, field
from typing import Literal

import pytest
from pydantic import ValidationError

import mho_scpi.session as session_module
from mho_scpi import (
    IdentityQuery,
    OptionSelector,
    OptionStatusQuery,
    ReadProgress,
    SessionComplete,
    SessionIncomplete,
    SessionLimits,
    SessionRequest,
    SocketStream,
    StreamFailure,
    WriteProgress,
    execute,
)


@dataclass(frozen=True)
class Call:
    operation: Literal["read", "write"]
    budget: float
    data: bytes = b""
    size: int = 0


@dataclass
class MemoryStream:
    response: bytes
    write_chunk: int = 2
    offset: int = 0
    calls: list[Call] = field(default_factory=list)
    submitted: bytearray = field(default_factory=bytearray)

    def write(self, data: bytes, timeout: float) -> int:
        amount = min(self.write_chunk, len(data))
        self.calls.append(Call("write", timeout, data=data))
        self.submitted.extend(data[:amount])
        return amount

    def read(self, size: int, timeout: float) -> bytes:
        self.calls.append(Call("read", timeout, size=size))
        result = self.response[self.offset : self.offset + size]
        self.offset += len(result)
        return result


def status_request(*, count: int = 1, limits: SessionLimits | None = None) -> SessionRequest:
    return SessionRequest(
        queries=tuple(OptionStatusQuery(selector=OptionSelector.FLEX) for _ in range(count)),
        limits=limits or SessionLimits(),
    )


def test_short_writes_and_one_byte_reads_keep_exact_exchange_order() -> None:
    stream = MemoryStream(b"RIGOL,MHO984,SYNTHETIC,00.01.00\r\n1\n")
    req = SessionRequest(queries=(IdentityQuery(), OptionStatusQuery(selector=OptionSelector.FLEX)))
    result = execute(stream, req)
    assert isinstance(result, SessionComplete)
    assert bytes(stream.submitted) == b"*IDN?\n:SYSTem:OPTion:STATus? FLEX\n"
    assert result.exchanges[0].reply.raw == b"RIGOL,MHO984,SYNTHETIC,00.01.00\r\n"
    assert result.exchanges[1].reply.raw == b"1\n"
    assert all(call.size == 1 for call in stream.calls if call.operation == "read")
    operations = "".join("W" if call.operation == "write" else "R" for call in stream.calls)
    assert operations == "WWW" + "R" * 33 + "W" * 14 + "RR"
    assert result.peer_delivery_proven is False and result.device_execution_proven is False


def test_eof_preserves_completed_prefix_and_partial_reply() -> None:
    stream = MemoryStream(b"1\n0")
    result = execute(stream, status_request(count=2))
    assert isinstance(result, SessionIncomplete)
    assert len(result.completed) == 1
    assert result.current is not None
    assert result.current.received_prefix == b"0"
    assert result.current.submitted_bytes == len(result.current.request)
    assert result.issue.code == "eof" and result.issue.query_index == 1
    assert result.current.read_progress_unknown is False


def test_zero_write_stops_without_retry() -> None:
    stream = MemoryStream(b"1\n", write_chunk=0)
    result = execute(stream, status_request())
    assert isinstance(result, SessionIncomplete)
    assert result.issue.code == "zero-write"
    assert len(stream.calls) == 1 and result.current is not None
    assert result.current.submitted_bytes == 0 and not result.current.write_progress_unknown


@pytest.mark.parametrize("count", [-1, 9999, True])
def test_invalid_backend_write_progress_is_not_accepted(count: int) -> None:
    class InvalidWrite(MemoryStream):
        def write(self, data: bytes, timeout: float) -> int:
            return count

    result = execute(InvalidWrite(b""), status_request())
    assert isinstance(result, SessionIncomplete)
    assert result.issue.code == "backend-write-count"
    assert result.current is not None and result.current.write_progress_unknown


def test_exception_after_partial_write_does_not_claim_zero_progress_or_retry() -> None:
    class TimeoutWrite(MemoryStream):
        def write(self, data: bytes, timeout: float) -> int:
            if self.submitted:
                raise TimeoutError("synthetic timeout")
            return super().write(data, timeout)

    stream = TimeoutWrite(b"")
    result = execute(stream, status_request())
    assert isinstance(result, SessionIncomplete) and result.current is not None
    assert result.issue.code == "stream-timeout"
    assert result.current.submitted_bytes == 2 and result.current.write_progress_unknown
    assert bytes(stream.submitted) == result.current.request[:2]


def test_backend_read_overrun_is_retained_bounded_and_rejected() -> None:
    class OverRead(MemoryStream):
        def read(self, size: int, timeout: float) -> bytes:
            return b"1\nextra"

    result = execute(OverRead(b""), status_request(limits=SessionLimits(max_response_bytes=2)))
    assert isinstance(result, SessionIncomplete) and result.current is not None
    assert result.issue.code == "backend-read-size"
    assert result.current.received_prefix == b"1\n" and result.current.omitted_response_bytes == 5
    assert result.completed == ()


def test_response_cap_never_consumes_past_the_bound() -> None:
    stream = MemoryStream(b"00\n")
    result = execute(stream, status_request(limits=SessionLimits(max_response_bytes=2)))
    assert isinstance(result, SessionIncomplete) and result.current is not None
    assert result.issue.code == "response-limit"
    assert result.current.received_prefix == b"00" and stream.offset == 2
    exact = execute(
        MemoryStream(b"1\n"), status_request(limits=SessionLimits(max_response_bytes=2))
    )
    assert isinstance(exact, SessionComplete)


def test_malformed_reply_stops_before_the_next_query() -> None:
    stream = MemoryStream(b"2\n1\n")
    result = execute(stream, status_request(count=2))
    assert isinstance(result, SessionIncomplete) and result.current is not None
    assert result.issue.code == "option-state"
    assert stream.submitted.count(b"\n") == 1 and stream.offset == 2
    assert result.current.received_prefix == b"2\n"


@pytest.mark.parametrize("count", [0, 2])
def test_empty_or_oversized_plan_never_calls_stream(count: int) -> None:
    stream = MemoryStream(b"")
    result = execute(stream, status_request(count=count, limits=SessionLimits(max_queries=1)))
    assert isinstance(result, SessionIncomplete)
    assert result.current is None and result.issue.code == "query-limit"
    assert not stream.calls


def test_arbitrary_commands_are_not_a_request_alternative() -> None:
    with pytest.raises(ValidationError):
        SessionRequest.model_validate({"queries": ({"kind": "arbitrary", "command": "*RST"},)})


@dataclass
class Clock:
    value: float = 0.0

    def monotonic(self) -> float:
        return self.value


def test_whole_transaction_deadline_does_not_reset_per_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = Clock()

    class AdvancingStream(MemoryStream):
        def read(self, size: int, timeout: float) -> bytes:
            value = super().read(size, timeout)
            clock.value += 0.3
            return value

    monkeypatch.setattr(session_module, "time", clock)
    stream = AdvancingStream(b"1\n1\n", write_chunk=1000)
    result = execute(stream, status_request(count=2, limits=SessionLimits(timeout_seconds=1.0)))
    assert isinstance(result, SessionIncomplete) and result.current is not None
    assert len(result.completed) == 1 and result.issue.code == "deadline"
    assert result.current.received_prefix == b"1\n"
    assert result.elapsed_seconds == pytest.approx(1.2)
    budgets = [call.budget for call in stream.calls]
    assert budgets == sorted(budgets, reverse=True)


def test_late_write_retains_confirmed_count(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = Clock()

    class LateWriter(MemoryStream):
        def write(self, data: bytes, timeout: float) -> int:
            count = super().write(data, timeout)
            clock.value = 2.0
            return count

    monkeypatch.setattr(session_module, "time", clock)
    result = execute(LateWriter(b""), status_request(limits=SessionLimits(timeout_seconds=1.0)))
    assert isinstance(result, SessionIncomplete) and result.current is not None
    assert result.issue.code == "deadline" and result.current.submitted_bytes == 2
    assert not result.current.write_progress_unknown


@pytest.mark.parametrize("previous", [None, 0.75])
def test_supplied_unix_socket_restores_timeout_and_remains_open(previous: float | None) -> None:
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        left.settimeout(previous)
        right.sendall(b"1\n")
        result = execute(SocketStream(left), status_request())
        assert isinstance(result, SessionComplete)
        assert left.gettimeout() == previous and left.fileno() >= 0
        assert right.recv(128) == b":SYSTem:OPTion:STATus? FLEX\n"
    finally:
        left.close()
        right.close()


def test_socket_timeout_restores_original_state() -> None:
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        left.settimeout(0.75)
        result = execute(
            SocketStream(left), status_request(limits=SessionLimits(timeout_seconds=0.03))
        )
        assert isinstance(result, SessionIncomplete) and result.current is not None
        assert result.issue.code == "stream-timeout"
        assert result.current.read_progress_unknown and left.gettimeout() == 0.75
        assert left.fileno() >= 0
    finally:
        left.close()
        right.close()


class RestoreFailureSocket(socket.socket):
    def __init__(self, original: socket.socket, fail_on: int) -> None:
        super().__init__(fileno=original.detach())
        self.timeout_calls = 0
        self.fail_on = fail_on

    def settimeout(self, value: float | None) -> None:
        self.timeout_calls += 1
        if self.timeout_calls == self.fail_on:
            raise OSError("synthetic restoration failure")
        super().settimeout(value)


@pytest.mark.parametrize("fail_on", [2, 4])
def test_socket_restoration_failure_retains_actual_progress(fail_on: int) -> None:
    original, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    left = RestoreFailureSocket(original, fail_on)
    try:
        right.sendall(b"1\n")
        result = execute(SocketStream(left), status_request())
        assert isinstance(result, SessionIncomplete) and result.current is not None
        assert result.issue.code == "timeout-restoration"
        assert result.current.timeout_restoration_failed
        assert result.current.submitted_bytes == len(result.current.request)
        assert not result.current.write_progress_unknown
        assert result.current.received_prefix == (b"1" if fail_on == 4 else b"")
        assert left.fileno() >= 0
    finally:
        left.close()
        right.close()


def test_typed_failures_preserve_returned_progress() -> None:
    class FailedWrite(MemoryStream):
        def write(self, data: bytes, timeout: float) -> int:
            raise StreamFailure("failure", "synthetic", progress=WriteProgress(3))

    class FailedRead(MemoryStream):
        def read(self, size: int, timeout: float) -> bytes:
            raise StreamFailure("failure", "synthetic", progress=ReadProgress(b"1"))

    written = execute(FailedWrite(b""), status_request())
    received = execute(FailedRead(b""), status_request())
    assert isinstance(written, SessionIncomplete) and written.current is not None
    assert written.current.submitted_bytes == 3 and not written.current.write_progress_unknown
    assert isinstance(received, SessionIncomplete) and received.current is not None
    assert received.current.received_prefix == b"1" and not received.current.read_progress_unknown


def test_queued_replies_and_surplus_do_not_establish_causality_or_exhaustion() -> None:
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        left.settimeout(0.75)
        # All responses deliberately predate submission of either query.
        right.sendall(b"1\n0\nEXTRA\n")
        result = execute(SocketStream(left), status_request(count=2))
        assert isinstance(result, SessionComplete)
        assert [item.reply.raw for item in result.exchanges] == [b"1\n", b"0\n"]
        assert result.response_causality_proven is False
        assert result.stream_exhaustion_proven is False
        assert left.gettimeout() == 0.75
        assert left.recv(128) == b"EXTRA\n"
        assert right.recv(128) == b":SYSTem:OPTion:STATus? FLEX\n" * 2
    finally:
        left.close()
        right.close()


def test_backend_diagnostic_is_retained_but_not_rendered_in_issue() -> None:
    class DiagnosticStream(MemoryStream):
        def write(self, data: bytes, timeout: float) -> int:
            raise StreamFailure("PRIVATE-CODE", "PRIVATE-BACKEND-DATA")

    result = execute(DiagnosticStream(b""), status_request())
    assert isinstance(result, SessionIncomplete) and result.current is not None
    assert result.current.backend_diagnostic == "PRIVATE-BACKEND-DATA"
    assert "PRIVATE" not in repr(result)
    assert result.issue.code == "stream-error"


def test_failure_before_operation_does_not_invent_submission_uncertainty() -> None:
    class NoOperation(MemoryStream):
        def write(self, data: bytes, timeout: float) -> int:
            raise StreamFailure("stream-state", "not started", operation_started=False)

    result = execute(NoOperation(b""), status_request())
    assert isinstance(result, SessionIncomplete) and result.current is not None
    assert result.current.submitted_bytes == 0 and not result.current.write_progress_unknown


def test_serialized_query_plan_requires_discriminator() -> None:
    with pytest.raises(ValidationError):
        SessionRequest.model_validate({"queries": ({},)})
    parsed = SessionRequest.model_validate({"queries": ({"kind": "identity"},)})
    assert parsed.queries == (IdentityQuery(),)
