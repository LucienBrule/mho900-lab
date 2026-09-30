"""Pinned local byte streams only; no ADB executable or endpoint operations."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from mho_adb import (
    DecodeAccepted,
    DecodeLimits,
    DecodeRejected,
    MatchOpenRequest,
    StreamReadyMatched,
    StreamReadyMissing,
    StreamReadyRejected,
    decode,
    match_open,
)
from mho_evidence import Sha256
from mho_lab_cli.inputs import read_bounded_regular


@dataclass(frozen=True)
class AdbInputRejected:
    code: str
    message: str


@dataclass(frozen=True)
class AdbMatchBlocked:
    side: Literal["client", "server"]
    cause: AdbInputRejected | DecodeRejected


@dataclass(frozen=True)
class AdbMatchReport:
    client_sha256: str
    server_sha256: str
    payload_sha256: str
    outcome: StreamReadyMatched | StreamReadyMissing | StreamReadyRejected


def inspect_retained_stream(
    path: Path, digest: str
) -> DecodeAccepted | DecodeRejected | AdbInputRejected:
    try:
        expected = Sha256(digest)
    except ValidationError:
        return AdbInputRejected("digest", "expected a lowercase SHA-256 digest")
    limits = DecodeLimits()
    try:
        raw = read_bounded_regular(path, limits.max_stream_bytes)
    except (OSError, ValueError):
        return AdbInputRejected("stream-file", "cannot read bounded unchanged regular stream file")
    if hashlib.sha256(raw).hexdigest() != expected.root:
        return AdbInputRejected("source-pin", "stream does not match caller pin")
    return decode(raw, limits)


def match_retained_streams(
    client: Path, client_digest: str, server: Path, server_digest: str, payload_digest: str
) -> AdbMatchReport | AdbMatchBlocked | AdbInputRejected:
    try:
        expected = Sha256(payload_digest)
    except ValidationError:
        return AdbInputRejected("payload-digest", "expected a lowercase payload SHA-256 digest")
    first = inspect_retained_stream(client, client_digest)
    if not isinstance(first, DecodeAccepted):
        return AdbMatchBlocked("client", first)
    second = inspect_retained_stream(server, server_digest)
    if not isinstance(second, DecodeAccepted):
        return AdbMatchBlocked("server", second)
    outcome = match_open(MatchOpenRequest(first, second, expected))
    return AdbMatchReport(first.raw_sha256, second.raw_sha256, expected.root, outcome)
