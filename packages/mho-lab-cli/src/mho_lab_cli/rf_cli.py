"""Thin offline receive-guard endpoint with structural TOML and no sample/path disclosure."""

from pathlib import Path

import click
from pydantic import ValidationError

from mho_rf import ReceiveIssue, ReceiveRejected, ReceiveResult
from mho_waveform import RawAcquisition

from .presentation import toml_string
from .rf_delegate import ReceiveInspectionRequest, inspect_receive


@click.group()
def rf() -> None:
    """Inspect supplied RAW records without contacting an instrument."""


@rf.command("receive-inspect")
@click.option("--preamble-before", type=click.Path(path_type=Path), required=True)
@click.option("--data", "data_path", type=click.Path(path_type=Path), required=True)
@click.option("--preamble-after", type=click.Path(path_type=Path), required=True)
@click.option("--actual-rate-hz", type=float, required=True)
@click.option("--memory-points", type=int, required=True)
@click.option("--start", type=int, required=True)
@click.option("--stop", type=int, required=True)
@click.option("--command-frequency-hz", type=float, required=True)
def receive_inspect_command(
    preamble_before: Path,
    data_path: Path,
    preamble_after: Path,
    actual_rate_hz: float,
    memory_points: int,
    start: int,
    stop: int,
    command_frequency_hz: float,
) -> None:
    """Apply the default frozen periodic-Hann receive profile to supplied files.

    Supplied rate/extent assertions and sampled-frequency acceptance do not prove
    physical origin, calibrated amplitude or validity of a later fitted model.
    """
    try:
        request = ReceiveInspectionRequest(
            preamble_before=preamble_before,
            waveform=data_path,
            preamble_after=preamble_after,
            command_frequency_hz=command_frequency_hz,
            acquisition=RawAcquisition(
                actual_sample_rate_hz=actual_rate_hz,
                memory_points=memory_points,
                start=start,
                stop=stop,
            ),
        )
    except ValidationError:
        present_receive(
            ReceiveRejected(
                issue=ReceiveIssue(
                    stage="input", code="invalid-contract", message="supplied observations invalid"
                )
            )
        )
        raise click.exceptions.Exit(1) from None
    result = inspect_receive(request)
    present_receive(result)
    if isinstance(result, ReceiveRejected):
        raise click.exceptions.Exit(1)


def scalar(name: str, value: object) -> None:
    """Narrow supported scalar/profile values at the presentation boundary."""
    if isinstance(value, str):
        rendered = toml_string(value)
    elif isinstance(value, bool):
        rendered = str(value).lower()
    elif isinstance(value, (int, float)):
        rendered = repr(value)
    elif isinstance(value, tuple) and all(isinstance(v, int) for v in value):
        rendered = "[" + ", ".join(str(v) for v in value) + "]"
    else:
        raise TypeError("unsupported receive presentation value")
    click.echo(f"{name} = {rendered}")


def present_receive(result: ReceiveResult) -> None:
    scalar("schema_version", "mho-rf.receive-inspection/1")
    scalar("result", result.kind)
    scalar("classification", "supplied RAW sampled-frequency receive qualification")
    scalar("physical_origin_proven", False)
    scalar("calibrated_amplitude_proven", False)
    scalar("final_fit_validity_proven", False)
    if isinstance(result, ReceiveRejected):
        scalar("stage", result.issue.stage)
        scalar("code", result.issue.code)
        scalar("message", result.issue.message)
        if result.issue.token_index is not None:
            scalar("token_index", result.issue.token_index)
    if result.command_frequency_hz is not None:
        scalar("command_frequency_hz", result.command_frequency_hz)
    if result.profile_sha256 is not None:
        scalar("profile_sha256", result.profile_sha256)
    if result.hashes is not None:
        for name in type(result.hashes).model_fields:
            scalar(name, getattr(result.hashes, name))
    if result.spectrum is not None:
        for name in type(result.spectrum).model_fields:
            scalar(name, getattr(result.spectrum, name))
    if result.profile is not None:
        click.echo("\n[profile]")
        for name in type(result.profile).model_fields:
            scalar(name, getattr(result.profile, name))
    if result.input is not None:
        click.echo("\n[input]")
        for name in type(result.input).model_fields:
            scalar(name, getattr(result.input, name))
