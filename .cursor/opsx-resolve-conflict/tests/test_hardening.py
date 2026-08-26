"""Hardening tests: terminal gate (M), AI_SEMANTIC authority (N), logical (F), recovery (G)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))

from opsx_conflict.classify import classify_path
from opsx_conflict.models import AuthorityLane, ConflictKind, PartitionedPath, ResolutionClass, UnmergedPath
from opsx_conflict.pipeline import run_go, run_preview


@pytest.mark.unit
def test_m_resolved_without_verification_not_verified_ready(auto_safe_repo: Path) -> None:
    """M: resolved candidate without external verification ≠ VERIFIED_READY."""

    preview = run_preview(auto_safe_repo)
    result = run_go(
        auto_safe_repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )
    assert result.status == "RESOLVED_PENDING_VERIFICATION"
    assert result.status != "VERIFIED_READY_FOR_CONTINUE"
    assert result.verification_handoff is not None
    assert result.candidate_identity


@pytest.mark.unit
def test_m_verified_ready_with_synthetic_evidence(auto_safe_repo: Path) -> None:
    """M: synthetic valid evidence packet → VERIFIED_READY_FOR_CONTINUE."""

    preview = run_preview(auto_safe_repo)
    result = run_go(
        auto_safe_repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )
    evidence = {
        "candidate_identity": result.candidate_identity,
        "completed_classes": [
            "RESOLUTION_VERIFICATION",
            "CANDIDATE_BINDING",
            "PYTHON_SYNTAX",
        ],
    }
    verified = run_go(
        auto_safe_repo,
        frozen_fingerprint=result.fingerprint,
        lanes=["process"],
        resume_run_id=result.run_id,
        verification_evidence=evidence,
    )
    assert verified.status == "VERIFIED_READY_FOR_CONTINUE"


@pytest.mark.unit
def test_n_parseable_without_authority_owner_required(empty_repo: Path) -> None:
    """N-A: parseable intents, no authority → OWNER_REQUIRED."""

    part = PartitionedPath(
        path="app/no_auth.py",
        lane=AuthorityLane.PRODUCT,
        inventory_class="C_OUT_OF_SCOPE",
        unmerged=UnmergedPath(path="app/no_auth.py", kind=ConflictKind.BOTH_MODIFIED),
    )
    c = classify_path(
        part,
        None,
        "def foo_a():\n    return 'a'\n    extra_a\n    more_a\n",
        "def foo_b():\n    return 'b'\n    extra_b\n    more_b\n",
        None,
        repo_root=empty_repo,
    )
    assert c.resolution_class == ResolutionClass.OWNER_REQUIRED
    assert "ai_semantic_downgrade" in c.reason


@pytest.mark.unit
def test_n_authority_proven_ai_semantic_allowed(empty_repo: Path) -> None:
    """N-B: authority + compatible intents → AI_SEMANTIC."""

    part = PartitionedPath(
        path=".opsx/authorized.py",
        lane=AuthorityLane.PROCESS,
        inventory_class="A_IN_SCOPE",
        unmerged=UnmergedPath(path=".opsx/authorized.py", kind=ConflictKind.BOTH_MODIFIED),
    )
    side_a = "# OPSX_AUTHORITY: invariant_keep\nbody_a_line1\nbody_a_line2\nunique_a\n"
    side_b = "# OPSX_AUTHORITY: invariant_keep\nbody_b_line1\nbody_b_line2\nunique_b\n"
    c = classify_path(part, None, side_a, side_b, None, repo_root=empty_repo)
    assert c.resolution_class == ResolutionClass.AI_SEMANTIC


@pytest.mark.unit
def test_n_new_business_choice_owner_required(empty_repo: Path) -> None:
    """N-C: conflicting business choice → OWNER_REQUIRED."""

    part = PartitionedPath(
        path=".opsx/choice.py",
        lane=AuthorityLane.PROCESS,
        inventory_class="A_IN_SCOPE",
        unmerged=UnmergedPath(path=".opsx/choice.py", kind=ConflictKind.BOTH_MODIFIED),
    )
    side_a = "# OPSX_AUTHORITY: inv\n# BUSINESS_CHOICE: option_a\nline_a1\nline_a2\n"
    side_b = "# OPSX_AUTHORITY: inv\n# BUSINESS_CHOICE: option_b\nline_b1\nline_b2\n"
    c = classify_path(part, None, side_a, side_b, None, repo_root=empty_repo)
    assert c.resolution_class == ResolutionClass.OWNER_REQUIRED


@pytest.mark.unit
def test_f_logical_conflict_without_markers(logical_conflict_repo: Path) -> None:
    """F: clean textual merge + bounded logical incompatibility."""

    preview = run_preview(logical_conflict_repo)
    result = run_go(
        logical_conflict_repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["product"],
    )
    assert result.status == "FAILED"
    assert "logical:" in (result.stop_reason or "")


@pytest.mark.unit
def test_g_mid_write_fault_and_resume(dual_write_repo: Path) -> None:
    """G: fault after first write → FAILED; resume completes deterministically."""

    preview = run_preview(dual_write_repo)
    first_path = ".opsx/file_a.txt"
    second_path = ".opsx/file_b.txt"

    failed = run_go(
        dual_write_repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
        write_fault_at_path=second_path,
    )
    assert failed.status == "FAILED"
    assert failed.execution_state is not None
    assert first_path in failed.execution_state.get("completed_paths", [])
    assert second_path not in failed.execution_state.get("completed_paths", [])
    assert failed.status != "VERIFIED_READY_FOR_CONTINUE"

    resumed = run_go(
        dual_write_repo,
        resume_run_id=failed.run_id,
        lanes=["process"],
    )
    assert resumed.status == "RESOLVED_PENDING_VERIFICATION"
    assert (dual_write_repo / second_path).is_file()
    assert resumed.ledger or resumed.execution_state
