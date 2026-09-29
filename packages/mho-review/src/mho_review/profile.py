"""Bounded TOML profile edge with structural, redacted failures."""

import hashlib
import tomllib

from pydantic import ValidationError

from .models import ProfileAccepted, ProfileRejected, ReviewIssue, ReviewProfile

MAX_PROFILE_BYTES = 65536


def load_profile(raw: bytes) -> ProfileAccepted | ProfileRejected:
    if not 0 < len(raw) <= MAX_PROFILE_BYTES:
        return ProfileRejected(
            ReviewIssue("profile", "profile-limit", "profile size exceeds bound")
        )
    try:
        value: object = tomllib.loads(raw.decode("utf-8"))
        profile = ReviewProfile.model_validate(value)
        return ProfileAccepted(profile=profile, raw_sha256=hashlib.sha256(raw).hexdigest())
    except (UnicodeError, ValueError, ValidationError, RecursionError):
        return ProfileRejected(
            ReviewIssue("profile", "profile-schema", "profile is not valid under the v1 schema")
        )
