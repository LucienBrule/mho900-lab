"""Bounded local-file input for application delegates; raw bytes remain external evidence."""

import os
import stat
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InputIdentity:
    device: int
    inode: int
    mode: int
    size: int
    modified_ns: int
    changed_ns: int

    @classmethod
    def read(cls, state: os.stat_result) -> "InputIdentity":
        return cls(
            device=state.st_dev,
            inode=state.st_ino,
            mode=state.st_mode,
            size=state.st_size,
            modified_ns=state.st_mtime_ns,
            changed_ns=state.st_ctime_ns,
        )


def read_bounded_regular(path: Path, limit_bytes: int) -> bytes:
    """Read one regular file without following its final link; reject observed changes."""
    if limit_bytes < 1:
        raise ValueError("input byte limit must be positive")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = InputIdentity.read(os.fstat(descriptor))
        if not stat.S_ISREG(before.mode) or before.size > limit_bytes:
            raise ValueError(f"input must be a regular file no larger than {limit_bytes} bytes")
        chunks: list[bytes] = []
        total = 0
        while chunk := os.read(descriptor, min(65536, limit_bytes + 1 - total)):
            chunks.append(chunk)
            total += len(chunk)
            if total > limit_bytes:
                raise ValueError("input grew beyond the byte limit")
        after = InputIdentity.read(os.fstat(descriptor))
        named = InputIdentity.read(os.stat(path, follow_symlinks=False))
        if before != after or before != named or total != before.size:
            raise ValueError("input changed during the read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)
