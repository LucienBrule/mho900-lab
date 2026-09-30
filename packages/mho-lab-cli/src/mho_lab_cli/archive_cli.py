"""TOML presentation of archive content hashes; never file payloads."""

from pathlib import Path

import click

from mho_evidence import Artifact, FileAdded, FileModified, FileRemoved
from mho_lab_cli.archive_delegate import (
    ArchiveOperationRejected,
    compare_archives,
    inspect_retained_archive,
)
from mho_lab_cli.scpi_cli import toml_string


def reject(result: ArchiveOperationRejected) -> None:
    click.echo('result = "rejected"')
    click.echo(f"stage = {toml_string(result.stage)}")
    click.echo(f"code = {toml_string(result.code)}")
    click.echo(f"message = {toml_string(result.message)}")
    raise click.exceptions.Exit(1)


def render_artifact(artifact: Artifact) -> None:
    click.echo(f"path = {toml_string(artifact.path.root)}")
    click.echo(f'sha256 = "{artifact.sha256.root}"')
    click.echo(f"size_bytes = {artifact.size_bytes}")


@click.group()
def archive() -> None:
    """Inspect pinned logical archives without extracting their files."""


@archive.command("inspect")
@click.argument("path", type=click.Path(path_type=Path))
@click.option("--expected-sha256", required=True)
def inspect_command(path: Path, expected_sha256: str) -> None:
    """Inventory one narrow uncompressed tar archive as content hashes."""
    result = inspect_retained_archive(path, expected_sha256)
    click.echo('schema_version = "mho-evidence.archive-inventory/1"')
    if isinstance(result, ArchiveOperationRejected):
        reject(result)
        return
    click.echo('result = "accepted"')
    click.echo(f'source_sha256 = "{result.source_sha256}"')
    click.echo(f"source_bytes = {result.source_bytes}")
    click.echo(f"member_count = {result.member_count}")
    click.echo(f"file_count = {len(result.artifacts)}")
    click.echo(f"directory_count = {len(result.directories)}")
    click.echo("extraction_performed = false")
    click.echo("restoration_fidelity_proven = false")
    for artifact in result.artifacts:
        click.echo("\n[[files]]")
        render_artifact(artifact)


@archive.command("diff")
@click.option("--before", type=click.Path(path_type=Path), required=True)
@click.option("--before-sha256", required=True)
@click.option("--after", type=click.Path(path_type=Path), required=True)
@click.option("--after-sha256", required=True)
def diff_command(before: Path, before_sha256: str, after: Path, after_sha256: str) -> None:
    """Compare regular-file contents; do not infer renames, meaning, or persistence."""
    result = compare_archives(before, before_sha256, after, after_sha256)
    click.echo('schema_version = "mho-evidence.archive-delta/1"')
    if isinstance(result, ArchiveOperationRejected):
        reject(result)
        return
    click.echo('result = "accepted"')
    click.echo(f'before_source_sha256 = "{result.before.source_sha256}"')
    click.echo(f'after_source_sha256 = "{result.after.source_sha256}"')
    click.echo(f"before_files = {result.delta.before_count}")
    click.echo(f"after_files = {result.delta.after_count}")
    click.echo(f"unchanged_files = {result.delta.unchanged_count}")
    click.echo(f"changed_files = {len(result.delta.changes)}")
    click.echo("directory_changes_included = false")
    click.echo("rename_inference_performed = false")
    click.echo("semantic_equivalence_proven = false")
    for change in result.delta.changes:
        click.echo("\n[[changes]]")
        click.echo(f'kind = "{change.kind}"')
        if isinstance(change, (FileRemoved, FileModified)):
            click.echo("[changes.before]")
            render_artifact(change.before)
        if isinstance(change, (FileAdded, FileModified)):
            click.echo("[changes.after]")
            render_artifact(change.after)
