"""Checks of the installed Click presentation boundary."""

from click.testing import CliRunner

from mho_lab_cli.cli import main


def test_version_is_tool_identity() -> None:
    result = CliRunner().invoke(main, ["version"])
    assert result.exit_code == 0
    assert result.output == "mho-lab 0.1.0\n"
