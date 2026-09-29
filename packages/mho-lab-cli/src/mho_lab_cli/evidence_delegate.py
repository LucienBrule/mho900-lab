"""Typed evidence use cases, independent of command-line presentation."""

from pathlib import Path

from mho_evidence import (
    SealCreated,
    SealPublishedUncertain,
    SealRejected,
    SealRequest,
    VerificationAccepted,
    VerificationRejected,
    VerifyRequest,
    seal,
    verify,
)


def seal_evidence(
    root: Path, output: Path, *, allow_empty: bool = False
) -> SealCreated | SealRejected | SealPublishedUncertain:
    return seal(SealRequest(root=root, output=output, allow_empty=allow_empty))


def verify_evidence(root: Path, manifest: Path) -> VerificationAccepted | VerificationRejected:
    return verify(VerifyRequest(root=root, manifest=manifest))
