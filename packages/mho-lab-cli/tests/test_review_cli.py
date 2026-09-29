"""Composed review failures remain structured and do not disclose private inputs."""

import tomllib
from pathlib import Path

import pytest
from click.testing import CliRunner

from mho_lab_cli.cli import main


@pytest.mark.parametrize("failure", ["digest", "missing", "schema", "symlink"])
def test_review_input_failures_are_redacted_toml(tmp_path: Path, failure: str) -> None:
    profile = tmp_path / "PRIVATE-PATH.toml"
    pin = "0" * 64
    if failure == "digest":
        pin = "PRIVATE-INVALID-DIGEST"
    elif failure == "schema":
        profile.write_text('private_identity = "PRIVATE-SERIAL"\n')
    elif failure == "symlink":
        source = tmp_path / "source"
        source.write_text("invalid")
        profile.symlink_to(source)
    result = CliRunner().invoke(
        main,
        [
            "review",
            "inspect",
            "--root",
            str(tmp_path / "root"),
            "--manifest",
            str(tmp_path / "manifest.toml"),
            "--expected-manifest-sha256",
            pin,
            "--profile",
            str(profile),
        ],
    )
    assert result.exit_code == 1
    document = tomllib.loads(result.output)
    assert document["result"] == "rejected"
    assert document["stage"] in ("input", "profile")
    assert "PRIVATE" not in result.output
