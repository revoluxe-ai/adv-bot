from __future__ import annotations

from opsx_conflict.runtime import StageEntry, classify_conflict


def entry(stage: int, mode: str = "100644") -> StageEntry:
    return StageEntry(mode=mode, oid=f"oid{stage}", stage=stage, path="x")


def test_conflict_taxonomy_core_cells() -> None:
    assert classify_conflict("x", [entry(2), entry(3)]) == "add/add"
    assert classify_conflict("x", [entry(1), entry(2)]) == "modify/delete"
    assert classify_conflict("x", [entry(1), entry(3)]) == "delete/modify"
    assert classify_conflict("x", [entry(1), entry(2), entry(3)]) == "modify/modify"
    assert (
        classify_conflict(
            "x",
            [entry(1, "100644"), entry(2, "100755"), entry(3, "100644")],
        )
        == "file-mode-or-type"
    )
