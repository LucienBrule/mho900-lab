"""Bounded synthetic TOML edges; no external evidence or device operations."""

from ipaddress import IPv4Address
from pathlib import Path

import pytest
from pydantic import ValidationError

from mho_evidence import Sha256
from mho_review import (
    ProfileAccepted,
    ProfileRejected,
    ReviewProfile,
    ReviewRejected,
    ReviewRequest,
    load_profile,
    review,
)
from mho_transport import Endpoint

PROFILE = b"""schema_version = "mho-review.profile/1"
capture = "capture.pcap"
statistics = "capture.stderr"
[client]
address = "192.0.2.1"
port = 41000
[server]
address = "192.0.2.2"
port = 5555
[[transcripts]]
request = "raw/request.bin"
reply = "raw/reply.bin"
"""


def test_profile_is_typed_and_deterministic() -> None:
    result = load_profile(PROFILE)
    assert isinstance(result, ProfileAccepted)
    assert result.profile.client.address == IPv4Address("192.0.2.1")
    assert result.profile.transcripts[0].request.root == "raw/request.bin"
    assert result == load_profile(PROFILE)


@pytest.mark.parametrize(
    "mutation",
    [
        "schema",
        "absolute",
        "parent",
        "duplicate",
        "unknown",
        "port",
        "host",
        "empty",
        "oversize",
        "bad-utf8",
    ],
)
def test_profile_rejects_invalid_or_ambiguous_input(mutation: str) -> None:
    raw = PROFILE
    if mutation == "schema":
        raw = raw.replace(b"profile/1", b"profile/2")
    elif mutation == "absolute":
        raw = raw.replace(b"raw/request.bin", b"/private/secret")
    elif mutation == "parent":
        raw = raw.replace(b"raw/request.bin", b"../private/secret")
    elif mutation == "duplicate":
        raw = raw.replace(b"raw/request.bin", b"capture.pcap")
    elif mutation == "unknown":
        raw += b'unknown = "PRIVATE_SECRET"\n'
    elif mutation == "port":
        raw = raw.replace(b"41000", b'"41000"')
    elif mutation == "host":
        raw = raw.replace(b"192.0.2.1", b"private.example")
    elif mutation == "empty":
        raw = b""
    elif mutation == "oversize":
        raw = b"x" * 65537
    elif mutation == "bad-utf8":
        raw = b"\xff"
    result = load_profile(raw)
    assert isinstance(result, ProfileRejected)
    assert "PRIVATE_SECRET" not in repr(result)


def test_manifest_pin_rejects_before_any_inventory(tmp_path: Path) -> None:
    result = load_profile(PROFILE)
    assert isinstance(result, ProfileAccepted)
    manifest = tmp_path / "manifest.toml"
    manifest.write_bytes(b"PRIVATE_INVALID_MANIFEST")
    rejected = review(
        ReviewRequest(tmp_path / "absent", manifest, Sha256("0" * 64), result.profile)
    )
    assert isinstance(rejected, ReviewRejected)
    assert rejected.issue.stage == "manifest" and rejected.issue.code == "manifest-pin"
    assert "PRIVATE_INVALID_MANIFEST" not in repr(rejected)


def test_deeply_nested_malformed_profile_returns_structural_rejection() -> None:
    raw = b"value = " + b"{ value = " * 2000 + b"0" + b"}" * 2000
    result = load_profile(raw)
    assert isinstance(result, ProfileRejected)
    assert result.issue.stage == "profile"


@pytest.mark.parametrize("base_client", [True, False])
def test_mixed_endpoint_construction_rejects_same_address_and_port(base_client: bool) -> None:
    endpoint = Endpoint(address=IPv4Address("192.0.2.1"), port=5555)
    mapped: object = {"address": "192.0.2.1", "port": 5555}
    with pytest.raises(ValidationError, match="client and server must differ"):
        ReviewProfile.model_validate(
            {
                "schema_version": "mho-review.profile/1",
                "capture": "capture.pcap",
                "statistics": "capture.stderr",
                "client": endpoint if base_client else mapped,
                "server": mapped if base_client else endpoint,
                "transcripts": [{"request": "request.bin", "reply": "reply.bin"}],
            }
        )
