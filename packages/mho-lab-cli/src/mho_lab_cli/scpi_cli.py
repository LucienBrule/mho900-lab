"""Offline SCPI transcript presentation with opt-in identity disclosure."""

import hashlib
from pathlib import Path

import click

from mho_lab_cli.presentation import render_observations
from mho_lab_cli.scpi_delegate import ScpiInputRejected, inspect_scpi
from mho_scpi import ExchangeRejected


@click.group()
def scpi() -> None:
    """Interpret preserved read-only query transcripts without opening a connection."""


@scpi.command("inspect")
@click.option("--requests", type=click.Path(path_type=Path), required=True)
@click.option("--replies", type=click.Path(path_type=Path), required=True)
@click.option("--show-identity", is_flag=True, help="Include all four exact identity strings.")
def inspect_command(requests: Path, replies: Path, show_identity: bool) -> None:
    """Decode canonical identity/option query pairs from two local raw files."""
    result = inspect_scpi(requests, replies)
    if isinstance(result, ScpiInputRejected):
        click.echo(f"input: {result.message}", err=True)
        raise click.exceptions.Exit(1)
    if isinstance(result, ExchangeRejected):
        click.echo(f"{result.issue.code}: {result.issue.message}", err=True)
        raise click.exceptions.Exit(1)
    click.echo('schema_version = "mho-scpi.observations/1"')
    click.echo('result = "accepted"')
    click.echo(f'request_sha256 = "{hashlib.sha256(result.request).hexdigest()}"')
    click.echo(f'response_sha256 = "{hashlib.sha256(result.response).hexdigest()}"')
    click.echo(f"query_count = {len(result.pairs)}")
    click.echo("physical_origin_proven = false")
    render_observations(result, show_identity)
