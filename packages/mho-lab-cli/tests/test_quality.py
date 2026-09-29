"""Executable positive and negative fixtures for the bounded typing policy."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from mho_lab_cli.quality import PolicyViolation, check_paths


@dataclass(frozen=True)
class RejectedSource:
    name: str
    source: str
    reason: str


REJECTED = [
    RejectedSource("any-import", "from typing import Any\nx: Any\n", "explicit type"),
    RejectedSource("any-qualified", "import typing as t\nx: t.Any\n", "explicit type"),
    RejectedSource("any-forward", "x: 'Any'\n", "explicit type"),
    RejectedSource(
        "any-alias",
        "from typing import Any as Escape\nAlias = Escape\ndef f(x: Alias) -> None: pass\n",
        "explicit type",
    ),
    RejectedSource(
        "any-getattr",
        "import typing as t\nEscape = getattr(t, 'Any')\nx: Escape\n",
        "explicit type",
    ),
    RejectedSource("legacy-dict", "from typing import Dict as D\nx: D[str, int]\n", "built-in"),
    RejectedSource("legacy-tuple", "import typing\nx: typing.Tuple[int, ...]\n", "built-in"),
    RejectedSource("fixed-tuple", "x: tuple[str, int]\n", "Fixed tuple"),
    RejectedSource("tuple-alias", "Pair = tuple[str, int]\n", "Fixed tuple"),
    RejectedSource("pep695-alias", "type Pair = tuple[str, int]\n", "Fixed tuple"),
    RejectedSource(
        "marked-alias",
        "from typing import TypeAlias\nPair: TypeAlias = tuple[str, int]\n",
        "Fixed tuple",
    ),
    RejectedSource("fixed-forward", "x: 'tuple[int, int]'\n", "Fixed tuple"),
    RejectedSource("bare-list", "x: list\n", "element types"),
    RejectedSource("bare-nested", "x: dict[str, list]\n", "element types"),
    RejectedSource(
        "bare-abc", "from collections.abc import Sequence as Seq\nx: Seq\n", "element types"
    ),
    RejectedSource("bare-forward", "def f() -> 'set': pass\n", "element types"),
    RejectedSource("type-comment", "x = []  # type: list\n", "element types"),
    RejectedSource("cast", "from typing import cast as c\nx = c(int, 3)\n", "typing.cast"),
    RejectedSource("tuple-record", "def f(): return 1, 'a'\n", "Tuple return"),
    RejectedSource("lambda-record", "f = lambda: (1, 'a')\n", "Lambda tuple"),
    RejectedSource("named-tuple", "from typing import NamedTuple\n", "named dataclass"),
    RejectedSource("namedtuple", "from collections import namedtuple as nt\n", "named dataclass"),
    RejectedSource("ignore", "x = 3  # type: ignore\n", "Blanket"),
    RejectedSource("ignore-empty", "x = 3  # type: ignore[]\n", "Blanket"),
    RejectedSource("noqa", "x = 3  # noqa\n", "Blanket"),
    RejectedSource("noqa-empty", "x = 3  # noqa: \n", "Blanket"),
    RejectedSource("star-import", "from typing import *\n", "Wildcard"),
]


@pytest.mark.parametrize("case", REJECTED, ids=lambda case: case.name)
def test_rejects_policy_fixture(tmp_path: Path, case: RejectedSource) -> None:
    path = tmp_path / "fixture.py"
    path.write_text(case.source)
    violations = check_paths([path])
    assert any(case.reason in violation.reason for violation in violations)
    assert all(violation.path == path and violation.line > 0 for violation in violations)
    assert path.read_text() == case.source


def test_alias_reference_itself_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "aliases.py"
    path.write_text("from typing import Any as Escape\nAlias = Escape\nx: Alias\n")
    assert any(v.line == 3 and "explicit type" in v.reason for v in check_paths([path]))


def test_allows_typed_collections_and_named_records(tmp_path: Path) -> None:
    path = tmp_path / "valid.py"
    path.write_text(
        "from dataclasses import dataclass\n"
        "from typing import Annotated, Literal\n"
        "@dataclass\n"
        "class Record:\n"
        "    count: int\n"
        "    names: list[str]\n"
        "def collect(values: dict[str, int]) -> tuple[int, ...]:\n"
        "    for key, value in values.items():\n"
        "        print(key, value)\n"
        "    return (1, 2)\n"
        "def text() -> 'tuple[str, ...]':\n"
        "    return ('Any', 'type: ignore')\n"
        "label: Literal['Any', 'tuple[int, str]']\n"
        "metadata: Annotated[list[int], 'Any']\n"
        "specific = 1  # noqa: F841\n"
        "specific_type = 1  # type: ignore[assignment]\n"
    )
    assert check_paths([path]) == []


def test_type_check_comments_inside_strings_are_not_suppressions(tmp_path: Path) -> None:
    path = tmp_path / "strings.py"
    path.write_text('text = "# noqa and # type: ignore"\n')
    assert check_paths([path]) == []


def test_parse_errors_and_missing_paths_are_violations(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.py"
    invalid.write_text("def broken(:\n")
    missing = tmp_path / "missing.py"
    violations = check_paths([invalid, missing])
    assert len(violations) == 2
    assert any("Cannot parse" in violation.reason for violation in violations)
    assert PolicyViolation(missing, 0, "Requested path does not exist.") in violations


def test_directory_scan_is_deterministic_and_deduplicated(tmp_path: Path) -> None:
    first = tmp_path / "a.py"
    second = tmp_path / "b.py"
    first.write_text("x: list\n")
    second.write_text("x: set\n")
    (tmp_path / "ignored.txt").write_text("x: Any\n")
    violations = check_paths([tmp_path, first])
    assert [v.path for v in violations] == [first, second]


def test_checker_and_tests_conform_to_their_own_policy() -> None:
    package = Path(__file__).resolve().parents[1]
    assert check_paths([package / "src/mho_lab_cli/quality.py", Path(__file__)]) == []
