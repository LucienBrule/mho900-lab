"""Bounded authored-import controls, not a claim about dynamic Python behavior."""

import ast
from importlib.util import resolve_name
from pathlib import Path

import pytest

PACKAGES = Path(__file__).resolve().parents[2]


def imports(module: str, source: str) -> tuple[str, ...]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            name = node.module or ""
            if node.level:
                name = resolve_name("." * node.level + name, module.rsplit(".", 1)[0])
            names.add(name)
            names.update(name + "." + alias.name for alias in node.names)
    return tuple(sorted(names))


def violations(module: str, source: str) -> tuple[str, ...]:
    findings: set[str] = set()
    is_cli = module.startswith("mho_lab_cli.")
    is_delegate = module.endswith(("_delegate", ".delegates"))
    for target in imports(module, source):
        top = target.split(".")[0]
        command = target.startswith("mho_lab_cli.") and any(
            part.endswith("_cli") or part == "cli" for part in target.split(".")[1:]
        )
        if not is_cli and top in {"click", "mho_lab_cli"}:
            findings.add("library imports presentation: " + target)
        if is_cli and module != "mho_lab_cli.cli" and command:
            findings.add("non-aggregator imports command: " + target)
        if is_delegate and (
            top == "click" or target.startswith("mho_lab_cli.presentation") or command
        ):
            findings.add("delegate imports presentation: " + target)
    return tuple(sorted(findings))


def test_workspace_authored_import_layers() -> None:
    checked = 0
    for path in sorted(PACKAGES.glob("*/src/**/*.py")):
        source_root = path.parents[len(path.relative_to(PACKAGES).parts) - 3]
        module = ".".join(path.relative_to(source_root).with_suffix("").parts)
        assert not violations(module, path.read_text()), module
        checked += 1
    assert checked > 30


@pytest.mark.parametrize(
    "module,source",
    [
        ("mho_evidence.manifest", "import click"),
        ("mho_evidence.manifest", "from mho_lab_cli import presentation"),
        ("mho_lab_cli.adb_cli", "from .scpi_cli import toml_string"),
        ("mho_lab_cli.archive_cli", "from . import scpi_cli"),
        ("mho_lab_cli.adb_delegate", "from click import echo"),
        ("mho_lab_cli.delegates", "from .presentation import toml_string"),
    ],
)
def test_layer_control_rejects_actual_dependency_inversions(module: str, source: str) -> None:
    assert violations(module, source)


@pytest.mark.parametrize(
    "module,source",
    [
        ("mho_evidence.manifest", "from .contracts import Artifact"),
        ("mho_lab_cli.cli", "from .scpi_cli import scpi"),
        ("mho_lab_cli.scpi_cli", "from .presentation import render_observations"),
        ("mho_lab_cli.scpi_delegate", "from mho_scpi import decode_exchange"),
    ],
)
def test_layer_control_preserves_intended_direction(module: str, source: str) -> None:
    assert not violations(module, source)
