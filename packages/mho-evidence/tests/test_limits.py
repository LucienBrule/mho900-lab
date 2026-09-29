"""Optional verification limits bound malformed or unexpectedly growing inventories."""

import os
from pathlib import Path

import pytest

from mho_evidence import (
    SealCreated,
    SealRequest,
    VerificationAccepted,
    VerificationLimits,
    VerificationRejected,
    VerifyRequest,
    seal,
    verify,
)


def prepared(tmp_path: Path) -> SealCreated:
    root = tmp_path / "root"
    root.mkdir()
    (root / "first").write_bytes(b"abcd")
    outcome = seal(SealRequest(root=root, output=tmp_path / "manifest.toml"))
    assert isinstance(outcome, SealCreated)
    return outcome


@pytest.mark.parametrize(
    "limits,code",
    [
        (VerificationLimits(max_file_bytes=3), "inventory-byte-limit"),
        (VerificationLimits(max_total_bytes=3), "inventory-byte-limit"),
        (VerificationLimits(max_manifest_bytes=8), "manifest-limit"),
    ],
)
def test_limits_reject_oversized_evidence(
    tmp_path: Path, limits: VerificationLimits, code: str
) -> None:
    manifest = prepared(tmp_path)
    result = verify(VerifyRequest(tmp_path / "root", manifest.output, limits))
    assert isinstance(result, VerificationRejected)
    assert result.issue.code == code


def test_limit_boundary_accepts_exact_bytes(tmp_path: Path) -> None:
    manifest = prepared(tmp_path)
    result = verify(
        VerifyRequest(
            tmp_path / "root",
            manifest.output,
            VerificationLimits(
                max_entries=1,
                max_file_bytes=4,
                max_total_bytes=4,
                max_depth=0,
                max_manifest_bytes=manifest.output.stat().st_size,
            ),
        )
    )
    assert isinstance(result, VerificationAccepted)


@pytest.mark.parametrize("depth_limit", [True, False])
def test_directories_count_toward_traversal_limits(tmp_path: Path, depth_limit: bool) -> None:
    root = tmp_path / "root"
    (root / "one" / "two").mkdir(parents=True)
    (root / "one" / "two" / "file").write_bytes(b"a")
    manifest = tmp_path / "manifest.toml"
    assert isinstance(seal(SealRequest(root, manifest)), SealCreated)
    limits = VerificationLimits(max_depth=1) if depth_limit else VerificationLimits(max_entries=2)
    result = verify(VerifyRequest(root, manifest, limits))
    assert isinstance(result, VerificationRejected)
    assert result.issue.code == (
        "inventory-depth-limit" if depth_limit else "inventory-entry-limit"
    )


@pytest.mark.parametrize("manifest_growth", [False, True])
def test_growth_during_read_cannot_escape_byte_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manifest_growth: bool
) -> None:
    manifest = prepared(tmp_path)
    target = manifest.output if manifest_growth else tmp_path / "root" / "first"
    inode = target.stat().st_ino
    original_size = target.stat().st_size
    original_read = os.read
    changed = False

    def growing_read(descriptor: int, size: int) -> bytes:
        nonlocal changed
        if not changed and os.fstat(descriptor).st_ino == inode:
            changed = True
            with target.open("ab") as stream:
                stream.write(b"unexpected-growth")
        return original_read(descriptor, size)

    monkeypatch.setattr(os, "read", growing_read)
    limits = (
        VerificationLimits(max_manifest_bytes=original_size)
        if manifest_growth
        else VerificationLimits(max_file_bytes=4)
    )
    result = verify(VerifyRequest(tmp_path / "root", manifest.output, limits))
    assert changed
    assert isinstance(result, VerificationRejected)
    assert result.issue.code == ("manifest-limit" if manifest_growth else "inventory-byte-limit")


def test_added_foreign_file_is_bounded_before_full_hash(tmp_path: Path) -> None:
    manifest = prepared(tmp_path)
    with (tmp_path / "root" / "large").open("wb") as stream:
        stream.truncate(1024**3)
    result = verify(
        VerifyRequest(tmp_path / "root", manifest.output, VerificationLimits(max_file_bytes=16))
    )
    assert isinstance(result, VerificationRejected)
    assert result.issue.code == "inventory-byte-limit"
