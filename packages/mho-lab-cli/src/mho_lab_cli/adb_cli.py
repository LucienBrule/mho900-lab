"""Payload-free TOML observations from retained Android debug-bridge frames."""

from pathlib import Path

import click

from mho_adb import DecodeRejected, StreamReadyMissing, StreamReadyRejected
from mho_lab_cli.adb_delegate import (
    AdbInputRejected,
    AdbMatchBlocked,
    inspect_retained_stream,
    match_retained_streams,
)
from mho_lab_cli.scpi_cli import toml_string


def render_failure(result: AdbInputRejected | DecodeRejected) -> None:
    click.echo('result = "rejected"')
    if isinstance(result, AdbInputRejected):
        click.echo(f"code = {toml_string(result.code)}")
        click.echo(f"message = {toml_string(result.message)}")
    else:
        click.echo(f"code = {toml_string(result.issue.code)}")
        click.echo(f"message = {toml_string(result.issue.message)}")
        click.echo(f"byte_offset = {result.issue.byte_offset}")
        click.echo(f"parsed_prefix_frames = {len(result.prefix)}")
        click.echo(f"source_bytes = {result.raw_bytes}")
        if result.raw_sha256 is not None:
            click.echo(f'source_sha256 = "{result.raw_sha256}"')
    raise click.exceptions.Exit(1)


@click.group()
def adb() -> None:
    """Decode preserved files only; never run ADB or contact a device."""


@adb.command("inspect")
@click.argument("path", type=click.Path(path_type=Path))
@click.option("--expected-sha256", required=True)
def inspect_command(path: Path, expected_sha256: str) -> None:
    """Inspect complete frames under the explicit additive-checksum-required profile."""
    result = inspect_retained_stream(path, expected_sha256)
    click.echo('schema_version = "mho-adb.frame-report/1"')
    click.echo('checksum_profile = "additive-required/1"')
    if isinstance(result, (AdbInputRejected, DecodeRejected)):
        render_failure(result)
        return
    click.echo('result = "accepted"')
    click.echo(f'source_sha256 = "{result.raw_sha256}"')
    click.echo(f"source_bytes = {result.raw_bytes}")
    click.echo(f"frame_count = {len(result.frames)}")
    click.echo("handshake_compatibility_proven = false")
    click.echo("state_machine_validated = false")
    click.echo("device_execution_proven = false")
    click.echo("physical_origin_proven = false")
    click.echo("\n[frames]")
    for kind in ("CNXN", "AUTH", "OPEN", "OKAY", "CLSE", "WRTE"):
        click.echo(f"{kind} = {sum(frame.kind == kind for frame in result.frames)}")


@adb.command("match-open")
@click.option("--client", type=click.Path(path_type=Path), required=True)
@click.option("--client-sha256", required=True)
@click.option("--server", type=click.Path(path_type=Path), required=True)
@click.option("--server-sha256", required=True)
@click.option("--payload-sha256", required=True)
def match_command(
    client: Path, client_sha256: str, server: Path, server_sha256: str, payload_sha256: str
) -> None:
    """Find one OPEN payload and matching stream-ready replies in retained directions."""
    result = match_retained_streams(client, client_sha256, server, server_sha256, payload_sha256)
    click.echo('schema_version = "mho-adb.ready-report/1"')
    click.echo('checksum_profile = "additive-required/1"')
    if isinstance(result, AdbInputRejected):
        render_failure(result)
        return
    if isinstance(result, AdbMatchBlocked):
        click.echo(f'stage = "{result.side}"')
        render_failure(result.cause)
        return
    click.echo(f'client_sha256 = "{result.client_sha256}"')
    click.echo(f'server_sha256 = "{result.server_sha256}"')
    click.echo(f'payload_sha256 = "{result.payload_sha256}"')
    click.echo("total_order_proven = false")
    click.echo("tcp_delivery_proven = false")
    click.echo("device_execution_proven = false")
    click.echo("physical_origin_proven = false")
    outcome = result.outcome
    if isinstance(outcome, StreamReadyRejected):
        click.echo('result = "rejected"')
        click.echo(f"code = {toml_string(outcome.issue.code)}")
        click.echo(f"message = {toml_string(outcome.issue.message)}")
        raise click.exceptions.Exit(1)
    if isinstance(outcome, StreamReadyMissing):
        click.echo('result = "missing"')
        click.echo(f'reason = "{outcome.reason}"')
        raise click.exceptions.Exit(1)
    click.echo('result = "matched"')
    click.echo(f"client_local_id = {outcome.client_local_id}")
    click.echo(f"server_local_id = {outcome.server_local_id}")
    click.echo(f"ready_frames = {len(outcome.ready_frames)}")
