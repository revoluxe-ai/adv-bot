"""Additional acceptance: synthesis, evidence, candidate binding."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))

from opsx_conflict.models import ResolutionClass
from opsx_conflict.pipeline import run_go, run_preview
from opsx_conflict.verify import verify_candidate


@pytest.mark.unit
def test_c_semantic_synthesis_in_ledger(auto_safe_repo: Path) -> None:
    """C: compatible sides merged, ledger records synthesis."""

    preview = run_preview(auto_safe_repo)
    result = run_go(
        auto_safe_repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )
    assert result.ledger
    entry = result.ledger[0]
    assert entry.resolution_kind in ("UNION", "SYNTHESIS")
    assert entry.result_worktree_sha256
    text = (auto_safe_repo / ".opsx" / "note.txt").read_text(encoding="utf-8")
    assert "a-only" in text or "b-only" in text


@pytest.mark.unit
def test_h_evidence_invalidated_after_semantic_write(auto_safe_repo: Path) -> None:
    """H: pre-resolution evidence not reused as terminal proof."""

    preview = run_preview(auto_safe_repo)
    pre_hash = hashlib.sha256(b"fake_pre_evidence").hexdigest()
    prior = {f"pre_resolution:{preview.classified[0].path}": pre_hash}
    result = run_go(
        auto_safe_repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )
    ok, refs, new_ev = verify_candidate(
        auto_safe_repo,
        preview.manifest,
        [c.path for c in preview.classified],
        result.ledger,
        prior,
    )
    assert ok
    assert f"pre_resolution:{preview.classified[0].path}" not in new_ev
    assert any("post_resolution:" in r for r in refs)


@pytest.mark.unit
def test_l_candidate_bound_to_worktree_hash(auto_safe_repo: Path) -> None:
    """L: verification binds to exact candidate bytes."""

    preview = run_preview(auto_safe_repo)
    result = run_go(
        auto_safe_repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )
    path = ".opsx/note.txt"
    actual = hashlib.sha256((auto_safe_repo / path).read_bytes()).hexdigest()
    assert result.ledger[0].result_worktree_sha256 == actual
