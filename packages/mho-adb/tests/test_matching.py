"""Independent wire construction for narrow retained OPEN/OKAY association."""

import hashlib
import warnings
from dataclasses import replace

import pytest

from mho_adb import (
    DecodeAccepted,
    DecodeLimits,
    MatchOpenRequest,
    OpenFrame,
    StreamReadyMatched,
    StreamReadyMissing,
    StreamReadyRejected,
    decode,
    match_open,
)
from mho_evidence import Sha256

SERVICE = b"shell:fixture-only\0"
DEFAULT_LIMITS = DecodeLimits()


def packet(command: bytes, local: int, remote: int, payload: bytes = b"") -> bytes:
    fields = (local, remote, len(payload), sum(payload) & 0xFFFFFFFF)
    return (
        command
        + b"".join(value.to_bytes(4, "little") for value in fields)
        + (int.from_bytes(command, "little") ^ 0xFFFFFFFF).to_bytes(4, "little")
        + payload
    )


def accepted(raw: bytes, limits: DecodeLimits = DEFAULT_LIMITS) -> DecodeAccepted:
    result = decode(raw, limits)
    assert isinstance(result, DecodeAccepted)
    return result


def request(client: bytes, server: bytes, payload: bytes = SERVICE) -> MatchOpenRequest:
    return MatchOpenRequest(
        client=accepted(client),
        server=accepted(server),
        expected_payload_sha256=Sha256(hashlib.sha256(payload).hexdigest()),
    )


def standard_request() -> MatchOpenRequest:
    return request(packet(b"OPEN", 7, 0, SERVICE), packet(b"OKAY", 41, 7))


def test_exact_open_and_consistent_repeated_ready_preserve_wire_without_action_claim() -> None:
    client = packet(b"OPEN", 6, 0, b"unrelated\0") + packet(b"OPEN", 7, 0, SERVICE)
    server = (
        packet(b"OKAY", 40, 6)
        + packet(b"OKAY", 41, 7)
        + packet(b"WRTE", 41, 7, b"private-output")
        + packet(b"OKAY", 41, 7)
        + packet(b"CLSE", 41, 7)
    )
    source = request(client, server)
    result = match_open(source)
    assert isinstance(result, StreamReadyMatched)
    assert result.client_local_id == 7 and result.server_local_id == 41
    assert result.open_frame.offset == len(packet(b"OPEN", 6, 0, b"unrelated\0"))
    assert result.open_frame.payload == SERVICE and len(result.ready_frames) == 2
    assert result.request.client.raw == client and result.request.server.raw == server
    assert result.total_order_proven is False and result.tcp_delivery_proven is False
    assert result.device_execution_proven is False and result.physical_origin_proven is False
    assert "fixture-only" not in repr(result) and "private-output" not in repr(source)


def test_digest_includes_terminal_nul_exactly() -> None:
    source = standard_request()
    result = match_open(
        replace(source, expected_payload_sha256=Sha256(hashlib.sha256(SERVICE[:-1]).hexdigest()))
    )
    assert isinstance(result, StreamReadyMissing) and result.reason == "open-not-found"


def test_no_open_is_missing_even_when_ready_identifier_exists() -> None:
    result = match_open(request(b"", packet(b"OKAY", 41, 7)))
    assert isinstance(result, StreamReadyMissing) and result.reason == "open-not-found"
    assert result.selected_open is None


def test_close_without_ready_is_missing_not_success_or_action_failure() -> None:
    result = match_open(request(packet(b"OPEN", 7, 0, SERVICE), packet(b"CLSE", 0, 7)))
    assert isinstance(result, StreamReadyMissing) and result.reason == "ready-not-found"
    assert result.selected_open is not None and result.selected_open.local_id == 7


def test_reversed_ready_identifier_pair_does_not_match() -> None:
    result = match_open(request(packet(b"OPEN", 7, 0, SERVICE), packet(b"OKAY", 7, 41)))
    assert isinstance(result, StreamReadyMissing) and result.reason == "ready-not-found"


@pytest.mark.parametrize("second_id", [7, 8])
def test_duplicate_expected_open_rejected_even_with_different_identifiers(second_id: int) -> None:
    result = match_open(
        request(
            packet(b"OPEN", 7, 0, SERVICE) + packet(b"OPEN", second_id, 0, SERVICE),
            packet(b"OKAY", 41, 7),
        )
    )
    assert isinstance(result, StreamReadyRejected) and result.issue.code == "ambiguous-open"


