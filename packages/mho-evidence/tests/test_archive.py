"""Synthetic tar controls, never extraction or private archive contents."""

import hashlib
import io
import os
import tarfile
from pathlib import Path
from typing import Literal

import pytest

from mho_evidence import (
    ArchiveAccepted,
    ArchiveLimits,
    ArchiveRejected,
    ArchiveRequest,
    Sha256,
    inspect_archive,
)


def regular(
    name: str, data: bytes = b"abc", *, format: Literal[0, 1, 2] = tarfile.USTAR_FORMAT
) -> bytes:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    return info.tobuf(format=format) + data + bytes((-len(data)) % 512)


def directory(name: str, *, format: Literal[0, 1, 2] = tarfile.USTAR_FORMAT) -> bytes:
    info = tarfile.TarInfo(name)
    info.type = tarfile.DIRTYPE
    return info.tobuf(format=format)


def inspect(
    tmp_path: Path, raw: bytes, limits: ArchiveLimits | None = None
) -> ArchiveAccepted | ArchiveRejected:
    source = tmp_path / "archive.tar"
    source.write_bytes(raw)
    return inspect_archive(
        ArchiveRequest(source, Sha256(hashlib.sha256(raw).hexdigest()), limits or ArchiveLimits())
    )


def changed_header(raw: bytes, start: int, replacement: bytes) -> bytes:
    value = bytearray(raw)
    value[start : start + len(replacement)] = replacement
    value[148:156] = b" " * 8
    checksum = sum(value[:512])
    value[148:156] = f"{checksum:06o}\0 ".encode()
    return bytes(value)


@pytest.mark.parametrize("format", [tarfile.USTAR_FORMAT, tarfile.GNU_FORMAT])
def test_regular_and_directory_inventory_is_sorted_and_pinned(
    tmp_path: Path, format: Literal[0, 1, 2]
) -> None:
    raw = (
        directory("data/", format=format)
        + regular("data/z", b"z", format=format)
        + regular("data/a", b"", format=format)
        + bytes(1024)
    )
    result = inspect(tmp_path, raw)
    assert isinstance(result, ArchiveAccepted)
    assert result.source_sha256 == hashlib.sha256(raw).hexdigest()
    assert result.source_bytes == len(raw) and result.member_count == 3
    assert [item.path.root for item in result.artifacts] == ["data/a", "data/z"]
    assert [item.root for item in result.directories] == ["data"]
    assert result.artifacts[0].sha256.root == hashlib.sha256(b"").hexdigest()
    assert result.artifacts[1].sha256.root == hashlib.sha256(b"z").hexdigest()
    assert result.physical_origin_proven is False
    assert result.atomic_snapshot_proven is False
    assert not (tmp_path / "data").exists()


def test_ustar_prefix_field_is_used_exactly(tmp_path: Path) -> None:
    name = "a" * 90 + "/" + "b" * 30
    result = inspect(tmp_path, regular(name) + bytes(1024))
    assert isinstance(result, ArchiveAccepted)
    assert result.artifacts[0].path.root == name


def test_empty_archive_and_extra_zero_records_are_supported(tmp_path: Path) -> None:
    result = inspect(tmp_path, bytes(10240))
    assert isinstance(result, ArchiveAccepted)
    assert result.member_count == 0 and result.artifacts == () and result.directories == ()


@pytest.mark.parametrize(
    "name",
    ["/absolute", "../parent", "./file", "a//b", "a/../b", "a\\b", "a:b", "a/", "control\nname"],
)
def test_unsafe_or_noncanonical_file_names_rejected(tmp_path: Path, name: str) -> None:
    assert isinstance(inspect(tmp_path, regular(name) + bytes(1024)), ArchiveRejected)


@pytest.mark.parametrize("kind", [b"1", b"2", b"3", b"4", b"6", b"7", b"x", b"g", b"L", b"K", b"S"])
def test_unsupported_member_types_rejected(tmp_path: Path, kind: bytes) -> None:
    raw = changed_header(regular("file"), 156, kind) + bytes(1024)
    assert isinstance(inspect(tmp_path, raw), ArchiveRejected)


