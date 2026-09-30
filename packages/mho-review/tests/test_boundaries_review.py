"""Review validates its own profile and resource contract before reading files."""

from pathlib import Path

import pytest

import mho_review.operations as operations
from mho_evidence import ArtifactPath, Sha256
from mho_review import (
    ProfileAccepted,
    ReviewLimits,
    ReviewProfile,
    ReviewRejected,
    ReviewRequest,
    load_profile,
    review,
)

FIXTURE = Path(__file__).resolve().parents[3] / "examples" / "sealed-review"
PIN = Sha256("b049d958172b0b013aa9934c66e029d2a33559e13aed9d3e362719e8ce9672f6")


def no_read(path: Path, maximum: int) -> bytes:
    raise AssertionError("invalid review contract reached filesystem")


def profile() -> ReviewProfile:
    parsed = load_profile((FIXTURE / "profile.toml").read_bytes())
    assert isinstance(parsed, ProfileAccepted)
    return parsed.profile


@pytest.mark.parametrize("value", [100001, True, float("inf"), None, "PRIVATE-LIMIT"])
def test_own_review_bound_is_not_replaced_by_looser_downstream_limit(
    monkeypatch: pytest.MonkeyPatch, value: object
) -> None:
    monkeypatch.setattr(operations, "read_bounded", no_read)
    limits = ReviewLimits().model_copy(update={"max_inventory_entries": value})
    result = review(
        ReviewRequest(FIXTURE / "bundle", FIXTURE / "manifest.toml", PIN, profile(), limits)
    )
    assert isinstance(result, ReviewRejected) and result.issue.stage == "contract"
    assert "PRIVATE" not in repr(result)


def test_unchecked_profile_schema_rejected_before_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(operations, "read_bounded", no_read)
    invalid = profile().model_copy(update={"schema_version": "PRIVATE-SCHEMA"})
    result = review(ReviewRequest(FIXTURE / "bundle", FIXTURE / "manifest.toml", PIN, invalid))
    assert isinstance(result, ReviewRejected) and result.issue.stage == "contract"
    assert "PRIVATE" not in repr(result)


def test_nested_unchecked_role_rejected_before_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(operations, "read_bounded", no_read)
    role = ArtifactPath("valid").model_copy(update={"root": "../PRIVATE"})
    invalid = profile().model_copy(update={"capture": role})
    result = review(ReviewRequest(FIXTURE / "bundle", FIXTURE / "manifest.toml", PIN, invalid))
    assert isinstance(result, ReviewRejected) and result.issue.stage == "contract"
    assert "PRIVATE" not in repr(result)


def test_duplicate_unchecked_roles_rejected_before_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(operations, "read_bounded", no_read)
    valid = profile()
    invalid = valid.model_copy(update={"statistics": valid.capture})
    result = review(ReviewRequest(FIXTURE / "bundle", FIXTURE / "manifest.toml", PIN, invalid))
    assert isinstance(result, ReviewRejected) and result.issue.stage == "contract"
