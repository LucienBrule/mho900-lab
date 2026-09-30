"""Public operations revalidate unchecked models before artifact consumption."""

from pathlib import Path

import pytest

import mho_evidence.archive as archive_module
import mho_evidence.operations as operations
from mho_evidence import (
    ArchiveLimits,
    ArchiveRejected,
    ArchiveRequest,
    Sha256,
    VerificationLimits,
    VerificationRejected,
    VerifyRequest,
    inspect_archive,
    verify,
)
from mho_evidence.manifest import Artifact, ArtifactPath, ManifestV1, dump_manifest, load_manifest


def no_open(path: Path) -> int:
    raise AssertionError("invalid model reached filesystem")


@pytest.mark.parametrize("value", [None, float("inf"), True, -1, "PRIVATE-LIMIT"])
def test_archive_limit_cannot_disable_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: object
) -> None:
    monkeypatch.setattr(archive_module, "open_directory", no_open)
    limits = ArchiveLimits().model_copy(update={"max_source_bytes": value})
    result = inspect_archive(ArchiveRequest(tmp_path / "unused", Sha256("0" * 64), limits))
    assert isinstance(result, ArchiveRejected) and result.issue.code == "archive-contract"
    assert "PRIVATE" not in repr(result)


@pytest.mark.parametrize("field", ["max_entries", "max_manifest_bytes", "max_depth"])
@pytest.mark.parametrize("value", [None, float("inf"), True, -1, "PRIVATE-LIMIT"])
def test_verification_limit_cannot_disable_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    monkeypatch.setattr(operations, "open_directory", no_open)
    limits = VerificationLimits().model_copy(update={field: value})
    result = verify(VerifyRequest(tmp_path / "unused", tmp_path / "seal", limits))
    assert isinstance(result, VerificationRejected) and result.issue.code == "invalid-limits"
    assert "PRIVATE" not in repr(result)


def test_archive_pin_is_validated_before_file_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(archive_module, "open_directory", no_open)
    pin = Sha256("0" * 64).model_copy(update={"root": "PRIVATE-DIGEST"})
    result = inspect_archive(ArchiveRequest(tmp_path / "unused", pin))
    assert isinstance(result, ArchiveRejected) and "PRIVATE" not in repr(result)


def test_unchecked_nested_manifest_is_not_serialized() -> None:
    artifact = Artifact(path=ArtifactPath("a"), sha256=Sha256("0" * 64), size_bytes=1)
    manifest = ManifestV1(
        schema_version="mho-evidence.manifest/1",
        inventory="recursive-regular-files",
        artifacts=(artifact,),
    )
    bad_pin = artifact.sha256.model_copy(update={"root": "PRIVATE-DIGEST"})
    bad_artifact = artifact.model_copy(update={"sha256": bad_pin})
    unchecked = manifest.model_copy(update={"artifacts": (bad_artifact,)})
    with pytest.raises(ValueError) as error:
        dump_manifest(unchecked)
    assert "PRIVATE" not in str(error.value)


def test_malformed_manifest_diagnostic_does_not_echo_invalid_field() -> None:
    raw = b"""schema_version="mho-evidence.manifest/1"
inventory="recursive-regular-files"
[[artifacts]]
path="a"
sha256="PRIVATE-DIGEST"
size_bytes=1
"""
    with pytest.raises(ValueError) as error:
        load_manifest(raw)
    assert "PRIVATE" not in str(error.value)
