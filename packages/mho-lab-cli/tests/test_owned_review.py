"""The installed consumer also composes public APIs in the source gate."""

from pathlib import Path

import pytest
from installed_smoke import owned_recorder_review


def test_owned_child_to_sealed_review(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checkout = Path(__file__).resolve().parents[3]
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    monkeypatch.chdir(tmp_path)
    owned_recorder_review(checkout, evidence)
    assert (evidence / "owned-review.toml").is_file()
