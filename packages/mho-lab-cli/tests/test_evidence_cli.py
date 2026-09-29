"""Exercise the public CLI through real local files and named failure outcomes."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from mho_evidence import EvidenceIssue, SealPublishedUncertain
from mho_lab_cli import evidence_cli
from mho_lab_cli.cli import main


def test_seal_verify_and_detect_extra_file(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    root.mkdir()
    (root / "capture.txt").write_bytes(b"unaltered external evidence\n")
    manifest = tmp_path / "manifest.toml"
    runner = CliRunner()
    sealed = runner.invoke(main, ["evidence", "seal", str(root), "--output", str(manifest)])
    assert sealed.exit_code == 0, sealed.output
    assert "Artifacts: 1; bytes: 28" in sealed.output
    original = manifest.read_bytes()
    verified = runner.invoke(main, ["evidence", "verify", str(root), "--manifest", str(manifest)])
    assert verified.exit_code == 0, verified.output
    assert "Verified SHA-256:" in verified.output
    (root / "unexpected.txt").write_bytes(b"extra")
    rejected = runner.invoke(main, ["evidence", "verify", str(root), "--manifest", str(manifest)])
    assert rejected.exit_code == 1
    assert "inventory-mismatch" in rejected.output
    assert manifest.read_bytes() == original


def test_existing_destination_preserved(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    root.mkdir()
    (root / "file").write_bytes(b"content")
    manifest = tmp_path / "existing.toml"
    manifest.write_bytes(b"preserve me")
    result = CliRunner().invoke(main, ["evidence", "seal", str(root), "--output", str(manifest)])
    assert result.exit_code == 1
    assert "destination-exists" in result.output
    assert manifest.read_bytes() == b"preserve me"


def test_empty_requires_explicit_flag(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    manifest = tmp_path / "empty.toml"
    runner = CliRunner()
    arguments = ["evidence", "seal", str(root), "--output", str(manifest)]
    assert runner.invoke(main, arguments).exit_code == 1
    assert not manifest.exists()
    assert runner.invoke(main, [*arguments, "--allow-empty"]).exit_code == 0
    result = runner.invoke(main, ["evidence", "verify", str(root), "--manifest", str(manifest)])
    assert result.exit_code == 0, result.output


def test_cli_preserves_symlink_for_library_rejection(tmp_path: Path) -> None:
    root = tmp_path / "actual"
    root.mkdir()
    (root / "file").write_bytes(b"evidence")
    linked = tmp_path / "alias"
    linked.symlink_to(root, target_is_directory=True)
    output = tmp_path / "manifest.toml"
    result = CliRunner().invoke(main, ["evidence", "seal", str(linked), "--output", str(output)])
    assert result.exit_code == 1
    assert not output.exists()


def test_published_uncertain_is_not_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "manifest.toml"

    def uncertain(root: Path, output: Path, *, allow_empty: bool) -> SealPublishedUncertain:
        return SealPublishedUncertain(
            output=output,
            manifest_sha256="a" * 64,
            issue=EvidenceIssue(code="filesystem-error", message="directory sync failed"),
        )

    monkeypatch.setattr(evidence_cli, "seal_evidence", uncertain)
    result = CliRunner().invoke(main, ["evidence", "seal", str(tmp_path), "--output", str(output)])
    assert result.exit_code == 3
    assert "publication requires inspection" in result.output
    assert "directory sync failed" in result.output
    assert "Manifest created:" not in result.output
