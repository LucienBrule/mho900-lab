"""Only synthetic identity values; no private unit data or network operations."""

from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from mho_scpi import (
    CodecLimits,
    ExchangeAccepted,
    ExchangeRejected,
    IdentityObservation,
    IdentityQuery,
    OptionSelector,
    OptionState,
    OptionStatusObservation,
    OptionStatusQuery,
    ReplyAccepted,
    ReplyRejected,
    decode_exchange,
    decode_reply,
    encode_query,
)


@pytest.mark.parametrize("selector", list(OptionSelector))
def test_exact_option_encoding_and_reply(selector: OptionSelector) -> None:
    query = OptionStatusQuery(selector=selector)
    assert (
        encode_query(query) == b":SYSTem:OPTion:STATus? " + selector.value.encode("ascii") + b"\n"
    )
    for raw in (b"0\n", b"1\r\n"):
        result = decode_reply(query, raw)
        assert isinstance(result, ReplyAccepted)
        assert result.raw == raw and result.query == query
        assert isinstance(result.observation, OptionStatusObservation)
        assert result.observation.selector == selector
        assert result.observation.state == (
            OptionState.DISABLED if raw[0] == 48 else OptionState.ENABLED
        )


def test_selector_inventory_is_exact() -> None:
    assert [selector.value for selector in OptionSelector] == [
        "BND",
        "AFG100",
        "AFG50",
        "AUDio",
        "CAN-FD",
        "FLEX",
        "AERO",
        "RLU-05",
        "BWU03T05",
        "BWU03T08",
        "BWU05T08",
    ]


@pytest.mark.parametrize("terminator", [b"\n", b"\r\n"])
def test_identity_fields_are_opaque_exact_strings(terminator: bytes) -> None:
    query = IdentityQuery()
    assert encode_query(query) == b"*IDN?\n"
    raw = b" Example Vendor ,Model Example,SYNTHETIC-0001,00.01.00 test suffix " + terminator
    result = decode_reply(query, raw)
    assert isinstance(result, ReplyAccepted)
    assert result.raw == raw
    assert isinstance(result.observation, IdentityObservation)
    assert result.observation.manufacturer == " Example Vendor "
    assert result.observation.model == "Model Example"
    assert result.observation.serial_number == "SYNTHETIC-0001"
    assert result.observation.software_revision == "00.01.00 test suffix "


@pytest.mark.parametrize(
    "raw",
    [b"1", b"1\r", b"1\n0\n", b"1\nextra", b"1\r\r\n", b"\x001\n", b"\xff\n", b"\t1\n", b"1\x7f\n"],
)
def test_malformed_framing_and_ascii_rejected(raw: bytes) -> None:
    result = decode_reply(OptionStatusQuery(selector=OptionSelector.BND), raw)
    assert isinstance(result, ReplyRejected)


@pytest.mark.parametrize(
    "raw", [b"2\n", b"true\n", b"01\n", b"+1\n", b" 1\n", b"1 \n", b"\n", b"\r\n"]
)
def test_status_is_exact_boolean_byte(raw: bytes) -> None:
    assert isinstance(
        decode_reply(OptionStatusQuery(selector=OptionSelector.BND), raw), ReplyRejected
    )


@pytest.mark.parametrize(
    "raw", [b"a,b,c\n", b"a,b,c,d,e\n", b"a,b,,d\n", b"a,b, ,d\n", b",b,c,d\n"]
)
def test_identity_requires_four_nonempty_fields(raw: bytes) -> None:
    assert isinstance(decode_reply(IdentityQuery(), raw), ReplyRejected)


def test_twelve_pair_exchange_retains_original_wire() -> None:
    request = b"*IDN?\r\n" + b"".join(
        encode_query(OptionStatusQuery(selector=selector)) for selector in OptionSelector
    )
    response = b"Example,Model,SYNTHETIC,opaque-version\n" + b"0\r\n" + b"1\n" * 10
    result = decode_exchange(request, response)
    assert isinstance(result, ExchangeAccepted)
    assert result.request == request and result.response == response
    assert len(result.pairs) == 12
    assert result.pairs[0].request == b"*IDN?\r\n"
    assert b"".join(pair.request for pair in result.pairs) == request
    assert b"".join(pair.reply.raw for pair in result.pairs) == response
    assert isinstance(result.pairs[1].reply.observation, OptionStatusObservation)
    assert result.pairs[1].reply.observation.state == OptionState.DISABLED


