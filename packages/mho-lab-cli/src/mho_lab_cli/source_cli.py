"""Explicit active source command; all other protocol interpretation stays offline."""

from pathlib import Path

import click
from pydantic import ValidationError

from mho_source import (
    FactoryPointCommand,
    PointCommand,
    TransportComplete,
    encode_factory_point,
    encode_point,
)

from .source_delegate import PointEvidenceFailed, PointRunResult, point_once


@click.group()
def source() -> None:
    """RF source protocols. *-once opens hardware; *frame commands are offline."""


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
    present_result(point_once(command, device, output))


@source.command("factory-frame")
@click.option("--frequency-hz", type=int, required=True)
@click.option("--power-code", type=int, required=True)
def factory_frame_command(frequency_hz: int, power_code: int) -> None:
    """Print the recovered factory frame offline (10 kHz steps, raw power 0..3)."""
    try:
        command = FactoryPointCommand(frequency_hz=frequency_hz, power_code=power_code)
    except ValidationError as error:
        raise click.ClickException(str(error)) from None
    click.echo(encode_factory_point(command).hex(" ").upper())


@source.command("factory-point-once")
@click.option("--device", type=click.Path(path_type=Path), required=True)
@click.option("--output", type=click.Path(path_type=Path), required=True)
@click.option("--frequency-hz", type=int, required=True)
@click.option("--power-code", type=int, required=True)
def factory_point_command(device: Path, output: Path, frequency_hz: int, power_code: int) -> None:
    """Attempt ONE recovered factory point frame; may save source frequency.

    Requires a prevalidated port and known receiver state. Does not reset the
    source or send cleanup bytes. Keep both SMA ports empty during qualification.
    Raw power 0..3 is not calibrated dBm. Never retry uncertainty automatically.
    """
    try:
        command = FactoryPointCommand(frequency_hz=frequency_hz, power_code=power_code)
    except ValidationError as error:
        raise click.ClickException(f"serial port not opened: {error}") from None
    present_result(point_once(command, device, output))


def present_result(result: PointRunResult) -> None:
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