@pytest.mark.parametrize("other_first", [False, True])
def test_selected_client_id_reuse_rejected_even_with_close(other_first: bool) -> None:
    selected = packet(b"OPEN", 7, 0, SERVICE)
    other = packet(b"OPEN", 7, 0, b"other-service\0")
    client = (
        other + packet(b"CLSE", 7, 40) + selected
        if other_first
        else selected + packet(b"CLSE", 7, 41) + other
    )
    result = match_open(request(client, packet(b"OKAY", 41, 7)))
    assert isinstance(result, StreamReadyRejected) and result.issue.code == "client-id-reused"


def test_changed_responder_id_rejects() -> None:
    result = match_open(
        request(
            packet(b"OPEN", 7, 0, SERVICE),
            packet(b"OKAY", 41, 7) + packet(b"OKAY", 42, 7),
        )
    )
    assert isinstance(result, StreamReadyRejected) and result.issue.code == "responder-id-changed"


def test_other_stream_responder_changes_do_not_change_selected_pair() -> None:
    result = match_open(
        request(
            packet(b"OPEN", 7, 0, SERVICE),
            packet(b"OKAY", 41, 7) + packet(b"OKAY", 50, 8) + packet(b"OKAY", 51, 8),
        )
    )
    assert isinstance(result, StreamReadyMatched) and len(result.ready_frames) == 1


@pytest.mark.parametrize("field", ["raw", "digest", "count", "wire", "payload", "offset", "bool"])
def test_forged_decoded_records_reject(field: str) -> None:
    source = standard_request()
    client = source.client
    first = client.frames[0]
    assert isinstance(first, OpenFrame)
    if field == "raw":
        client = replace(client, raw=client.raw + b"extra")
    elif field == "digest":
        client = replace(client, raw_sha256="0" * 64)
    elif field == "count":
        client = replace(client, raw_bytes=client.raw_bytes + 1)
    elif field == "wire":
        client = replace(client, frames=(replace(first, wire=first.wire[:-1]),))
    elif field == "payload":
        client = replace(client, frames=(replace(first, payload=b"different\0"),))
    elif field == "offset":
        client = replace(client, frames=(replace(first, offset=1),))
    else:
        client = replace(client, frames=(replace(first, arg1=False),))
    result = match_open(replace(source, client=client))
    assert isinstance(result, StreamReadyRejected) and result.issue.code == "decoded-stream"


def test_server_forgery_is_rejected_too() -> None:
    source = standard_request()
    result = match_open(replace(source, server=replace(source.server, raw_bytes=0)))
    assert isinstance(result, StreamReadyRejected) and result.issue.code == "decoded-stream"


def test_unchecked_invalid_digest_and_limits_reject() -> None:
    source = standard_request()
    bad_hash = match_open(
        replace(source, expected_payload_sha256=Sha256.model_construct(root="private invalid"))
    )
    assert isinstance(bad_hash, StreamReadyRejected)
    assert bad_hash.issue.code == "expected-payload-digest"
    assert "private invalid" not in repr(bad_hash)
    bad_limits = match_open(
        replace(
            source, client=replace(source.client, limits=DecodeLimits.model_construct(max_frames=0))
        )
    )
    assert isinstance(bad_limits, StreamReadyRejected)
    assert bad_limits.issue.code == "decoded-stream"


def test_custom_valid_decoder_limits_are_preserved_during_revalidation() -> None:
    source = standard_request()
    client = accepted(source.client.raw, DecodeLimits(max_frames=1, max_payload_bytes=len(SERVICE)))
    result = match_open(replace(source, client=client))
    assert isinstance(result, StreamReadyMatched)
    assert result.request.client.limits.max_frames == 1


@pytest.mark.parametrize("value", [0, True])
def test_forged_proof_flags_reject_including_integer_zero(value: int | bool) -> None:
    source = standard_request()
    object.__setattr__(source.client, "physical_origin_proven", value)
    result = match_open(source)
    assert isinstance(result, StreamReadyRejected) and result.issue.code == "decoded-stream"


def test_server_open_cannot_supply_missing_client_open() -> None:
    result = match_open(request(b"", packet(b"OPEN", 7, 0, SERVICE) + packet(b"OKAY", 41, 7)))
    assert isinstance(result, StreamReadyMissing) and result.reason == "open-not-found"


def test_malformed_limit_fields_do_not_emit_private_serializer_warning() -> None:
    source = standard_request()
    malformed = DecodeLimits()
    object.__setattr__(malformed, "max_frames", "PRIVATE_INVALID_VALUE")
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        result = match_open(replace(source, client=replace(source.client, limits=malformed)))
    assert isinstance(result, StreamReadyRejected) and result.issue.code == "decoded-stream"
    assert recorded == [] and "PRIVATE_INVALID_VALUE" not in repr(result)
