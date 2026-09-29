"""Filesystem behavior and immutable schema checks; no device or network I/O."""

import os
import stat
from pathlib import Path

import pytest
from pydantic import ValidationError

from mho_evidence import (
    ArtifactPath,
    SealCreated,
    SealPublishedUncertain,
    SealRejected,
    SealRequest,
    VerificationAccepted,
    VerificationRejected,
    VerifyRequest,
    load_manifest,
    seal,
    verify,
)


def create_root(tmp_path: Path) -> Path:
    root = tmp_path.resolve() / "evidence"
    root.mkdir()
    (root / "nested").mkdir()
    (root / "nested" / "sample.bin").write_bytes(b"sample\x00bytes")
    (root / "empty.bin").write_bytes(b"")
    return root


def test_roundtrip_and_deterministic_inventory(tmp_path: Path) -> None:
    root = create_root(tmp_path)
    first = tmp_path.resolve() / "first.toml"
    second = tmp_path.resolve() / "second.toml"
    created = seal(SealRequest(root=root, output=first))
    assert isinstance(created, SealCreated)
    assert created.artifact_count == 2 and created.total_bytes == 12
    assert isinstance(seal(SealRequest(root=root, output=second)), SealCreated)
    assert first.read_bytes() == second.read_bytes()
    accepted = verify(VerifyRequest(root=root, manifest=first))
    assert isinstance(accepted, VerificationAccepted)
    assert accepted.manifest_sha256 == created.manifest_sha256
    model = load_manifest(first.read_bytes())
    assert [item.path.root for item in model.artifacts] == ["empty.bin", "nested/sample.bin"]
    with pytest.raises(ValidationError):
        model.__setattr__("empty_allowed", True)


@pytest.mark.parametrize("mutation", ["change", "truncate", "delete", "add", "rename"])
def test_changed_inventory_rejected(tmp_path: Path, mutation: str) -> None:
    root = create_root(tmp_path)
    manifest = tmp_path.resolve() / "manifest.toml"
    assert isinstance(seal(SealRequest(root=root, output=manifest)), SealCreated)
    member = root / "nested" / "sample.bin"
    if mutation == "change":
        member.write_bytes(b"different!!!")
    elif mutation == "truncate":
        member.write_bytes(b"s")
    elif mutation == "delete":
        member.unlink()
    elif mutation == "rename":
        member.rename(root / "renamed.bin")
    else:
        (root / "added.bin").write_bytes(b"new")
    result = verify(VerifyRequest(root=root, manifest=manifest))
    assert isinstance(result, VerificationRejected)
    assert result.issue.code == "inventory-mismatch"


@pytest.mark.parametrize("name", ["", "/absolute", "a/../b", "./x", "a//b", "a/", "a\\b", "C:x"])
def test_path_values_reject_noncanonical_names(name: str) -> None:
    with pytest.raises(ValidationError):
        ArtifactPath(name)


@pytest.mark.parametrize("kind", ["file", "directory", "dangling", "fifo"])
def test_symlinks_and_special_files_rejected(tmp_path: Path, kind: str) -> None:
    root = create_root(tmp_path)
    extra = root / "bad"
    if kind == "fifo":
        os.mkfifo(extra)
    elif kind == "directory":
        extra.symlink_to(root / "nested", target_is_directory=True)
    elif kind == "dangling":
        extra.symlink_to(tmp_path / "missing")
    else:
        extra.symlink_to(root / "empty.bin")
    result = seal(SealRequest(root=root, output=tmp_path.resolve() / "seal.toml"))
    assert isinstance(result, SealRejected)
    assert result.issue.code == "unsupported-entry"


def test_root_and_output_parent_symlinks_rejected(tmp_path: Path) -> None:
    root = create_root(tmp_path)
    alias = tmp_path.resolve() / "alias"
    alias.symlink_to(root, target_is_directory=True)
    assert isinstance(seal(SealRequest(root=alias, output=tmp_path / "one.toml")), SealRejected)
    outside = tmp_path.resolve() / "outside"
    outside.mkdir()
    output_alias = tmp_path.resolve() / "output-alias"
    output_alias.symlink_to(outside, target_is_directory=True)
    assert isinstance(seal(SealRequest(root=root, output=output_alias / "two.toml")), SealRejected)
    nested_alias = tmp_path.resolve() / "parent-alias"
    nested_alias.symlink_to(tmp_path.resolve(), target_is_directory=True)
    assert isinstance(
        seal(SealRequest(root=nested_alias / "evidence", output=outside / "three.toml")),
        SealRejected,
    )


def test_output_inside_root_and_no_overwrite(tmp_path: Path) -> None:
    root = create_root(tmp_path)
    assert isinstance(seal(SealRequest(root=root, output=root / "seal.toml")), SealRejected)
    existing = tmp_path.resolve() / "existing.toml"
    existing.write_bytes(b"preserve exactly")
    result = seal(SealRequest(root=root, output=existing))
    assert isinstance(result, SealRejected) and result.issue.code == "destination-exists"
    assert existing.read_bytes() == b"preserve exactly"
    link = tmp_path.resolve() / "link.toml"
    link.symlink_to(tmp_path / "missing")
    assert isinstance(seal(SealRequest(root=root, output=link)), SealRejected)
    assert link.is_symlink()


