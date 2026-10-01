"""Explicit active source command; all other protocol interpretation stays offline."""

from pathlib import Path

import click
from pydantic import ValidationError

from mho_source import PointCommand, TransportComplete, encode_point

from .source_delegate import PointEvidenceFailed, point_once


@click.group()
def source() -> None:
    """Candidate RF source control. point-once opens hardware; frame is offline."""


@source.command("frame")
@click.option("--frequency-hz", type=int, required=True)
@click.option("--reference-hz", type=int, required=True)
@click.option("--power-code", type=int, required=True)
def frame_command(frequency_hz: int, reference_hz: int, power_code: int) -> None:
    """Print a candidate frame without opening a serial port."""
    try:
        command = PointCommand(
            frequency_hz=frequency_hz, reference_hz=reference_hz, power_code=power_code
        )
    except ValidationError:
        raise click.ClickException("invalid point command") from None
    click.echo(encode_point(command).hex(" ").upper())


@source.command("point-once")
@click.option("--device", type=click.Path(path_type=Path), required=True)
@click.option("--output", type=click.Path(path_type=Path), required=True)
@click.option("--frequency-hz", type=int, required=True)
@click.option("--reference-hz", type=int, required=True)
@click.option("--power-code", type=int, required=True)
def point_command(
    device: Path, output: Path, frequency_hz: int, reference_hz: int, power_code: int
) -> None:
    """Attempt ONE source setting command; requires an explicit, prevalidated port.

    May persist ordinary source settings. Keep both SMA ports empty for the
    compatibility experiment. Never retry an uncertain run automatically.
    """
    try:
        command = PointCommand(
            frequency_hz=frequency_hz, reference_hz=reference_hz, power_code=power_code
        )
    except ValidationError:
        raise click.ClickException("invalid point command; serial port not opened") from None
    result = point_once(command, device, output)
    if isinstance(result, PointEvidenceFailed):
        click.echo(
            f"evidence-incomplete: {result.phase}; execution_started={result.execution_started}",
            err=True,
        )
        click.echo("Inspect the retained run. Do not retry automatically.", err=True)
        raise click.exceptions.Exit(2)
    click.echo(f'result = "{result.outcome.kind}"')
    click.echo(f'manifest_sha256 = "{result.manifest_sha256}"')
    click.echo("device_acceptance_proven = false")
    if not isinstance(result.outcome, TransportComplete):
        raise click.exceptions.Exit(1)
