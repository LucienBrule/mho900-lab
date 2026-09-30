"""Pinned, uncompressed USTAR/GNU-USTAR regular-file inventory without extraction.

Directory names may have one terminal slash, treated as the tar type delimiter.
No other name normalization is performed. GNU extension fields, base-256 numbers,
links, PAX, sparse members and long-name records are outside this narrow profile.
"""

import hashlib
import os
from contextlib import suppress
from dataclasses import dataclass

from .api import EvidenceIssue
from .archive_models import ArchiveAccepted, ArchiveLimits, ArchiveRejected, ArchiveRequest
from .filesystem import EvidenceFailure, check_root_name, open_directory, read_file
from .manifest import Artifact, ArtifactPath, Sha256

BLOCK = 512
ZERO_BLOCK = bytes(BLOCK)


class ArchiveFailure(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.issue = EvidenceIssue(code=code, message=message)
        super().__init__(message)


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise ArchiveFailure(code, message)


def octal(raw: bytes, *, blank_allowed: bool = False) -> int:
    value = raw.rstrip(b"\0 ").lstrip(b" ")
    if not value and blank_allowed:
        return 0
    require(
        bool(value) and all(48 <= byte <= 55 for byte in value),
        "archive-number",
        "header numeric field is outside the octal profile",
    )
    return int(value, 8)


def string_field(raw: bytes) -> str:
    value, separator, padding = raw.partition(b"\0")
    require(not separator or not any(padding), "archive-header", "nonzero string-field padding")
    return value.decode("utf-8")


@dataclass(frozen=True)
class Header:
    path: ArtifactPath
    size: int
    directory: bool


def header(block: bytes, limits: ArchiveLimits) -> Header:
    checksum = octal(block[148:156])
    require(
        sum(block[:148]) + 8 * 32 + sum(block[156:]) == checksum,
        "archive-checksum",
        "tar header checksum does not match",
    )
    magic = block[257:265]
    require(
        magic in (b"ustar\x0000", b"ustar  \x00"),
        "archive-format",
        "only explicit USTAR or GNU-USTAR headers are supported",
    )
    kind = block[156:157]
    require(
        kind in (b"0", b"\0", b"5"),
        "archive-member-type",
        "only ordinary regular files and directories are supported",
    )
    require(not any(block[157:257]), "archive-link", "link target field must be empty")
    # Validate numeric framing even for metadata not represented in the inventory.
    octal(block[100:108])
    octal(block[108:116])
    octal(block[116:124])
    octal(block[136:148])
    size = octal(block[124:136])
    require(
        octal(block[329:337], blank_allowed=True) == 0
        and octal(block[337:345], blank_allowed=True) == 0,
        "archive-device",
        "device fields must be zero for ordinary members",
    )
    string_field(block[265:297])
    string_field(block[297:329])
    name = string_field(block[:100])
    if magic == b"ustar\x0000":
        prefix = string_field(block[345:500])
        require(not any(block[500:512]), "archive-header", "reserved header bytes must be zero")
        if prefix:
            name = prefix + "/" + name
    else:
        require(not any(block[345:512]), "archive-extension", "GNU extension fields unsupported")
    directory = kind == b"5"
    if directory and name.endswith("/"):
        name = name[:-1]
    path = ArtifactPath(name)
    require(
        len(name.split("/")) <= limits.max_path_depth,
        "archive-depth-limit",
        "member path exceeds configured depth",
    )
    require(
        not directory or size == 0,
        "archive-directory-size",
        "directory member must have zero data extent",
    )
    require(
        size <= limits.max_member_bytes,
        "archive-member-limit",
        "member payload exceeds configured limit",
    )
    return Header(path=path, size=size, directory=directory)


def inventory(raw: bytes, limits: ArchiveLimits, digest: str) -> ArchiveAccepted:
    require(
        len(raw) >= 2 * BLOCK and len(raw) % BLOCK == 0,
        "archive-framing",
        "archive must contain complete blocks and a two-block terminator",
    )
    artifacts: list[Artifact] = []
    directories: list[ArtifactPath] = []
    seen: set[str] = set()
    files: set[str] = set()
    required_directories: set[str] = set()
    position = 0
    total = 0
    terminated = False
    while position < len(raw):
        block = raw[position : position + BLOCK]
        if block == ZERO_BLOCK:
            require(
                position + 2 * BLOCK <= len(raw)
                and raw[position + BLOCK : position + 2 * BLOCK] == ZERO_BLOCK,
                "archive-terminator",
                "two consecutive zero terminator blocks required",
            )
            require(not any(raw[position:]), "archive-trailing", "nonzero data after terminator")
            terminated = True
            break
        require(
            len(seen) < limits.max_members,
            "archive-member-count",
            "member count exceeds configured limit",
        )
        entry = header(block, limits)
        name = entry.path.root
        require(name not in seen, "archive-duplicate", "duplicate logical member name")
        ancestors = name.split("/")[:-1]
        parent = ""
        for component in ancestors:
            parent = component if not parent else parent + "/" + component
            require(parent not in files, "archive-conflict", "file is ancestor of another member")
            required_directories.add(parent)
        require(
            entry.directory or name not in required_directories,
            "archive-conflict",
            "file conflicts with a required parent directory",
        )
        seen.add(name)
        total += entry.size
        require(
            total <= limits.max_total_payload_bytes,
            "archive-total-limit",
            "total payload exceeds configured limit",
        )
        data_start = position + BLOCK
        data_end = data_start + entry.size
        next_header = data_start + ((entry.size + BLOCK - 1) // BLOCK) * BLOCK
        require(next_header <= len(raw), "archive-truncated", "member payload extent is truncated")
        require(
            not any(raw[data_end:next_header]),
            "archive-padding",
            "member payload padding must be zero",
        )
        if entry.directory:
            directories.append(entry.path)
        else:
            files.add(name)
            artifacts.append(
                Artifact(
                    path=entry.path,
                    sha256=Sha256(hashlib.sha256(raw[data_start:data_end]).hexdigest()),
                    size_bytes=entry.size,
                )
            )
        position = next_header
    require(terminated, "archive-terminator", "archive lacks two zero terminator blocks")
    return ArchiveAccepted(
        source_sha256=digest,
        source_bytes=len(raw),
        artifacts=tuple(sorted(artifacts, key=lambda item: item.path.root)),
        directories=tuple(sorted(directories, key=lambda item: item.root)),
        member_count=len(seen),
    )


def inspect_archive(request: ArchiveRequest) -> ArchiveAccepted | ArchiveRejected:
    """Read one bounded unchanged regular file and require its externally pinned hash."""
    parent: int | None = None
    try:
        parent = open_directory(request.path.parent)
        raw = read_file(parent, request.path.name, "archive", request.limits.max_source_bytes)
        check_root_name(parent, request.path.parent)
        descriptor = parent
        parent = None
        os.close(descriptor)
        digest = hashlib.sha256(raw).hexdigest()
        require(
            digest == request.expected_sha256.root,
            "archive-source-pin",
            "archive source does not match caller pin",
        )
        return inventory(raw, request.limits, digest)
    except ArchiveFailure as error:
        return ArchiveRejected(error.issue)
    except (OSError, ValueError, EvidenceFailure, NotImplementedError):
        return ArchiveRejected(EvidenceIssue("archive-input", "archive input or header rejected"))
    finally:
        if parent is not None:
            with suppress(OSError):
                os.close(parent)
