"""Bounded regular-file reads; repeated observations do not establish atomicity."""

import os
import stat
from dataclasses import dataclass
from pathlib import Path


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
            value.st_dev,
            value.st_ino,
            value.st_mode,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )


def open_parent(path: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open("/", flags)
    try:
        for part in Path(os.path.abspath(path)).parent.parts[1:]:
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def read_bounded(path: Path, limit: int) -> bytes:
    parent = open_parent(path)
    descriptor: int | None = None
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
        before = FileState.read(os.fstat(descriptor))
        if not stat.S_ISREG(before.mode) or before.size > limit:
            raise ValueError("input type or size outside bounds")
        chunks: list[bytes] = []
        total = 0
        while chunk := os.read(descriptor, min(65536, limit + 1 - total)):
            total += len(chunk)
            if total > limit:
                raise ValueError("input exceeds bound")
            chunks.append(chunk)
        after = FileState.read(os.fstat(descriptor))
        named = FileState.read(os.stat(path.name, dir_fd=parent, follow_symlinks=False))
        # Rewalk the parent name so renamed/replaced ancestry is observed too.
        current_parent = open_parent(path)
        try:
            original = os.fstat(parent)
            current = os.fstat(current_parent)
            if original.st_dev != current.st_dev or original.st_ino != current.st_ino:
                raise ValueError("input parent changed")
        finally:
            os.close(current_parent)
        if before != after or before != named or total != before.size:
            raise ValueError("input changed")
        return b"".join(chunks)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)
