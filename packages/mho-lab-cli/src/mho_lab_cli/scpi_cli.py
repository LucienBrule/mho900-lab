"""Offline SCPI transcript presentation with opt-in identity disclosure."""

import hashlib
from pathlib import Path

import click

from mho_lab_cli.scpi_delegate import ScpiInputRejected, inspect_scpi
from mho_scpi import ExchangeAccepted, ExchangeRejected, IdentityObservation


def toml_string(value: str) -> str:
    """Quote an external string without interpreting its contents as TOML."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return '"' + escaped + '"'


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


def render_observations(result: ExchangeAccepted, show_identity: bool) -> None:
    """Render typed observations; identity disclosure remains an explicit choice."""
    for index, pair in enumerate(result.pairs):
        observation = pair.reply.observation
        click.echo("\n[[observations]]")
        click.echo(f"index = {index}")
        click.echo(f'kind = "{observation.kind}"')
        if isinstance(observation, IdentityObservation):
            click.echo(f"identity_redacted = {str(not show_identity).lower()}")
            if show_identity:
                click.echo(f"manufacturer = {toml_string(observation.manufacturer)}")
                click.echo(f"model = {toml_string(observation.model)}")
                click.echo(f"serial_number = {toml_string(observation.serial_number)}")
                click.echo(f"software_revision = {toml_string(observation.software_revision)}")
        else:
            click.echo(f'selector = "{observation.selector.value}"')
            click.echo(f'state = "{observation.state.value}"')