def test_explicit_empty_inventory(tmp_path: Path) -> None:
    root = tmp_path.resolve() / "empty"
    root.mkdir()
    output = tmp_path.resolve() / "empty.toml"
    assert isinstance(seal(SealRequest(root=root, output=output)), SealRejected)
    assert not output.exists()
    assert isinstance(seal(SealRequest(root=root, output=output, allow_empty=True)), SealCreated)
    assert isinstance(verify(VerifyRequest(root=root, manifest=output)), VerificationAccepted)
    output.write_bytes(
        output.read_bytes().replace(b"empty_allowed = true", b"empty_allowed = false")
    )
    assert isinstance(verify(VerifyRequest(root=root, manifest=output)), VerificationRejected)


@pytest.mark.parametrize(
    "mutation", ["version", "missing-schema", "extra", "duplicate", "bool-size"]
)
def test_invalid_external_manifest_rejected(tmp_path: Path, mutation: str) -> None:
    root = create_root(tmp_path)
    output = tmp_path.resolve() / "manifest.toml"
    assert isinstance(seal(SealRequest(root=root, output=output)), SealCreated)
    content = output.read_text()
    if mutation == "version":
        content = content.replace("manifest/1", "manifest/999")
    elif mutation == "missing-schema":
        content = "\n".join(content.splitlines()[1:])
    elif mutation == "extra":
        content += "unrecognized = 1\n"
    elif mutation == "duplicate":
        content += "\n[[artifacts]]\n" + content.split("[[artifacts]]\n")[-1]
    else:
        content = content.replace("size_bytes = 0", "size_bytes = false")
    output.write_text(content)
    result = verify(VerifyRequest(root=root, manifest=output))
    assert isinstance(result, VerificationRejected)
    assert result.issue.code == "invalid-manifest-or-path"


def test_observed_midread_change_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = create_root(tmp_path)
    member = root / "nested" / "sample.bin"
    real_read = os.read
    changed = False

    def mutate_after_read(fd: int, size: int) -> bytes:
        nonlocal changed
        value = real_read(fd, size)
        if value and not changed:
            changed = True
            member.write_bytes(b"changed during hash")
        return value

    monkeypatch.setattr(os, "read", mutate_after_read)
    output = tmp_path.resolve() / "manifest.toml"
    result = seal(SealRequest(root=root, output=output))
    assert isinstance(result, SealRejected)
    assert result.issue.code == "observed-change"
    assert not output.exists()


def test_prepublication_fsync_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = create_root(tmp_path)
    output = tmp_path.resolve() / "manifest.toml"

    def fail_sync(fd: int) -> None:
        raise OSError("injected file sync failure")

    monkeypatch.setattr(os, "fsync", fail_sync)
    result = seal(SealRequest(root=root, output=output))
    assert isinstance(result, SealRejected)
    assert not output.exists()
    assert not list(tmp_path.glob(".mho-evidence-*.tmp"))


def test_published_directory_sync_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = create_root(tmp_path)
    output = tmp_path.resolve() / "manifest.toml"
    real_sync = os.fsync

    def fail_directory_sync(fd: int) -> None:
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("injected directory sync failure")
        real_sync(fd)

    monkeypatch.setattr(os, "fsync", fail_directory_sync)
    result = seal(SealRequest(root=root, output=output))
    assert isinstance(result, SealPublishedUncertain)
    assert output.is_file()
    assert isinstance(verify(VerifyRequest(root=root, manifest=output)), VerificationAccepted)
    assert isinstance(seal(SealRequest(root=root, output=output)), SealRejected)


def test_competing_publication_never_overwrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = create_root(tmp_path)
    output = tmp_path.resolve() / "manifest.toml"
    original_link = os.link

    def competing_link(
        source: str,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        output.write_bytes(b"competing publisher")
        original_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(os, "link", competing_link)
    outcome = seal(SealRequest(root=root, output=output))
    assert isinstance(outcome, SealRejected)
    assert outcome.issue.code == "destination-exists"
    assert output.read_bytes() == b"competing publisher"


def test_verification_rejects_manifest_link(tmp_path: Path) -> None:
    root = create_root(tmp_path)
    output = tmp_path.resolve() / "manifest.toml"
    assert isinstance(seal(SealRequest(root=root, output=output)), SealCreated)
    alias = tmp_path.resolve() / "manifest-alias.toml"
    alias.symlink_to(output)
    assert isinstance(verify(VerifyRequest(root=root, manifest=alias)), VerificationRejected)


@pytest.mark.parametrize("mutation", ["temporary-bytes", "output-parent"])
def test_publication_change_reported_uncertain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    root = create_root(tmp_path)
    parent = tmp_path.resolve() / "publication"
    parent.mkdir()
    output = parent / "manifest.toml"
    original_link = os.link

    def changed_link(
        source: str,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
        follow_symlinks: bool,
    ) -> None:
        if mutation == "temporary-bytes":
            (parent / source).write_bytes(b"replaced temporary bytes")
        else:
            parent.rename(tmp_path.resolve() / "moved-publication")
            parent.mkdir()
        original_link(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(os, "link", changed_link)
    outcome = seal(SealRequest(root=root, output=output))
    assert isinstance(outcome, SealPublishedUncertain)
    assert outcome.issue.code == "observed-change"
    if mutation == "temporary-bytes":
        assert output.read_bytes() == b"replaced temporary bytes"
    else:
        assert not output.exists()
        assert (tmp_path.resolve() / "moved-publication" / "manifest.toml").is_file()
