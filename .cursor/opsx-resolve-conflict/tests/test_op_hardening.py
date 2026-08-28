"""O/P correctness: full candidate identity and resume CAS."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))

from opsx_conflict.classify import classify_path
from opsx_conflict.git_capture import stage_file
from opsx_conflict.models import AuthorityLane, ConflictKind, PartitionedPath, ResolutionClass, UnmergedPath
from opsx_conflict.pipeline import run_go, run_preview


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True)


@pytest.mark.unit
def test_o_full_candidate_rejects_staged_non_conflict_mutation(
    conflict_plus_auto_merge_repo: Path,
) -> None:
    """O: mutating auto-merged staged path invalidates verification packet."""

    repo = conflict_plus_auto_merge_repo
    preview = run_preview(repo)
    resolved = run_go(
        repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )
    assert resolved.status == "RESOLVED_PENDING_VERIFICATION"
    handoff = resolved.verification_handoff
    assert handoff is not None
    assert "app/auto_merged.py" in handoff.get("staged_paths", [])

    evidence = {
        "candidate_identity": resolved.candidate_identity,
        "completed_classes": [
            "RESOLUTION_VERIFICATION",
            "CANDIDATE_BINDING",
        ],
    }
    accepted = run_go(
        repo,
        resume_run_id=resolved.run_id,
        lanes=["process"],
        verification_evidence=evidence,
    )
    assert accepted.status == "VERIFIED_READY_FOR_CONTINUE"

    auto_path = repo / "app" / "auto_merged.py"
    auto_path.write_text("line1\nline2 mutated\nline3\nline4 feature\n", encoding="utf-8")
    stage_file(repo, "app/auto_merged.py")

    rejected = run_go(
        repo,
        resume_run_id=resolved.run_id,
        lanes=["process"],
        verification_evidence=evidence,
    )
    assert rejected.status != "VERIFIED_READY_FOR_CONTINUE"
    assert rejected.status == "RESOLVED_PENDING_VERIFICATION"
    assert "verification_candidate_tree_mismatch" in (rejected.stop_reason or "")


@pytest.mark.unit
def test_o_same_staged_tree_accepts_packet(conflict_plus_auto_merge_repo: Path) -> None:
    """O: unchanged full staged tree keeps packet valid."""

    repo = conflict_plus_auto_merge_repo
    preview = run_preview(repo)
    resolved = run_go(
        repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )
    evidence = {
        "candidate_identity": resolved.candidate_identity,
        "completed_classes": [
            "RESOLUTION_VERIFICATION",
            "CANDIDATE_BINDING",
        ],
    }
    verified = run_go(
        repo,
        resume_run_id=resolved.run_id,
        lanes=["process"],
        verification_evidence=evidence,
    )
    assert verified.status == "VERIFIED_READY_FOR_CONTINUE"
    assert verified.candidate_identity == resolved.candidate_identity


@pytest.mark.unit
def test_p1_resume_rejects_completed_path_drift(dual_write_repo: Path) -> None:
    """P1: external mutation of completed path blocks resume writes."""

    repo = dual_write_repo
    preview = run_preview(repo)
    first_path = ".opsx/file_a.txt"
    second_path = ".opsx/file_b.txt"

    failed = run_go(
        repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
        write_fault_at_path=second_path,
    )
    assert failed.status == "FAILED"
    b_before = (repo / second_path).read_text(encoding="utf-8")

    (repo / first_path).write_text("external tamper\n", encoding="utf-8")

    resumed = run_go(repo, resume_run_id=failed.run_id, lanes=["process"])
    assert resumed.status == "STALE_EXECUTION"
    assert resumed.status != "RESOLVED_PENDING_VERIFICATION"
    assert (repo / second_path).read_text(encoding="utf-8") == b_before
    assert "resume_cas_completed_drift" in (resumed.stop_reason or "")


@pytest.mark.unit
def test_p2_resume_rejects_pending_path_drift(dual_write_repo: Path) -> None:
    """P2: external mutation of unfinished path blocks resume before overwrite."""

    repo = dual_write_repo
    preview = run_preview(repo)
    first_path = ".opsx/file_a.txt"
    second_path = ".opsx/file_b.txt"

    failed = run_go(
        repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
        write_fault_at_path=second_path,
    )
    assert failed.status == "FAILED"

    tampered = "external tamper on b\n"
    (repo / second_path).write_text(tampered, encoding="utf-8")

    resumed = run_go(repo, resume_run_id=failed.run_id, lanes=["process"])
    assert resumed.status == "STALE_EXECUTION"
    assert resumed.status != "RESOLVED_PENDING_VERIFICATION"
    assert (repo / second_path).read_text(encoding="utf-8") == tampered
    assert "resume_cas_pending_drift" in (resumed.stop_reason or "")


@pytest.mark.unit
def test_authority_marker_only_product_lane_owner_required(empty_repo: Path) -> None:
    """Authority trust-root: conflict-file marker cannot self-authorize AI_SEMANTIC."""

    part = PartitionedPath(
        path="app/marker_only.py",
        lane=AuthorityLane.PRODUCT,
        inventory_class="C_OUT_OF_SCOPE",
        unmerged=UnmergedPath(
            path="app/marker_only.py",
            kind=ConflictKind.BOTH_MODIFIED,
        ),
    )
    side_a = "# OPSX_AUTHORITY: invariant_keep\nbody_a_line1\nbody_a_line2\nunique_a\n"
    side_b = "# OPSX_AUTHORITY: invariant_keep\nbody_b_line1\nbody_b_line2\nunique_b\n"
    c = classify_path(part, None, side_a, side_b, None, repo_root=empty_repo)
    assert c.resolution_class == ResolutionClass.OWNER_REQUIRED
    assert "ai_semantic_downgrade" in c.reason
