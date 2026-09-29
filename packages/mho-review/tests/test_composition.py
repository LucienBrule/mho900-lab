"""Independent adversarial compositions of locally generated sealed evidence."""

from pathlib import Path

import pytest
from review_composition_fixtures import (
    CLIENT_ADDRESS,
    CLIENT_PORT,
    IDENTITY_REQUEST,
    IDENTITY_RESPONSE,
    SERVER_ADDRESS,
    SERVER_PORT,
    STATUS_REQUEST,
    STATUS_RESPONSE,
    Bundle,
    capture_bytes,
    seal_inputs,
    terminal_statistics,
    write_inputs,
)

import mho_review.operations as operations
from mho_evidence import Sha256
from mho_review import (
    ProfileAccepted,
    ProfileRejected,
    ReviewAccepted,
    ReviewRejected,
    ReviewRequest,
    load_profile,
    review,
)
from mho_scpi import CodecLimits, ExchangeAccepted, ExchangeRejected
from mho_transport import (
    CaptureInspectionAccepted,
    CaptureInspectionRejected,
    CaptureInspectionRequest,
)


def profile_text() -> str:
    return f'''schema_version = "mho-review.profile/1"
capture = "capture.pcap"
statistics = "stderr.txt"
[client]
address = "{CLIENT_ADDRESS}"
port = {CLIENT_PORT}
[server]
address = "{SERVER_ADDRESS}"
port = {SERVER_PORT}
[[transcripts]]
request = "q-0.bin"
reply = "r-0.bin"
[[transcripts]]
request = "q-1.bin"
reply = "r-1.bin"
'''


def review_bundle(
    bundle: Bundle, *, profile: str | None = None, pin: str | None = None
) -> ReviewAccepted | ReviewRejected:
    parsed = load_profile((profile or profile_text()).encode())
    assert isinstance(parsed, ProfileAccepted)
    return review(
        ReviewRequest(
            root=bundle.root,
            manifest=bundle.manifest,
            expected_manifest_sha256=Sha256(pin or bundle.pin),
            profile=parsed.profile,
        )
    )


def test_consistent_sealed_bundle_reconstructs_exact_ordered_observations(tmp_path: Path) -> None:
    bundle = seal_inputs(write_inputs(tmp_path))
    result = review_bundle(bundle)
    assert isinstance(result, ReviewAccepted)
    assert result.manifest_sha256 == bundle.pin
    assert result.transcript.request == IDENTITY_REQUEST + STATUS_REQUEST
    assert result.transcript.reply == IDENTITY_RESPONSE + STATUS_RESPONSE
    assert [pair.reply.raw for pair in result.exchange.pairs] == [
        IDENTITY_RESPONSE,
        STATUS_RESPONSE,
    ]
    assert result.capture_assessment.capture.capture_frames == 6
    assert result.capture_assessment.process_exit_proven is False
    assert result.capture_assessment.wire_completeness_proven is False
    assert result.physical_origin_proven is False
    assert result.atomic_snapshot_proven is False
    assert result.peer_delivery_proven is False
    assert result.device_execution_proven is False


def test_wrong_manifest_pin_rejects_before_consumer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = seal_inputs(write_inputs(tmp_path))
    reached: list[bool] = []

    def unexpected_consumer(
        request: CaptureInspectionRequest,
    ) -> CaptureInspectionAccepted | CaptureInspectionRejected:
        reached.append(True)
        raise AssertionError("wrong pin must not reach capture interpretation")

    monkeypatch.setattr(operations, "inspect_capture", unexpected_consumer)
    result = review_bundle(bundle, pin="0" * 64)
    assert isinstance(result, ReviewRejected)
    assert result.issue.stage == "manifest"
    assert not reached


@pytest.mark.parametrize(
    "substitution",
    [
        'capture = "../foreign.pcap"',
        'capture = "/foreign.pcap"',
        'capture = "stderr.txt"',
        'capture = "q-0.bin"',
    ],
)
def test_outside_or_aliased_roles_reject_at_profile_boundary(substitution: str) -> None:
    parsed = load_profile(profile_text().replace('capture = "capture.pcap"', substitution).encode())
    assert isinstance(parsed, ProfileRejected)


def test_duplicate_transcript_role_rejects() -> None:
    raw = profile_text().replace('reply = "r-1.bin"', 'reply = "r-0.bin"')
    assert isinstance(load_profile(raw.encode()), ProfileRejected)


def test_symlink_role_cannot_substitute_foreign_bytes_after_seal(tmp_path: Path) -> None:
    bundle = seal_inputs(write_inputs(tmp_path))
    original = bundle.root / "r-0.bin"
    original.unlink()
    foreign = tmp_path / "foreign.bin"
    foreign.write_bytes(IDENTITY_RESPONSE)
    original.symlink_to(foreign)
    result = review_bundle(bundle)
    assert isinstance(result, ReviewRejected)
    assert result.issue.stage == "inventory-before"
    assert foreign.read_bytes() == IDENTITY_RESPONSE


def test_valid_foreign_statistics_copied_after_seal_are_not_silently_used(tmp_path: Path) -> None:
    bundle = seal_inputs(write_inputs(tmp_path))
    (bundle.root / "stderr.txt").write_bytes(
        b"tcpdump: different recorder startup\n" + terminal_statistics()
    )
    result = review_bundle(bundle)
    assert isinstance(result, ReviewRejected)
    assert result.issue.stage == "inventory-before"


