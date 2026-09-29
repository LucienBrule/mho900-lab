"""Descriptor-relative checks detect observed changes, not every filesystem race."""

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .api import EvidenceIssue
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


def read_file(parent: int, name: str, logical: str) -> bytes:
    """Read a manifest with the same no-link/type/change checks as artifacts."""
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        before = FileState.read(os.fstat(descriptor))
        if not stat.S_ISREG(before.mode):
            reject("unsupported-entry", "only regular files are supported", logical)
        chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            chunks.append(chunk)
        data = b"".join(chunks)
        after = FileState.read(os.fstat(descriptor))
        named = FileState.read(os.stat(name, dir_fd=parent, follow_symlinks=False))
        if before != after or before != named or len(data) != before.size:
            reject("observed-change", "file changed while being read", logical)
        return data
    finally:
        os.close(descriptor)


def hash_file(parent: int, name: str, logical: str, expected: FileState) -> Artifact:
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        before = FileState.read(os.fstat(descriptor))
        if not stat.S_ISREG(before.mode) or before != expected:
            reject("observed-change", "artifact identity changed before hashing", logical)
        digest = hashlib.sha256()
        size = 0
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
        after = FileState.read(os.fstat(descriptor))
        named = FileState.read(os.stat(name, dir_fd=parent, follow_symlinks=False))
        if before != after or before != named or size != before.size:
            reject("observed-change", "artifact changed while hashing", logical)
        return Artifact(
            path=ArtifactPath(logical), sha256=Sha256(digest.hexdigest()), size_bytes=size
        )
    finally:
        os.close(descriptor)


def scan(root: int, *, hash_contents: bool) -> Inventory:
    artifacts: list[Artifact] = []
    entries: list[ObservedEntry] = []

    def visit(parent: int, prefix: str) -> None:
        before = FileState.read(os.fstat(parent))
        with os.scandir(parent) as listing:
            names = sorted(entry.name for entry in listing)
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
                    visit(child, logical + "/")
                finally:
                    os.close(child)
            elif stat.S_ISREG(state.mode):
                if hash_contents:
                    artifacts.append(hash_file(parent, name, logical, state))
            else:
                reject("unsupported-entry", "symlinks and special files are rejected", logical)
        if before != FileState.read(os.fstat(parent)):
            reject("observed-change", "directory changed during inventory", prefix or ".")

    visit(root, "")
    return Inventory(
        artifacts=tuple(sorted(artifacts, key=lambda item: item.path.root)),
        entries=tuple(sorted(entries, key=lambda item: item.path)),
    )


def inventory(root: int) -> Inventory:
    first = scan(root, hash_contents=True)
    second = scan(root, hash_contents=False)
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
