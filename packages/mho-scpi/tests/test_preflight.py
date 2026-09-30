"""Unchecked typed records must not broaden the public query grammar."""

from dataclasses import dataclass

import pytest
from pydantic import BaseModel

from mho_scpi import (
    CodecLimits,
    ExchangeRejected,
    IdentityQuery,
    OptionSelector,
    OptionStatusQuery,
    Query,
    ReplyRejected,
    SessionIncomplete,
    SessionLimits,
    SessionRequest,
    decode_exchange,
    decode_reply,
    encode_query,
    execute,
)


class NoIO:
    def write(self, data: bytes, timeout: float) -> int:
        raise AssertionError("preflight attempted a write")

    def read(self, size: int, timeout: float) -> bytes:
        raise AssertionError("preflight attempted a read")


@dataclass(frozen=True)
class UncheckedSelector:
    value: str = "BND\n*RST"


def unchecked[T: BaseModel](model: T, name: str, value: object) -> T:
    # Deliberately corrupt a frozen record to test the runtime boundary.
    object.__setattr__(model, name, value)
    return model


def malformed_queries() -> tuple[Query, ...]:
    return (
        unchecked(OptionStatusQuery(selector=OptionSelector.BND), "selector", UncheckedSelector()),
        unchecked(OptionStatusQuery(selector=OptionSelector.BND), "selector", "BND"),
        unchecked(OptionStatusQuery(selector=OptionSelector.BND), "kind", "identity"),
        unchecked(OptionStatusQuery(selector=OptionSelector.BND), "selector", None),
        unchecked(IdentityQuery(), "kind", "option-status"),
    )


@pytest.mark.parametrize("query", malformed_queries())
def test_encode_rejects_unchecked_query_without_value_diagnostic(query: Query) -> None:
    with pytest.raises(ValueError) as error:
        encode_query(query)
    assert "*RST" not in str(error.value)


@pytest.mark.parametrize("query", malformed_queries())
def test_whole_plan_rejected_before_first_valid_query(query: Query) -> None:
    request = SessionRequest.model_construct(queries=(IdentityQuery(), query))
    result = execute(NoIO(), request)
    assert isinstance(result, SessionIncomplete)
    assert result.issue.code == "invalid-plan"
    assert not result.completed and result.current is None
    assert "*RST" not in repr(result)
    reply = decode_reply(query, b"1\n")
    assert isinstance(reply, ReplyRejected)
    assert reply.issue.code == "invalid-input"
    assert "*RST" not in repr(reply)


@pytest.mark.parametrize(
    "limits",
    [
        SessionLimits.model_construct(timeout_seconds=float("nan")),
        SessionLimits.model_construct(timeout_seconds=float("inf")),
        SessionLimits.model_construct(timeout_seconds=True),
        SessionLimits.model_construct(timeout_seconds=0),
        SessionLimits.model_construct(max_queries=True),
        SessionLimits.model_construct(max_queries=129),
        SessionLimits.model_construct(max_response_bytes=5000),
        SessionLimits.model_construct(max_response_bytes=True),
    ],
)
def test_unchecked_limits_rejected_before_io(limits: SessionLimits) -> None:
    result = execute(NoIO(), SessionRequest(queries=(IdentityQuery(),), limits=limits))
    assert isinstance(result, SessionIncomplete)
    assert result.issue.code == "invalid-plan"
    assert result.current is None and not result.completed


def test_mutable_unchecked_collection_is_rejected() -> None:
    result = execute(
        NoIO(), unchecked(SessionRequest(queries=(IdentityQuery(),)), "queries", [IdentityQuery()])
    )
    assert isinstance(result, SessionIncomplete) and result.issue.code == "invalid-plan"


@pytest.mark.parametrize(
    "limits",
    [
        unchecked(CodecLimits(), "max_line_bytes", float("inf")),
        CodecLimits.model_construct(max_line_bytes=True),
        CodecLimits.model_construct(max_queries=5000),
        CodecLimits.model_construct(max_exchange_bytes=32 * 1024**2),
    ],
)
def test_codec_limits_revalidated_without_model_serializer(limits: CodecLimits) -> None:
    exchange = decode_exchange(b"*IDN?\n", b"A,B,C,D\n", limits)
    assert isinstance(exchange, ExchangeRejected)
    assert exchange.issue.code == "invalid-limits"
    reply = decode_reply(IdentityQuery(), b"A,B,C,D\n", limits)
    assert isinstance(reply, ReplyRejected) and reply.issue.code == "invalid-input"


def test_unchecked_but_valid_query_is_reconstructed() -> None:
    query = OptionStatusQuery.model_construct(selector=OptionSelector.FLEX)
    assert encode_query(query) == b":SYSTem:OPTion:STATus? FLEX\n"
    assert encode_query(IdentityQuery.model_construct()) == b"*IDN?\n"