@pytest.mark.parametrize(
    "case",
    [
        "checksum",
        "one-zero",
        "missing-zero",
        "truncated-block",
        "truncated-payload",
        "trailing-data",
        "payload-padding",
        "directory-data",
        "base256",
        "gnu-extension",
        "linkname",
        "header-padding",
        "duplicate",
        "file-parent",
        "late-file-parent",
        "file-directory",
    ],
)
def test_malformed_archives_rejected(tmp_path: Path, case: str) -> None:
    raw = regular("file") + bytes(1024)
    if case == "checksum":
        raw = b"X" + raw[1:]
    elif case == "one-zero":
        raw = raw[:-512]
    elif case == "missing-zero":
        raw = raw[:-1024]
    elif case == "truncated-block":
        raw = raw[:-1]
    elif case == "truncated-payload":
        raw = changed_header(raw, 124, b"00000010000\0")
    elif case == "trailing-data":
        raw += bytes(511) + b"X"
    elif case == "payload-padding":
        raw = raw[:515] + b"X" + raw[516:]
    elif case == "directory-data":
        raw = changed_header(raw, 156, b"5")
    elif case == "base256":
        raw = changed_header(raw, 124, b"\x80" + bytes(11))
    elif case == "gnu-extension":
        raw = changed_header(regular("file", format=tarfile.GNU_FORMAT) + bytes(1024), 345, b"1")
    elif case == "linkname":
        raw = changed_header(raw, 157, b"target")
    elif case == "header-padding":
        raw = changed_header(raw, 500, b"x")
    elif case == "duplicate":
        raw = regular("file") * 2 + bytes(1024)
    elif case == "file-parent":
        raw = regular("file") + regular("file/child") + bytes(1024)
    elif case == "late-file-parent":
        raw = regular("file/child") + regular("file") + bytes(1024)
    elif case == "file-directory":
        raw = regular("file") + directory("file/") + bytes(1024)
    assert isinstance(inspect(tmp_path, raw), ArchiveRejected)


@pytest.mark.parametrize("limit", ["source", "member", "count", "total", "depth"])
def test_limits_are_enforced(tmp_path: Path, limit: str) -> None:
    raw = regular("a/one", b"ab") + regular("a/two", b"cd") + bytes(1024)
    bounds = ArchiveLimits()
    if limit == "source":
        bounds = ArchiveLimits(max_source_bytes=1024)
    elif limit == "member":
        bounds = ArchiveLimits(max_member_bytes=1)
    elif limit == "count":
        bounds = ArchiveLimits(max_members=1)
    elif limit == "total":
        bounds = ArchiveLimits(max_total_payload_bytes=3)
    elif limit == "depth":
        bounds = ArchiveLimits(max_path_depth=1)
    assert isinstance(inspect(tmp_path, raw, bounds), ArchiveRejected)


def test_source_pin_is_required_and_errors_redacted(tmp_path: Path) -> None:
    source = tmp_path / "PRIVATE_NAME"
    source.write_bytes(regular("PRIVATE_MEMBER") + bytes(1024))
    result = inspect_archive(ArchiveRequest(source, Sha256("0" * 64)))
    assert isinstance(result, ArchiveRejected)
    assert result.issue.code == "archive-source-pin" and "PRIVATE" not in repr(result)


@pytest.mark.parametrize("kind", ["symlink", "fifo", "compressed"])
def test_unsupported_sources_rejected_without_extraction(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "source"
    raw = bytes(1024)
    if kind == "symlink":
        real = tmp_path / "real"
        real.write_bytes(raw)
        source.symlink_to(real)
    elif kind == "fifo":
        os.mkfifo(source)
    else:
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz"):
            pass
        raw = buffer.getvalue()
        source.write_bytes(raw)
    result = inspect_archive(ArchiveRequest(source, Sha256(hashlib.sha256(raw).hexdigest())))
    assert isinstance(result, ArchiveRejected)
