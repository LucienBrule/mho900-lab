"""Content record comparisons with independent expected paths and change kinds."""

import hashlib

import pytest

from mho_evidence import (
    Artifact,
    ArtifactPath,
    DeltaRejected,
    FileAdded,
    FileModified,
    FileRemoved,
    InventoryDelta,
    InventoryDiffRequest,
    Sha256,
    compare_inventory,
)


def artifact(path: str, data: bytes) -> Artifact:
    return Artifact(
        path=ArtifactPath(path),
        sha256=Sha256(hashlib.sha256(data).hexdigest()),
        size_bytes=len(data),
    )


def test_named_changes_are_stably_ordered_and_keep_exact_records() -> None:
    before = (
        artifact("alpha", b"removed"),
        artifact("middle", b"old"),
        artifact("same", b"unchanged"),
    )
    after = (
        artifact("beta", b"added"),
        artifact("middle", b"new"),
        artifact("same", b"unchanged"),
        artifact("zeta", b"last"),
    )
    result = compare_inventory(InventoryDiffRequest(before=before, after=after))
    assert isinstance(result, InventoryDelta)
    assert result.changes == (
        FileRemoved(before=before[0]),
        FileAdded(after=after[0]),
        FileModified(before=before[1], after=after[1]),
        FileAdded(after=after[3]),
    )
    assert result.before_count == 3 and result.after_count == 4 and result.unchanged_count == 1
    assert result.rename_inference is False and result.metadata_compared is False
    assert result.persistence_proven is False and result.semantic_equivalence_proven is False
    assert [item.kind for item in result.changes] == ["removed", "added", "modified", "added"]


def test_same_content_at_new_path_is_remove_add_not_rename() -> None:
    before = artifact("old-name", b"same bytes")
    after = artifact("new-name", b"same bytes")
    result = compare_inventory(InventoryDiffRequest(before=(before,), after=(after,)))
    assert isinstance(result, InventoryDelta)
    assert result.changes == (FileAdded(after=after), FileRemoved(before=before))
    assert result.unchanged_count == 0


def test_empty_both_and_one_sided_inputs() -> None:
    empty = compare_inventory(InventoryDiffRequest(before=(), after=()))
    assert isinstance(empty, InventoryDelta)
    assert (
        empty.changes == ()
        and empty.before_count == empty.after_count == empty.unchanged_count == 0
    )
    value = artifact("empty-file", b"")
    added = compare_inventory(InventoryDiffRequest(before=(), after=(value,)))
    removed = compare_inventory(InventoryDiffRequest(before=(value,), after=()))
    assert isinstance(added, InventoryDelta) and added.changes == (FileAdded(after=value),)
    assert isinstance(removed, InventoryDelta) and removed.changes == (FileRemoved(before=value),)


def test_equal_digest_but_different_size_is_a_modified_record() -> None:
    before = artifact("same-path", b"four")
    after = Artifact(path=before.path, sha256=before.sha256, size_bytes=5)
    result = compare_inventory(InventoryDiffRequest(before=(before,), after=(after,)))
    assert isinstance(result, InventoryDelta)
    assert result.changes == (FileModified(before=before, after=after),)
    assert result.unchanged_count == 0


def test_equal_size_but_different_digest_is_modified() -> None:
    before = artifact("same-path", b"abcd")
    after = artifact("same-path", b"efgh")
    result = compare_inventory(InventoryDiffRequest(before=(before,), after=(after,)))
    assert isinstance(result, InventoryDelta)
    assert result.changes == (FileModified(before=before, after=after),)


@pytest.mark.parametrize("side", ["before", "after"])
@pytest.mark.parametrize("duplicate", [False, True])
def test_noncanonical_order_and_duplicates_reject_without_repair(
    side: str, duplicate: bool
) -> None:
    first = artifact("a", b"first")
    second = artifact("a" if duplicate else "b", b"second")
    invalid = (first, second) if duplicate else (second, first)
    request = InventoryDiffRequest(
        before=invalid if side == "before" else (), after=invalid if side == "after" else ()
    )
    result = compare_inventory(request)
    assert isinstance(result, DeltaRejected)
    assert result.issue.code == "inventory-order"
    assert side in result.issue.message
    assert request.before == (invalid if side == "before" else ())
    assert request.after == (invalid if side == "after" else ())


def test_case_and_unicode_are_not_silently_normalized() -> None:
    before = (artifact("A", b"same"), artifact("e\u0301", b"same"))
    after = (artifact("a", b"same"), artifact("\u00e9", b"same"))
    result = compare_inventory(InventoryDiffRequest(before=before, after=after))
    assert isinstance(result, InventoryDelta)
    assert result.changes == (
        FileRemoved(before=before[0]),
        FileAdded(after=after[0]),
        FileRemoved(before=before[1]),
        FileAdded(after=after[1]),
    )


@pytest.mark.parametrize("path", ["../outside", "/absolute", "a//b", "a/./b", "a\\b"])
def test_unchecked_noncanonical_artifact_values_reject(path: str) -> None:
    canonical = artifact("valid", b"value")
    invalid = Artifact.model_construct(
        path=ArtifactPath.model_construct(root=path),
        sha256=canonical.sha256,
        size_bytes=canonical.size_bytes,
    )
    result = compare_inventory(InventoryDiffRequest(before=(invalid,), after=()))
    assert isinstance(result, DeltaRejected) and result.issue.code == "inventory-value"
    assert path not in result.issue.message


def test_unchecked_negative_size_rejects() -> None:
    canonical = artifact("valid", b"value")
    invalid = Artifact.model_construct(path=canonical.path, sha256=canonical.sha256, size_bytes=-1)
    assert isinstance(
        compare_inventory(InventoryDiffRequest(before=(), after=(invalid,))), DeltaRejected
    )


def test_equal_distinct_objects_count_as_unchanged() -> None:
    before = artifact("same", b"bytes")
    after = artifact("same", b"bytes")
    assert before is not after
    result = compare_inventory(InventoryDiffRequest(before=(before,), after=(after,)))
    assert isinstance(result, InventoryDelta)
    assert result.changes == () and result.unchanged_count == 1


def test_digest_model_subclass_does_not_change_content_comparison() -> None:
    class DigestSubclass(Sha256):
        pass

    before = artifact("same", b"bytes")
    after = Artifact(
        path=before.path,
        sha256=DigestSubclass(before.sha256.root),
        size_bytes=before.size_bytes,
    )
    result = compare_inventory(InventoryDiffRequest(before=(before,), after=(after,)))
    assert isinstance(result, InventoryDelta)
    assert result.changes == () and result.unchanged_count == 1
