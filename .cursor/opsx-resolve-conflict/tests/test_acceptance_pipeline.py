"""Acceptance tests A–L для unified conflict pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))

from opsx_conflict.models import ResolutionClass
from opsx_conflict.partition import is_mixed_scope
from opsx_conflict.pipeline import run_go, run_preview


@pytest.mark.unit
def test_a_mixed_scope_partitions_not_blocked(mixed_scope_conflict_repo: Path) -> None:
    """A: process + product → partition, no BLOCKED_MIXED_SCOPE."""

    result = run_preview(mixed_scope_conflict_repo)
    assert result.status == "PREVIEW_READY"
    assert result.partitions
    assert is_mixed_scope(result.partitions)
    lanes = {p.lane.value for p in result.partitions}
    assert "process" in lanes
    assert "product" in lanes
    assert result.stop_reason == "mixed_scope_partitioned"


@pytest.mark.unit
def test_b_auto_safe_batch_without_owner(auto_safe_repo: Path) -> None:
    """B: AUTO_SAFE resolves without Owner."""

    preview = run_preview(auto_safe_repo)
    auto_items = [
        c for c in preview.classified
        if c.resolution_class in (ResolutionClass.AUTO_SAFE, ResolutionClass.AI_SEMANTIC)
    ]
    assert auto_items
    result = run_go(
        auto_safe_repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )
    assert result.status in ("RESOLVED_PENDING_VERIFICATION", "PAUSED", "VERIFIED_READY_FOR_CONTINUE")
    assert result.ledger


@pytest.mark.unit
def test_d_authority_conflict_owner_required(delete_modify_repo: Path) -> None:
    """D/E: delete/modify → OWNER_REQUIRED, no silent write."""

    preview = run_preview(delete_modify_repo)
    owner_items = [
        c for c in preview.classified
        if c.resolution_class == ResolutionClass.OWNER_REQUIRED
    ]
    assert owner_items
    result = run_go(delete_modify_repo, frozen_fingerprint=preview.fingerprint)
    assert result.status == "PAUSED"
    assert not result.staged_paths


@pytest.mark.unit
def test_g_partial_failure_no_pass(auto_safe_repo: Path) -> None:
    """G: wrong fingerprint → no PASS."""

    preview = run_preview(auto_safe_repo)
    result = run_go(auto_safe_repo, frozen_fingerprint="stale_fingerprint")
    assert result.status == "STALE_EXECUTION"
    assert result.stop_reason == "REPLAN_REQUIRED"


@pytest.mark.unit
def test_k_owner_aggregation(mixed_scope_conflict_repo: Path) -> None:
    """K: Owner decisions aggregated in packets."""

    preview = run_preview(mixed_scope_conflict_repo)
    owner_count = sum(
        1 for c in preview.classified
        if c.resolution_class == ResolutionClass.OWNER_REQUIRED
    )
    if owner_count:
        assert preview.owner_packets
        assert len(preview.owner_packets) <= owner_count


@pytest.mark.unit
def test_j_no_ready_while_unmerged_owner_pending(delete_modify_repo: Path) -> None:
    """J: READY impossible while owner pending."""

    preview = run_preview(delete_modify_repo)
    result = run_go(delete_modify_repo, frozen_fingerprint=preview.fingerprint)
    assert result.status != "VERIFIED_READY_FOR_CONTINUE"
