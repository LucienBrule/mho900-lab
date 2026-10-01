"""Thin original RAW AC statistics endpoint and structural TOML presentation."""

from pathlib import Path

import click
from pydantic import ValidationError

from mho_rf import RawAcStatistics, RawStatisticsIssue, RawStatisticsRejected, RawStatisticsResult
from mho_waveform import RawAcquisition

from .presentation import toml_scalar as scalar
from .raw_ac_delegate import inspect_raw_ac
from .waveform_delegate import WaveformInspectionRequest


@click.command("raw-ac-inspect")
@click.option("--preamble-before", type=click.Path(path_type=Path), required=True)
@click.option("--data", "data_path", type=click.Path(path_type=Path), required=True)
@click.option("--preamble-after", type=click.Path(path_type=Path), required=True)
@click.option("--actual-rate-hz", type=float, required=True)
@click.option("--memory-points", type=int, required=True)
@click.option("--start", type=int, required=True)
@click.option("--stop", type=int, required=True)
def raw_ac_inspect_command(
    preamble_before: Path,
    data_path: Path,
    preamble_after: Path,
    actual_rate_hz: float,
    memory_points: int,
    start: int,
    stop: int,
) -> None:
    """Compute supplied original RAW AC statistics; no receive or experiment gate."""
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
            ),
        )
    except ValidationError:
        present_raw_ac(
            RawStatisticsRejected(
                issue=RawStatisticsIssue(
                    stage="input", code="invalid-contract", message="supplied observations invalid"
                )
            )
        )
        raise click.exceptions.Exit(1) from None
    result = inspect_raw_ac(request)
    present_raw_ac(result)
    if isinstance(result, RawStatisticsRejected):
        raise click.exceptions.Exit(1)


def present_raw_ac(result: RawStatisticsResult) -> None:
    scalar("schema_version", "mho-rf.raw-ac-inspection/1")
    scalar("result", result.kind)
    scalar("classification", "supplied original RAW sampled AC statistics")
    scalar("method", "unwindowed-demeaned-population")
    scalar("physical_origin_proven", False)
    scalar("calibrated_amplitude_proven", False)
    scalar("receive_qualification_proven", False)
    if isinstance(result, RawStatisticsRejected):
        scalar("stage", result.issue.stage)
        scalar("code", result.issue.code)
        scalar("message", result.issue.message)
        if result.issue.token_index is not None:
            scalar("token_index", result.issue.token_index)
    if result.evidence is not None:
        scalar("preamble_before_sha256", result.evidence.preamble_before_sha256)
        scalar("waveform_sha256", result.evidence.waveform_sha256)
        scalar("preamble_after_sha256", result.evidence.preamble_after_sha256)
    if isinstance(result, RawAcStatistics):
        g = result.geometry
        click.echo("\n[geometry]")
        scalar("points", g.points)
        scalar("acquisition_count", g.acquisition_count)
        scalar("memory_points", g.memory_points)
        scalar("start", g.start)
        scalar("stop", g.stop)
        scalar("actual_sample_rate_hz", g.actual_sample_rate_hz)
        scalar("interval_sample_rate_hz", g.interval_sample_rate_hz)
        scalar("interval_relative_tolerance", g.interval_relative_tolerance)
        scalar("x_increment_s", g.x_increment_s)
        scalar("record_duration_s", g.record_duration_s)
        scalar("first_to_last_span_s", g.first_to_last_span_s)
        m = result.metrics
        click.echo("\n[metrics]")
        scalar("dc_mean_v", m.dc_mean_v)
        scalar("voltage_min_v", m.voltage_min_v)
        scalar("voltage_max_v", m.voltage_max_v)
        scalar("voltage_vpp_v", m.voltage_vpp_v)
        scalar("ac_rms_v", m.ac_rms_v)
        scalar("constant_samples", m.constant_samples)
        scalar("zero_sampled_ac", m.zero_sampled_ac)
