"""Click presentation for explicit offline evidence operations."""

from pathlib import Path
from typing import assert_never

import click

from mho_evidence import (
    EvidenceIssue,
    SealCreated,
    SealPublishedUncertain,
    SealRejected,
    VerificationAccepted,
    VerificationRejected,
)
from mho_lab_cli.evidence_delegate import seal_evidence, verify_evidence


def show_issue(issue: EvidenceIssue) -> None:
    location = f" ({issue.path})" if issue.path is not None else ""
    click.echo(f"{issue.code}: {issue.message}{location}", err=True)


@click.group()
def evidence() -> None:
    """Seal or verify an exact inventory of local regular files."""


@evidence.command("seal")
@click.argument("root", type=click.Path(path_type=Path))
@click.option("--output", type=click.Path(path_type=Path), required=True)
@click.option("--allow-empty", is_flag=True, help="Explicitly permit an empty inventory.")
def seal_command(root: Path, output: Path, allow_empty: bool) -> None:
    """Create a new TOML manifest outside ROOT without overwriting files."""
    result = seal_evidence(root, output, allow_empty=allow_empty)
    match result:
        case SealCreated():
            click.echo(f"Manifest created: {result.output}")
            click.echo(f"SHA-256: {result.manifest_sha256}")
            click.echo(f"Artifacts: {result.artifact_count}; bytes: {result.total_bytes}")
        case SealRejected():
            show_issue(result.issue)
            raise click.exceptions.Exit(1)
        case SealPublishedUncertain():
            click.echo(f"Manifest publication requires inspection: {result.output}", err=True)
            click.echo(f"Intended manifest SHA-256: {result.manifest_sha256}", err=True)
            show_issue(result.issue)
            raise click.exceptions.Exit(3)
        case _:
            assert_never(result)


@evidence.command("verify")
@click.argument("root", type=click.Path(path_type=Path))
@click.option("--manifest", type=click.Path(path_type=Path), required=True)
def verify_command(root: Path, manifest: Path) -> None:
    """Verify content and exact inventory against a preserved manifest."""
    result = verify_evidence(root, manifest)
    match result:
        case VerificationAccepted():
            click.echo(f"Verified SHA-256: {result.manifest_sha256}")
            click.echo(f"Artifacts: {result.artifact_count}; bytes: {result.total_bytes}")
        case VerificationRejected():
            show_issue(result.issue)
            raise click.exceptions.Exit(1)
        case _:
            assert_never(result)
