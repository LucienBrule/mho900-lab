"""Read-only command presentation for retained packet-capture evidence."""

from pathlib import Path

import click

from mho_lab_cli.capture_delegate import CaptureReportRejected, inspect_capture_report


@click.group()
def capture() -> None:
    """Assess existing files; never open a network capture interface."""


@capture.command("assess")
@click.argument("pcap", type=click.Path(path_type=Path))
@click.option("--stderr", type=click.Path(path_type=Path), required=True)
def assess_command(pcap: Path, stderr: Path) -> None:
    """Compare stored frame counts with final tcpdump statistics."""
    result = inspect_capture_report(pcap, stderr)
    if isinstance(result, CaptureReportRejected):
        click.echo(f"{result.stage}/{result.issue.code}: {result.issue.message}", err=True)
        raise click.exceptions.Exit(1)
    metadata = result.capture
    counts = result.statistics
    click.echo('schema_version = "mho-capture.assessment/1"')
    click.echo('result = "accepted"')
    click.echo(f'capture_sha256 = "{metadata.capture_sha256}"')
    click.echo(f"capture_bytes = {metadata.capture_bytes}")
    click.echo(f"capture_frames = {metadata.capture_frames}")
    click.echo(f'statistics_sha256 = "{counts.raw_sha256}"')
    click.echo(f"packets_captured = {counts.captured}")
    click.echo(f"packets_received_by_filter = {counts.received_by_filter}")
    click.echo(f"packets_dropped_by_kernel = {counts.dropped_by_kernel}")
    click.echo(f"statistics_groups = {counts.group_count}")
    click.echo("process_exit_proven = false")
    click.echo("wire_completeness_proven = false")
    click.echo("drop_reporting_support_established = false")
