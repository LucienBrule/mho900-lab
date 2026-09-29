"""Offline sealing and independent verification; no atomic snapshot claim."""

import hashlib
import os
import uuid
from contextlib import suppress
from pathlib import Path

from .api import (
    EvidenceIssue,
    SealCreated,
    SealPublishedUncertain,
    SealRejected,
    SealRequest,
    VerificationAccepted,
    VerificationRejected,
    VerifyRequest,
)
from .filesystem import (
    EvidenceFailure,
    absolute,
    check_root_name,
    inventory,
    open_directory,
    read_file,
    reject,
    scan,
)
from .manifest import ManifestV1, dump_manifest, load_manifest


def outside(root: Path, artifact: Path) -> None:
    if absolute(artifact).is_relative_to(absolute(root)):
        reject("output-within-root", "manifest must be outside the evidence root")


def failure(error: OSError | ValueError | EvidenceFailure | NotImplementedError) -> EvidenceIssue:
    if isinstance(error, EvidenceFailure):
        return error.issue
    if isinstance(error, FileExistsError):
        return EvidenceIssue(code="destination-exists", message="destination already exists")
    if isinstance(error, ValueError):
        return EvidenceIssue(code="invalid-manifest-or-path", message=str(error))
    return EvidenceIssue(code="filesystem-error", message=str(error))


def seal(request: SealRequest) -> SealCreated | SealRejected | SealPublishedUncertain:
    """Inventory regular files and publish a new external manifest without replacement.

    A published-uncertain outcome means the output link was created, but a later
    operation failed. Callers must inspect that output, never blindly retry or
    overwrite it. This is not a claim of atomic acquisition or storage durability.
    """
    root_fd: int | None = None
    parent_fd: int | None = None
    temporary: str | None = None
    published = False
    digest = ""
    try:
        outside(request.root, request.output)
        root_fd = open_directory(request.root)
        parent_fd = open_directory(request.output.parent)
        try:
            os.stat(request.output.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            reject("destination-exists", "destination already exists")
        observed = inventory(root_fd)
        if not observed.artifacts and not request.allow_empty:
            reject("empty-inventory", "empty root requires explicit allow_empty")
        manifest = ManifestV1(
            schema_version="mho-evidence.manifest/1",
            inventory="recursive-regular-files",
            artifacts=observed.artifacts,
            empty_allowed=request.allow_empty,
        )
        encoded = dump_manifest(manifest)
        digest = hashlib.sha256(encoded).hexdigest()
        temporary = ".mho-evidence-" + uuid.uuid4().hex + ".tmp"
        descriptor = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent_fd
        )
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if scan(root_fd, hash_contents=False).entries != observed.entries:
            reject("observed-change", "inventory changed before publication")
        check_root_name(root_fd, request.root)
        check_root_name(parent_fd, request.output.parent)
        os.link(
            temporary,
            request.output.name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
            follow_symlinks=False,
        )
        published = True
        os.unlink(temporary, dir_fd=parent_fd)
        temporary = None
        os.fsync(parent_fd)
        if read_file(parent_fd, request.output.name, "published manifest") != encoded:
            reject("observed-change", "published manifest differs from the encoded inventory")
        check_root_name(parent_fd, request.output.parent)
        descriptor = parent_fd
        parent_fd = None
        os.close(descriptor)
        descriptor = root_fd
        root_fd = None
        os.close(descriptor)
        return SealCreated(
            output=request.output,
            manifest_sha256=digest,
            artifact_count=len(manifest.artifacts),
            total_bytes=sum(artifact.size_bytes for artifact in manifest.artifacts),
        )
    except (OSError, ValueError, EvidenceFailure, NotImplementedError) as error:
        issue = failure(error)
        if published:
            return SealPublishedUncertain(
                output=request.output, manifest_sha256=digest, issue=issue
            )
        return SealRejected(issue=issue)
    finally:
        # Cleanup never unlinks the published output. An orphan temp can remain on
        # an I/O failure; it is not a seal and must not be mistaken for publication.
        if temporary is not None and parent_fd is not None:
            with suppress(OSError):
                os.unlink(temporary, dir_fd=parent_fd)
        if parent_fd is not None:
            with suppress(OSError):
                os.close(parent_fd)
        if root_fd is not None:
            with suppress(OSError):
                os.close(root_fd)


def verify(request: VerifyRequest) -> VerificationAccepted | VerificationRejected:
    """Validate the TOML edge and independently rescan exact regular-file inventory."""
    root_fd: int | None = None
    parent_fd: int | None = None
    try:
        outside(request.root, request.manifest)
        parent_fd = open_directory(request.manifest.parent)
        maximum = request.limits.max_manifest_bytes if request.limits is not None else None
        encoded = read_file(parent_fd, request.manifest.name, "manifest", maximum)
        manifest = load_manifest(encoded)
        root_fd = open_directory(request.root)
        observed = inventory(root_fd, request.limits)
        if observed.artifacts != manifest.artifacts:
            reject("inventory-mismatch", "artifact inventory, digest or byte count differs")
        check_root_name(root_fd, request.root)
        check_root_name(parent_fd, request.manifest.parent)
        if read_file(parent_fd, request.manifest.name, "manifest", maximum) != encoded:
            reject("observed-change", "manifest changed during verification")
        descriptor = parent_fd
        parent_fd = None
        os.close(descriptor)
        descriptor = root_fd
        root_fd = None
        os.close(descriptor)
        return VerificationAccepted(
            manifest_sha256=hashlib.sha256(encoded).hexdigest(),
            artifact_count=len(manifest.artifacts),
            total_bytes=sum(artifact.size_bytes for artifact in manifest.artifacts),
        )
    except (OSError, ValueError, EvidenceFailure, NotImplementedError) as error:
        return VerificationRejected(issue=failure(error))
    finally:
        if parent_fd is not None:
            with suppress(OSError):
                os.close(parent_fd)
        if root_fd is not None:
            with suppress(OSError):
                os.close(root_fd)
