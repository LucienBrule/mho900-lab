"""Deterministic comparison of canonical path/size/digest inventories only."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import ValidationError

from .api import EvidenceIssue
from .manifest import Artifact, ArtifactPath, Sha256


@dataclass(frozen=True)
class InventoryDiffRequest:
    before: tuple[Artifact, ...]
    after: tuple[Artifact, ...]


@dataclass(frozen=True)
class FileAdded:
    after: Artifact
    kind: Literal["added"] = field(default="added", init=False)


@dataclass(frozen=True)
class FileRemoved:
    before: Artifact
    kind: Literal["removed"] = field(default="removed", init=False)


@dataclass(frozen=True)
class FileModified:
    before: Artifact
    after: Artifact
    kind: Literal["modified"] = field(default="modified", init=False)


type InventoryChange = FileAdded | FileRemoved | FileModified


@dataclass(frozen=True)
class InventoryDelta:
    changes: tuple[InventoryChange, ...]
    unchanged_count: int
    before_count: int
    after_count: int
    rename_inference: Literal[False] = False
    metadata_compared: Literal[False] = False
    semantic_equivalence_proven: Literal[False] = False
    persistence_proven: Literal[False] = False
    kind: Literal["inventory-delta"] = field(default="inventory-delta", init=False)


@dataclass(frozen=True)
class DeltaRejected:
    issue: EvidenceIssue
    kind: Literal["delta-rejected"] = field(default="delta-rejected", init=False)


def _validate_inventory(
    items: tuple[Artifact, ...], side: Literal["before", "after"]
) -> EvidenceIssue | None:
    previous: str | None = None
    for artifact in items:
        # Recheck the primitive fields even when a caller used an unchecked model
        # constructor. Do not sort, normalize paths, deduplicate or repair inputs.
        try:
            path = ArtifactPath(artifact.path.root)
            Artifact(path=path, sha256=Sha256(artifact.sha256.root), size_bytes=artifact.size_bytes)
        except (ValidationError, AttributeError, TypeError):
            return EvidenceIssue(
                "inventory-value", side + " inventory contains a noncanonical artifact"
            )
        if previous is not None and path.root <= previous:
            return EvidenceIssue(
                "inventory-order", side + " inventory paths must be sorted and unique"
            )
        previous = path.root
    return None


def compare_inventory(request: InventoryDiffRequest) -> InventoryDelta | DeltaRejected:
    """Compare supplied records, not files, timestamps, ownership or behavior.

    Equal digest and size at the same path count as unchanged. The input producer
    remains responsible for binding records to actual bytes. Matching content at
    different paths is reported as removal/addition, never inferred as a rename.
    """
    issue = _validate_inventory(request.before, "before")
    if issue is None:
        issue = _validate_inventory(request.after, "after")
    if issue is not None:
        return DeltaRejected(issue)
    changes: list[InventoryChange] = []
    unchanged = 0
    before_index = 0
    after_index = 0
    while before_index < len(request.before) and after_index < len(request.after):
        before = request.before[before_index]
        after = request.after[after_index]
        if before.path.root < after.path.root:
            changes.append(FileRemoved(before=before))
            before_index += 1
        elif before.path.root > after.path.root:
            changes.append(FileAdded(after=after))
            after_index += 1
        else:
            if before.sha256.root == after.sha256.root and before.size_bytes == after.size_bytes:
                unchanged += 1
            else:
                changes.append(FileModified(before=before, after=after))
            before_index += 1
            after_index += 1
    changes.extend(FileRemoved(before=artifact) for artifact in request.before[before_index:])
    changes.extend(FileAdded(after=artifact) for artifact in request.after[after_index:])
    return InventoryDelta(
        changes=tuple(changes),
        unchanged_count=unchanged,
        before_count=len(request.before),
        after_count=len(request.after),
    )
