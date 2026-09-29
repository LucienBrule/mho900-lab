"""Redacted presentation of explicitly bound offline evidence facts."""

from pathlib import Path

import click

from mho_lab_cli.review_delegate import inspect_review
from mho_lab_cli.scpi_cli import render_observations, toml_string
from mho_review import ReviewAccepted, ReviewRejected


@click.group()
def review() -> None:
    """Review sealed files without launching processes or opening network connections."""


@review.command("inspect")
@click.option("--root", type=click.Path(path_type=Path), required=True)
@click.option("--manifest", type=click.Path(path_type=Path), required=True)
@click.option("--expected-manifest-sha256", required=True)
@click.option("--profile", type=click.Path(path_type=Path), required=True)
@click.option("--show-identity", is_flag=True, help="Include the exact private identity strings.")
def inspect_command(
    root: Path, manifest: Path, expected_manifest_sha256: str, profile: Path, show_identity: bool
) -> None:
    """Bind capture statistics, TCP bytes and SCPI observations to one pinned inventory."""
    result = inspect_review(root, manifest, expected_manifest_sha256, profile)
    click.echo('schema_version = "mho-review.report/1"')
    outcome: ReviewAccepted | ReviewRejected
    if isinstance(result, ReviewRejected):
        outcome = result
    else:
        click.echo(f'profile_sha256 = "{result.profile_sha256}"')
        outcome = result.outcome
    if isinstance(outcome, ReviewRejected):
        click.echo('result = "rejected"')
        click.echo(f"stage = {toml_string(outcome.issue.stage)}")
        click.echo(f"code = {toml_string(outcome.issue.code)}")
        click.echo(f"message = {toml_string(outcome.issue.message)}")
        raise click.exceptions.Exit(1)
    click.echo('result = "accepted"')
    click.echo(f'manifest_sha256 = "{outcome.manifest_sha256}"')
    click.echo(f"inventory_files = {outcome.inventory.artifact_count}")
    click.echo(f"inventory_bytes = {outcome.inventory.total_bytes}")
    capture = outcome.capture_assessment.capture
    counts = outcome.capture_assessment.statistics
    click.echo(f'capture_sha256 = "{capture.capture_sha256}"')
    click.echo(f'statistics_sha256 = "{counts.raw_sha256}"')
    click.echo(f"capture_frames = {capture.capture_frames}")
    click.echo(f"selected_tcp_frames = {outcome.transcript.metadata.selected_tcp_frames}")
    click.echo(f"packets_captured = {counts.captured}")
    click.echo(f"packets_received_by_filter = {counts.received_by_filter}")
    click.echo(f"packets_dropped_by_kernel = {counts.dropped_by_kernel}")
    click.echo(f"query_count = {len(outcome.exchange.pairs)}")
    click.echo("selected_transcript_bytes_equal = true")
    click.echo("physical_origin_proven = false")
    click.echo("atomic_snapshot_proven = false")
    click.echo("process_exit_proven = false")
    click.echo("wire_completeness_proven = false")
    click.echo("drop_reporting_support_established = false")
    click.echo("peer_delivery_proven = false")
    click.echo("device_execution_proven = false")
    click.echo("response_causality_proven = false")
    render_observations(outcome.exchange, show_identity)
