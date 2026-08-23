"""Tests для classify, resolve, verify helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))

from opsx_conflict.classify import classify_path
from opsx_conflict.models import (
    AuthorityLane,
    ConflictKind,
    PartitionedPath,
    ResolutionClass,
    UnmergedPath,
)
from opsx_conflict.resolve_text import resolve_text, _synthesis_union


@pytest.mark.unit
def test_synthesis_union_preserves_both() -> None:
    a = "header\nfunc_a\n"
    b = "header\nfunc_b\n"
    merged = _synthesis_union(a, b)
    assert "func_a" in merged or "func_b" in merged


@pytest.mark.unit
def test_classify_delete_modify_owner_required() -> None:
    part = PartitionedPath(
        path=".opsx/x.txt",
        lane=AuthorityLane.PROCESS,
        inventory_class="A_IN_SCOPE",
        unmerged=UnmergedPath(path=".opsx/x.txt", kind=ConflictKind.DELETED_BY_THEM),
    )
    c = classify_path(part, None, "a", None, None)
    assert c.resolution_class == ResolutionClass.OWNER_REQUIRED


@pytest.mark.unit
def test_resolve_with_owner_choice() -> None:
    from opsx_conflict.models import ClassifiedConflict, ResolutionKind

    c = ClassifiedConflict(
        conflict_id="x",
        cluster_id=None,
        path=".opsx/x.txt",
        lane=AuthorityLane.PROCESS,
        resolution_class=ResolutionClass.OWNER_REQUIRED,
        resolution_kind=ResolutionKind.UNRESOLVED,
        reason="delete",
    )
    text, kind = resolve_text(c, "side_a", "side_b", None, owner_choice="side_a")
    assert text == "side_a"
    assert kind.value == "KEEP_SIDE_A"
