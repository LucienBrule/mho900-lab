"""Typed application coordination for a caller-pinned offline review."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from mho_evidence import Sha256
from mho_lab_cli.inputs import read_bounded_regular
from mho_review import (
    ProfileRejected,
    ReviewAccepted,
    ReviewIssue,
    ReviewRejected,
    ReviewRequest,
    load_profile,
    review,
)


@dataclass(frozen=True)
class ReviewReport:
    profile_sha256: str
    outcome: ReviewAccepted | ReviewRejected


def inspect_review(
    root: Path, manifest: Path, expected_digest: str, profile: Path
) -> ReviewReport | ReviewRejected:
    try:
        expected = Sha256(expected_digest)
    except ValidationError:
        return ReviewRejected(ReviewIssue("input", "digest", "expected a lowercase SHA-256 digest"))
    try:
        encoded = read_bounded_regular(profile, 65536)
    except (OSError, ValueError):
        return ReviewRejected(
            ReviewIssue("input", "profile-file", "cannot read bounded regular profile")
        )
    parsed = load_profile(encoded)
    if isinstance(parsed, ProfileRejected):
        return ReviewRejected(parsed.issue)
    outcome = review(ReviewRequest(root, manifest, expected, parsed.profile))
    return ReviewReport(parsed.raw_sha256, outcome)
