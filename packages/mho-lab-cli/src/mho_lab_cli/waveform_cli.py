"""Offline raw ASCII waveform qualification rendered as structural TOML."""

import json
from pathlib import Path

import click
from pydantic import ValidationError

from mho_waveform import RawAcquisition, WaveformRejected

from .waveform_delegate import (
    WaveformInputRejected,
    WaveformInspectionRequest,
    inspect_waveform,
)


@click.group()
def waveform() -> None:
    """Inspect supplied waveform files without opening an instrument connection."""


@waveform.command("inspect")
@click.option("--preamble-before", type=click.Path(path_type=Path), required=True)
@click.option("--data", "data_path", type=click.Path(path_type=Path), required=True)
@click.option("--preamble-after", type=click.Path(path_type=Path), required=True)
@click.option("--actual-rate-hz", type=float, required=True)
@click.option("--memory-points", type=int, required=True)
@click.option("--start", type=int, required=True)
@click.option("--stop", type=int, required=True)
@click.option("--interval-relative-tolerance", type=float, default=1e-8, show_default=True)
def inspect_command(
    preamble_before: Path,
    data_path: Path,
    preamble_after: Path,
    actual_rate_hz: float,
    memory_points: int,
    start: int,
    stop: int,
    interval_relative_tolerance: float,
) -> None:
    """Qualify explicit RAW/ASCII evidence against supplied rate and selected extent.

    These observations are supplied assertions, not independent physical-origin proof.
    ASCII samples already represent volts and are never vertically rescaled.
    """
    try:
        request = WaveformInspectionRequest(
            preamble_before=preamble_before,
            waveform=data_path,
            preamble_after=preamble_after,
            acquisition=RawAcquisition(
                actual_sample_rate_hz=actual_rate_hz,
                memory_points=memory_points,
                start=start,
                stop=stop,
                interval_relative_tolerance=interval_relative_tolerance,
            ),
        )
    except ValidationError:
        present_rejection("input", "invalid-contract", "invalid supplied acquisition observations")
        raise click.exceptions.Exit(1) from None
    result = inspect_waveform(request)
    if isinstance(result, WaveformInputRejected):
        present_rejection("input", "input-files", result.message)
        raise click.exceptions.Exit(1)
    if isinstance(result, WaveformRejected):
        present_rejection(result.issue.stage, result.issue.code, result.issue.message)
        if result.issue.token_index is not None:
            click.echo(f"token_index = {result.issue.token_index}")
        raise click.exceptions.Exit(1)
    record = result.waveform
    evidence = record.evidence
    metadata = record.preamble
    click.echo('schema_version = "mho-waveform.inspection/1"')
    click.echo('result = "accepted"')
    click.echo('classification = "supplied raw ASCII voltage record"')
    click.echo("physical_origin_proven = false")
    click.echo("calibrated_rf_gain_proven = false")
    click.echo("ascii_volts_rescaled = false")
    click.echo(f'preamble_before_sha256 = "{evidence.preamble_before_sha256}"')
    click.echo(f'waveform_sha256 = "{evidence.waveform_sha256}"')
    click.echo(f'preamble_after_sha256 = "{evidence.preamble_after_sha256}"')
    click.echo(f'format = "{metadata.format.name}"')
    click.echo(f'mode = "{metadata.mode.name}"')
    click.echo(f"points = {metadata.points}")
    click.echo(f"acquisition_count = {metadata.acquisition_count}")
    click.echo(f"actual_sample_rate_hz = {result.acquisition.actual_sample_rate_hz!r}")
    click.echo(f"memory_points = {result.acquisition.memory_points}")
    click.echo(f"start = {result.acquisition.start}")
    click.echo(f"stop = {result.acquisition.stop}")
    click.echo(f"interval_relative_tolerance = {result.acquisition.interval_relative_tolerance!r}")
    click.echo(f"x_increment_s = {metadata.x_increment_s!r}")
    click.echo(f"x_origin_s = {metadata.x_origin_s!r}")
    click.echo(f"x_reference = {metadata.x_reference!r}")
    click.echo(f"record_duration_s = {result.record_duration_s!r}")
    click.echo(f"first_to_last_span_s = {result.first_to_last_span_s!r}")
    click.echo(f"voltage_min_v = {min(record.volts)!r}")
    click.echo(f"voltage_max_v = {max(record.volts)!r}")


def present_rejection(stage: str, code: str, message: str) -> None:
    click.echo('schema_version = "mho-waveform.inspection/1"')
    click.echo('result = "rejected"')
    click.echo("physical_origin_proven = false")
    click.echo("stage = " + json.dumps(stage))
    click.echo("code = " + json.dumps(code))
    click.echo("message = " + json.dumps(message))
