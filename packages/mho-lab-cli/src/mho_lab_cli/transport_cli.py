"""Present captured stream evidence without emitting private transcript bytes."""

import hashlib
from ipaddress import AddressValueError, IPv4Address
from pathlib import Path
from typing import assert_never

import click

from mho_lab_cli.transport_delegate import inspect_transcript
from mho_transport import Endpoint, TranscriptAccepted, TranscriptRejected


def endpoint(address: str, port: int, option: str) -> Endpoint:
    try:
        parsed = IPv4Address(address)
    except AddressValueError as error:
        raise click.BadParameter("expected a literal IPv4 address", param_hint=option) from error
    return Endpoint(address=parsed, port=port)


@click.group()
def transport() -> None:
    """Inspect preserved packet captures without network access."""


@transport.command("inspect")
@click.argument("capture", type=click.Path(path_type=Path))
@click.option("--client-address", required=True)
@click.option("--client-port", type=click.IntRange(1, 65535), required=True)
@click.option("--server-address", required=True)
@click.option("--server-port", type=click.IntRange(1, 65535), required=True)
def inspect_command(
    capture: Path,
    client_address: str,
    client_port: int,
    server_address: str,
    server_port: int,
) -> None:
    """Report TOML counts and digests for one explicitly selected TCP connection."""
    client = endpoint(client_address, client_port, "--client-address")
    server = endpoint(server_address, server_port, "--server-address")
    result = inspect_transcript(capture, client, server)
    match result:
        case TranscriptAccepted():
            metadata = result.metadata
            click.echo('schema_version = "mho-transport.summary/1"')
            click.echo('result = "accepted"')
            click.echo(f'capture_sha256 = "{metadata.capture_sha256}"')
            click.echo(f"capture_bytes = {metadata.capture_bytes}")
            click.echo(f"capture_frames = {metadata.capture_frames}")
            click.echo(f"selected_tcp_frames = {metadata.selected_tcp_frames}")
            click.echo(f"ignored_frames = {metadata.ignored_frames}")
            click.echo(f"retransmitted_bytes = {metadata.retransmitted_bytes}")
            click.echo(f"request_bytes = {len(result.request)}")
            click.echo(f"reply_bytes = {len(result.reply)}")
            click.echo(f'request_sha256 = "{hashlib.sha256(result.request).hexdigest()}"')
            click.echo(f'reply_sha256 = "{hashlib.sha256(result.reply).hexdigest()}"')
            click.echo("checksums_verified = false")
            click.echo("peer_delivery_proven = false")
            click.echo("device_execution_proven = false")
            click.echo("kernel_drop_statistics_available = false")
        case TranscriptRejected():
            issue = result.issue
            location = f" (frame {issue.frame_number})" if issue.frame_number is not None else ""
            click.echo(f"{issue.code}: {issue.message}{location}", err=True)
            raise click.exceptions.Exit(1)
        case _:
            assert_never(result)
