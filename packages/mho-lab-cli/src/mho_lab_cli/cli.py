"""Thin Click presentation adapters."""

from pathlib import Path

import click

from mho_lab_cli.capture_cli import capture
from mho_lab_cli.delegates import PolicyRejected, check_quality, identify_tool
from mho_lab_cli.evidence_cli import evidence
from mho_lab_cli.review_cli import review
from mho_lab_cli.scpi_cli import scpi
from mho_lab_cli.transport_cli import transport


@click.group()
def main() -> None:
    """Offline research tooling for MHO900 Lab."""


main.add_command(evidence)
main.add_command(transport)
main.add_command(capture)
main.add_command(scpi)
main.add_command(review)


@main.command()
def version() -> None:
    """Print this tool's version; do not contact an instrument."""
    identity = identify_tool()
    click.echo(f"{identity.name} {identity.version}")


@main.command()
@click.argument("paths", type=click.Path(path_type=Path), nargs=-1, required=True)
def quality(paths: tuple[Path, ...]) -> None:
    """Check authored typing conventions in explicit source paths."""
    result = check_quality(paths)
    if isinstance(result, PolicyRejected):
        for issue in result.violations:
            click.echo(f"{issue.path}:{issue.line}: {issue.reason}", err=True)
        raise click.exceptions.Exit(1)
    click.echo("Typing policy passed.")
