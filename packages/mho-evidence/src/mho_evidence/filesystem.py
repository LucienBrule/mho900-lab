"""Descriptor-relative checks detect observed changes, not every filesystem race."""

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .api import EvidenceIssue, VerificationLimits
from .manifest import Artifact, ArtifactPath, Sha256


class EvidenceFailure(Exception):
    def __init__(self, issue: EvidenceIssue) -> None:
        self.issue = issue
        super().__init__(issue.message)


def reject(code: str, message: str, path: str | None = None) -> None:
    raise EvidenceFailure(EvidenceIssue(code=code, message=message, path=path))


@dataclass(frozen=True)
class FileState:
    device: int
    inode: int
    mode: int
    size: int
    modified_ns: int
    changed_ns: int

    @classmethod
    def read(cls, value: os.stat_result) -> "FileState":
        return cls(
            device=value.st_dev,
            inode=value.st_ino,
            mode=value.st_mode,
            size=value.st_size,
            modified_ns=value.st_mtime_ns,
            changed_ns=value.st_ctime_ns,
        )


@dataclass(frozen=True)
class ObservedEntry:
    path: str
    state: FileState


@dataclass(frozen=True)
class Inventory:
    artifacts: tuple[Artifact, ...]
    entries: tuple[ObservedEntry, ...]


def absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def open_directory(path: Path) -> int:
    """Walk every existing parent without following symlinks; caller owns fd."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current = os.open("/", flags)
    try:
        for part in absolute(path).parts[1:]:
            child = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def read_file(parent: int, name: str, logical: str, max_bytes: int | None = None) -> bytes:
    """Read a manifest with the same no-link/type/change checks as artifacts."""
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        before = FileState.read(os.fstat(descriptor))
        if not stat.S_ISREG(before.mode):
            reject("unsupported-entry", "only regular files are supported", logical)
        if max_bytes is not None and before.size > max_bytes:
            reject("manifest-limit", "manifest exceeds configured byte limit")
        chunks: list[bytes] = []
        total = 0
        while chunk := os.read(
            descriptor,
            min(1024 * 1024, max_bytes + 1 - total) if max_bytes is not None else 1024 * 1024,
        ):
            total += len(chunk)
            if max_bytes is not None and total > max_bytes:
                reject("manifest-limit", "manifest grew beyond configured byte limit")
            chunks.append(chunk)
        data = b"".join(chunks)
        after = FileState.read(os.fstat(descriptor))
        named = FileState.read(os.stat(name, dir_fd=parent, follow_symlinks=False))
        if before != after or before != named or len(data) != before.size:
            reject("observed-change", "file changed while being read", logical)
        return data
    finally:
        os.close(descriptor)


def hash_file(
    parent: int, name: str, logical: str, expected: FileState, max_bytes: int | None = None
) -> Artifact:
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        before = FileState.read(os.fstat(descriptor))
        if not stat.S_ISREG(before.mode) or before != expected:
            reject("observed-change", "artifact identity changed before hashing", logical)
        digest = hashlib.sha256()
        size = 0
        while chunk := os.read(
            descriptor,
            min(1024 * 1024, max_bytes + 1 - size) if max_bytes is not None else 1024 * 1024,
        ):
            size += len(chunk)
            if max_bytes is not None and size > max_bytes:
                reject("inventory-byte-limit", "artifact grew beyond configured byte limit")
            digest.update(chunk)
        after = FileState.read(os.fstat(descriptor))
        named = FileState.read(os.stat(name, dir_fd=parent, follow_symlinks=False))
        if before != after or before != named or size != before.size:
            reject("observed-change", "artifact changed while hashing", logical)
        return Artifact(
            path=ArtifactPath(logical), sha256=Sha256(digest.hexdigest()), size_bytes=size
        )
    finally:
        os.close(descriptor)


def scan(root: int, *, hash_contents: bool, limits: VerificationLimits | None = None) -> Inventory:
    artifacts: list[Artifact] = []
    entries: list[ObservedEntry] = []

    total_bytes = 0
    discovered_entries = 0

    def visit(parent: int, prefix: str, depth: int) -> None:
        nonlocal total_bytes, discovered_entries
        if limits is not None and depth > limits.max_depth:
            reject("inventory-depth-limit", "directory depth exceeds configured limit")
        before = FileState.read(os.fstat(parent))
        with os.scandir(parent) as listing:
            names: list[str] = []
            for entry in listing:
                discovered_entries += 1
                if limits is not None and discovered_entries > limits.max_entries:
                    reject("inventory-entry-limit", "inventory exceeds configured entry limit")
                names.append(entry.name)
            names.sort()
        for name in names:
            logical = prefix + name
            ArtifactPath(logical)
            state = FileState.read(os.stat(name, dir_fd=parent, follow_symlinks=False))
            entries.append(ObservedEntry(path=logical, state=state))
            if stat.S_ISDIR(state.mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                try:
                    if FileState.read(os.fstat(child)) != state:
                        reject("observed-change", "directory identity changed", logical)
                    visit(child, logical + "/", depth + 1)
                finally:
                    os.close(child)
            elif stat.S_ISREG(state.mode):
                cap: int | None = None
                if limits is not None:
                    cap = min(limits.max_file_bytes, limits.max_total_bytes - total_bytes)
                    if state.size > cap:
                        reject("inventory-byte-limit", "inventory exceeds configured byte limit")
                total_bytes += state.size
                if hash_contents:
                    if limits is None:
                        artifacts.append(hash_file(parent, name, logical, state))
                    else:
                        artifacts.append(hash_file(parent, name, logical, state, cap))
            else:
                reject("unsupported-entry", "symlinks and special files are rejected", logical)
        if before != FileState.read(os.fstat(parent)):
            reject("observed-change", "directory changed during inventory", prefix or ".")

    visit(root, "", 0)
    return Inventory(
        artifacts=tuple(sorted(artifacts, key=lambda item: item.path.root)),
        entries=tuple(sorted(entries, key=lambda item: item.path)),
    )


def inventory(root: int, limits: VerificationLimits | None = None) -> Inventory:
    if limits is None:
        first = scan(root, hash_contents=True)
        second = scan(root, hash_contents=False)
    else:
        first = scan(root, hash_contents=True, limits=limits)
        second = scan(root, hash_contents=False, limits=limits)
    if first.entries != second.entries:
        reject("observed-change", "inventory changed between observations")
    return first


def check_root_name(root: int, path: Path) -> None:
    current = open_directory(path)
    try:
        if FileState.read(os.fstat(root)) != FileState.read(os.fstat(current)):
            reject("observed-change", "root path no longer identifies the observed directory")
    finally:
        os.close(current)