@pytest.mark.parametrize(
    "wire",
    [
        b"*RST\n",
        b"*IDN?;*RST\n",
        b"*idn?\n",
        b" *IDN?\n",
        b":SYSTem:OPTion:INSTall token\n",
        b":SYSTem:OPTion:STATus? UNKNOWN\n",
        b":SYSTem:OPTion:STATus? BND;*RST\n",
        b":SYSTem:OPTion:STATus? audio\n",
        b"*IDN?\x00\n",
    ],
)
def test_unknown_mutating_or_noncanonical_requests_rejected(wire: bytes) -> None:
    result = decode_exchange(wire, b"a,b,c,d\n")
    assert isinstance(result, ExchangeRejected)
    assert result.issue.query_index == 0


@dataclass(frozen=True)
class MalformedExchange:
    request: bytes
    response: bytes


@pytest.mark.parametrize(
    "case",
    [
        MalformedExchange(b"", b""),
        MalformedExchange(b"*IDN?", b"a,b,c,d\n"),
        MalformedExchange(b"*IDN?\n", b"a,b,c,d"),
        MalformedExchange(b"*IDN?\n", b"a,b,c,d\n1\n"),
        MalformedExchange(b"*IDN?\n*IDN?\n", b"a,b,c,d\n"),
    ],
)
def test_exchange_framing_and_count_rejected(case: MalformedExchange) -> None:
    assert isinstance(decode_exchange(case.request, case.response), ExchangeRejected)


def test_rejection_identifies_later_query_without_payload_echo() -> None:
    request = b"*IDN?\n:SYSTem:OPTion:STATus? BND\n"
    result = decode_exchange(request, b"a,b,SYNTHETIC,d\nSECRET_INVALID_STATUS\n")
    assert isinstance(result, ExchangeRejected)
    assert result.issue.query_index == 1
    assert "SECRET" not in result.issue.message


def test_explicit_limits() -> None:
    status = OptionStatusQuery(selector=OptionSelector.BND)
    assert isinstance(decode_reply(status, b"1\r\n", CodecLimits(max_line_bytes=2)), ReplyRejected)
    assert isinstance(decode_reply(status, b"1\n", CodecLimits(max_line_bytes=2)), ReplyAccepted)
    wire = encode_query(status) * 2
    assert isinstance(
        decode_exchange(wire, b"1\n1\n", CodecLimits(max_queries=1)), ExchangeRejected
    )
    assert isinstance(
        decode_exchange(b"*IDN?\n", b"a,b,c,d\n", CodecLimits(max_exchange_bytes=2)),
        ExchangeRejected,
    )


def test_query_boundaries_reject_extra_fields_and_coercion() -> None:
    with pytest.raises(ValidationError):
        IdentityQuery.model_validate({"kind": "identity", "command": "*RST"})
    with pytest.raises(ValidationError):
        OptionStatusQuery.model_validate({"selector": "BND"})
    with pytest.raises(ValidationError):
        CodecLimits(max_queries=True)


def test_rejected_inputs_are_retained_without_repr_disclosure() -> None:
    raw = b"PRIVATE_SYNTHETIC_MALFORMED\n"
    query = IdentityQuery()
    reply = decode_reply(query, raw)
    assert isinstance(reply, ReplyRejected)
    assert reply.raw == raw and reply.query == query
    assert "PRIVATE_SYNTHETIC" not in repr(reply)
    exchange = decode_exchange(b"*IDN?\n", raw)
    assert isinstance(exchange, ExchangeRejected)
    assert exchange.request == b"*IDN?\n" and exchange.response == raw
    assert "PRIVATE_SYNTHETIC" not in repr(exchange)