def test_preserving_sealed_membership_does_not_prove_common_origin(tmp_path: Path) -> None:
    root = write_inputs(tmp_path)
    # This intentionally mixed source is consistent, so no byte-only checker can
    # authenticate its physical origin. Do not invent an origin check from text.
    (root / "stderr.txt").write_bytes(
        b"tcpdump: different recorder startup\n" + terminal_statistics()
    )
    result = review_bundle(seal_inputs(root))
    assert isinstance(result, ReviewAccepted)
    assert result.capture_assessment.process_exit_proven is False
    assert result.capture_assessment.wire_completeness_proven is False


@pytest.mark.parametrize("member", ["q-1.bin", "r-1.bin"])
def test_valid_sealed_raw_log_must_equal_selected_tcp_bytes(tmp_path: Path, member: str) -> None:
    root = write_inputs(tmp_path)
    replacement = b":SYSTem:OPTion:STATus? BND\n" if member.startswith("q") else b"0\n"
    (root / member).write_bytes(replacement)
    result = review_bundle(seal_inputs(root))
    assert isinstance(result, ReviewRejected)
    assert result.issue.stage == "transcripts"


def test_ordered_transcript_roles_are_not_sorted_or_guessed(tmp_path: Path) -> None:
    bundle = seal_inputs(write_inputs(tmp_path))
    swapped = (
        profile_text()
        .replace("q-0.bin", "temporary")
        .replace("q-1.bin", "q-0.bin")
        .replace("temporary", "q-1.bin")
    )
    swapped = (
        swapped.replace("r-0.bin", "temporary")
        .replace("r-1.bin", "r-0.bin")
        .replace("temporary", "r-1.bin")
    )
    result = review_bundle(bundle, profile=swapped)
    assert isinstance(result, ReviewRejected)
    assert result.issue.stage == "transcripts"


def test_selected_tuple_is_explicit_not_first_available_connection(tmp_path: Path) -> None:
    bundle = seal_inputs(write_inputs(tmp_path))
    result = review_bundle(
        bundle, profile=profile_text().replace(f"port = {CLIENT_PORT}", "port = 43001")
    )
    assert isinstance(result, ReviewRejected)
    assert result.issue.stage == "tcp"


def test_capture_changed_after_inventory_check_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = seal_inputs(write_inputs(tmp_path))
    original = operations.inspect_capture
    reached: list[bool] = []

    def substitute_before_interpretation(
        request: CaptureInspectionRequest,
    ) -> CaptureInspectionAccepted | CaptureInspectionRejected:
        reached.append(True)
        # Keep an internally valid six-frame capture, with different reply bytes.
        request.capture.write_bytes(
            capture_bytes(
                IDENTITY_REQUEST + STATUS_REQUEST,
                IDENTITY_RESPONSE + b"0\n",
            )
        )
        return original(request)

    monkeypatch.setattr(operations, "inspect_capture", substitute_before_interpretation)
    result = review_bundle(bundle)
    assert reached == [True]
    assert isinstance(result, ReviewRejected)
    assert result.issue.stage == "capture"


@pytest.mark.parametrize("count,drops", [(7, 0), (6, 1)])
def test_sealed_counts_must_agree_and_report_no_observed_drops(
    tmp_path: Path, count: int, drops: int
) -> None:
    root = write_inputs(tmp_path)
    (root / "stderr.txt").write_bytes(terminal_statistics(count, drops))
    result = review_bundle(seal_inputs(root))
    assert isinstance(result, ReviewRejected)
    assert result.issue.stage == "assessment"


def test_missing_statistics_are_not_interpreted_as_zero(tmp_path: Path) -> None:
    root = write_inputs(tmp_path)
    (root / "stderr.txt").write_bytes(b"tcpdump: listening on synthetic interface\n")
    assert isinstance(review_bundle(seal_inputs(root)), ReviewRejected)


@pytest.mark.parametrize("variant", ["malformed-reply", "mutating-request"])
def test_wire_and_logs_can_agree_but_scpi_still_rejects(tmp_path: Path, variant: str) -> None:
    root = write_inputs(tmp_path)
    query = STATUS_REQUEST
    reply = STATUS_RESPONSE
    if variant == "malformed-reply":
        reply = b"2\n"
    else:
        query = b"*RST\n"
    (root / "q-1.bin").write_bytes(query)
    (root / "r-1.bin").write_bytes(reply)
    (root / "capture.pcap").write_bytes(
        capture_bytes(
            IDENTITY_REQUEST + query,
            IDENTITY_RESPONSE + reply,
        )
    )
    result = review_bundle(seal_inputs(root))
    assert isinstance(result, ReviewRejected)
    assert result.issue.stage == "scpi"
    assert "SYNTHETIC" not in repr(result.issue)


def test_unselected_role_outside_exact_inventory_rejects(tmp_path: Path) -> None:
    root = write_inputs(tmp_path)
    (root / "unrelated.bin").write_bytes(b"sealed but unselected")
    bundle = seal_inputs(root)
    (root / "unrelated.bin").write_bytes(b"changed after seal")
    assert isinstance(review_bundle(bundle), ReviewRejected)


def test_final_verification_detects_unselected_member_change_after_decode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = write_inputs(tmp_path)
    unrelated = root / "unselected.bin"
    unrelated.write_bytes(b"original")
    bundle = seal_inputs(root)
    original = operations.decode_exchange
    reached: list[bool] = []

    def mutate_after_decode(
        request: bytes, response: bytes, limits: CodecLimits | None = None
    ) -> ExchangeAccepted | ExchangeRejected:
        result = original(request, response, limits or CodecLimits())
        assert isinstance(result, ExchangeAccepted)
        reached.append(True)
        unrelated.write_bytes(b"changed after successful decode")
        return result

    monkeypatch.setattr(operations, "decode_exchange", mutate_after_decode)
    result = review_bundle(bundle)
    assert reached == [True]
    assert isinstance(result, ReviewRejected)
    assert result.issue.stage == "inventory-after"
