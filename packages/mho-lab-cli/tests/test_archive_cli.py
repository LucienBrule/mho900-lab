"""Archive CLI reports content changes without extracting or displaying payloads."""

import hashlib
import io
import tarfile
import tomllib
from pathlib import Path

from click.testing import CliRunner

from mho_lab_cli.cli import main


def fixture(path: Path, *, changed: bool) -> str:
    with tarfile.open(path, "w", format=tarfile.USTAR_FORMAT) as archive:
        for name, data in {
            "data/stable.bin": b"PRIVATE-UNCHANGED-PAYLOAD",
            "data/value.bin": b"PRIVATE-NEW-PAYLOAD" if changed else b"PRIVATE-OLD-PAYLOAD",
            **(
                {"data/added.bin": b"PRIVATE-ADDED"}
                if changed
                else {"data/removed.bin": b"PRIVATE-REMOVED"}
            ),
        }.items():
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_archive_delta_is_typed_and_payload_free(tmp_path: Path) -> None:
    before = tmp_path / "PRIVATE-HOST-before.tar"
    after = tmp_path / "PRIVATE-HOST-after.tar"
    before_digest = fixture(before, changed=False)
    after_digest = fixture(after, changed=True)
    result = CliRunner().invoke(
        main,
        [
            "archive",
            "diff",
            "--before",
            str(before),
            "--before-sha256",
            before_digest,
            "--after",
            str(after),
            "--after-sha256",
            after_digest,
        ],
    )
    assert result.exit_code == 0, result.output
    parsed = tomllib.loads(result.output)
    assert parsed["unchanged_files"] == 1
    assert parsed["changed_files"] == 3
    assert parsed["rename_inference_performed"] is False
    assert 'kind = "added"' in result.output
    assert 'kind = "removed"' in result.output
    assert 'kind = "modified"' in result.output
    assert "PRIVATE" not in result.output
    assert not (tmp_path / "data").exists()


def test_archive_inspect_and_wrong_pin(tmp_path: Path) -> None:
    path = tmp_path / "PRIVATE-HOST.tar"
    digest = fixture(path, changed=False)
    accepted = CliRunner().invoke(
        main, ["archive", "inspect", str(path), "--expected-sha256", digest]
    )
    assert accepted.exit_code == 0, accepted.output
    assert tomllib.loads(accepted.output)["file_count"] == 3
    assert "PRIVATE" not in accepted.output
    rejected = CliRunner().invoke(
        main, ["archive", "inspect", str(path), "--expected-sha256", "0" * 64]
    )
    assert rejected.exit_code == 1
    assert tomllib.loads(rejected.output)["result"] == "rejected"
    assert "PRIVATE" not in rejected.output


def test_after_rejection_preserves_named_stage(tmp_path: Path) -> None:
    before = tmp_path / "before.tar"
    digest = fixture(before, changed=False)
    result = CliRunner().invoke(
        main,
        [
            "archive",
            "diff",
            "--before",
            str(before),
            "--before-sha256",
            digest,
            "--after",
            str(tmp_path / "PRIVATE-MISSING.tar"),
            "--after-sha256",
            "0" * 64,
        ],
    )
    assert result.exit_code == 1
    assert tomllib.loads(result.output)["stage"] == "after"
    assert "PRIVATE" not in result.output
