"""Regression: explicit Owner per-path decisions override AI_SEMANTIC synthesis."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from opsx_conflict.git_capture import read_stage_content
from opsx_conflict.models import (
    AuthorityLane,
    ClassifiedConflict,
    ResolutionClass,
    ResolutionKind,
)
from opsx_conflict.pipeline import run_go, run_preview
from opsx_conflict.resolve_text import resolve_text

MANIFEST_PATH = ".opsx/00_manifest_stub.json"
BAD_MODULE_PATH = ".opsx/bad_module.py"
DELETE_PATH = ".opsx/to_delete.txt"


def _git_index_stage(repo: Path, rel_path: str) -> str | None:
    norm = rel_path.replace("\\", "/")
    result = subprocess.run(
        ["git", "ls-files", "-u", "--", norm],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    stages = {line.split()[2] for line in result.stdout.splitlines() if line.strip()}
    if "0" in stages:
        return "0"
    if stages & {"1", "2", "3"}:
        return "unmerged"
    return None


def _ai_semantic_conflict(path: str) -> ClassifiedConflict:
    return ClassifiedConflict(
        conflict_id="x",
        cluster_id=None,
        path=path,
        lane=AuthorityLane.PROCESS,
        resolution_class=ResolutionClass.AI_SEMANTIC,
        resolution_kind=ResolutionKind.SYNTHESIS,
        reason="compatible_semantic",
    )


@pytest.mark.unit
def test_resolve_ai_semantic_owner_side_a_exact_target() -> None:
    """Owner side_a on AI_SEMANTIC returns exact TARGET bytes, not synthesis."""

    side_a = '"""doc"""\nvalue = "target"\n'
    side_b = '"""doc"""\nvalue = "source"\n'
    classified = _ai_semantic_conflict(".opsx/x.py")
    with patch("opsx_conflict.resolve_text._synthesis_union") as mock_union:
        text, kind = resolve_text(
            classified, side_a, side_b, side_a, owner_choice="side_a"
        )
        mock_union.assert_not_called()
    assert text == side_a
    assert kind == ResolutionKind.KEEP_SIDE_A


@pytest.mark.unit
def test_resolve_ai_semantic_owner_side_b_exact_source() -> None:
    """Owner side_b on AI_SEMANTIC returns exact SOURCE bytes."""

    side_a = "a-only\n"
    side_b = "b-only\n"
    classified = _ai_semantic_conflict(".opsx/x.py")
    with patch("opsx_conflict.resolve_text._synthesis_union") as mock_union:
        text, kind = resolve_text(
            classified, side_a, side_b, side_a, owner_choice="side_b"
        )
        mock_union.assert_not_called()
    assert text == side_b
    assert kind == ResolutionKind.KEEP_SIDE_B


@pytest.mark.unit
def test_resolve_ai_semantic_owner_delete() -> None:
    """Owner delete on AI_SEMANTIC requests deletion without synthesis."""

    classified = _ai_semantic_conflict(DELETE_PATH)
    with patch("opsx_conflict.resolve_text._synthesis_union") as mock_union:
        text, kind = resolve_text(
            classified, "keep-me\n", "other\n", "keep-me\n", owner_choice="delete"
        )
        mock_union.assert_not_called()
    assert text is None
    assert kind == ResolutionKind.DELETE


@pytest.mark.unit
def test_go_ai_semantic_owner_side_a_writes_exact_target(
    bad_python_synthesis_repo: Path,
) -> None:
    """GO: AI_SEMANTIC + Owner side_a writes exact stage-2 TARGET bytes."""

    repo = bad_python_synthesis_repo
    preview = run_preview(repo)
    bad_cls = next(c for c in preview.classified if c.path == BAD_MODULE_PATH)
    assert bad_cls.resolution_class == ResolutionClass.AI_SEMANTIC

    _, side_a, _ = (
        None,
        read_stage_content(repo, BAD_MODULE_PATH, 2),
        read_stage_content(repo, BAD_MODULE_PATH, 3),
    )
    assert side_a is not None

    with patch("opsx_conflict.resolve_text._synthesis_union") as mock_union:
        result = run_go(
            repo,
            frozen_fingerprint=preview.fingerprint,
            lanes=["process"],
            owner_choices={BAD_MODULE_PATH: "side_a"},
        )
        mock_union.assert_not_called()

    assert BAD_MODULE_PATH in result.execution_state.get("completed_paths", [])
    assert (repo / BAD_MODULE_PATH).read_text(encoding="utf-8") == side_a
    assert BAD_MODULE_PATH in (result.staged_paths or [])
    assert result.status in ("PAUSED", "RESOLVED_PENDING_VERIFICATION")
    assert result.status not in (
        "VERIFIED_READY_FOR_CONTINUE",
    )


@pytest.mark.unit
def test_go_escalated_path_resumes_with_owner_side_a(
    bad_python_synthesis_repo: Path,
) -> None:
    """Previously escalated path executes again when Owner supplies side_a."""

    repo = bad_python_synthesis_repo
    preview = run_preview(repo)
    _, side_a, _ = (
        None,
        read_stage_content(repo, BAD_MODULE_PATH, 2),
        read_stage_content(repo, BAD_MODULE_PATH, 3),
    )
    assert side_a is not None

    first = run_go(
        repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )
    assert first.status == "PAUSED"
    assert BAD_MODULE_PATH in first.execution_state.get("owner_escalated_paths", {})

    resumed = run_go(
        repo,
        resume_run_id=first.run_id,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
        owner_choices={BAD_MODULE_PATH: "side_a"},
    )

    assert BAD_MODULE_PATH not in resumed.execution_state.get(
        "owner_escalated_paths", {}
    )
    assert BAD_MODULE_PATH in resumed.execution_state.get("completed_paths", [])
    assert (repo / BAD_MODULE_PATH).read_text(encoding="utf-8") == side_a
    assert BAD_MODULE_PATH in (resumed.staged_paths or [])


@pytest.mark.unit
def test_go_owner_side_b_on_ai_semantic(bad_python_synthesis_repo: Path) -> None:
    """Owner side_b on AI_SEMANTIC applies exact SOURCE bytes."""

    repo = bad_python_synthesis_repo
    preview = run_preview(repo)
    _, _, side_b = (
        None,
        read_stage_content(repo, BAD_MODULE_PATH, 2),
        read_stage_content(repo, BAD_MODULE_PATH, 3),
    )
    assert side_b is not None

    result = run_go(
        repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
        owner_choices={BAD_MODULE_PATH: "side_b"},
    )

    assert (repo / BAD_MODULE_PATH).read_text(encoding="utf-8") == side_b
    assert BAD_MODULE_PATH in result.execution_state.get("completed_paths", [])


@pytest.mark.unit
def test_go_owner_delete_on_owner_required(delete_modify_repo: Path) -> None:
    """Owner delete on OWNER_REQUIRED removes conflicted path."""

    repo = delete_modify_repo
    preview = run_preview(repo)
    del_cls = next(c for c in preview.classified if c.path == DELETE_PATH)
    assert del_cls.resolution_class == ResolutionClass.OWNER_REQUIRED

    result = run_go(
        repo,
        frozen_fingerprint=preview.fingerprint,
        owner_choices={DELETE_PATH: "delete"},
    )

    assert not (repo / DELETE_PATH).exists()
    assert DELETE_PATH in result.execution_state.get("completed_paths", [])


@pytest.mark.unit
def test_go_without_owner_choice_still_pauses_on_invalid_synthesis(
    bad_python_synthesis_repo: Path,
) -> None:
    """No explicit Owner choice: invalid AI_SEMANTIC synthesis still PAUSED."""

    repo = bad_python_synthesis_repo
    preview = run_preview(repo)
    result = run_go(
        repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )
    assert result.status == "PAUSED"
    assert "synthesis_validation_failed" in (result.stop_reason or "")
    assert result.status not in (
        "RESOLVED_PENDING_VERIFICATION",
        "VERIFIED_READY_FOR_CONTINUE",
    )


@pytest.mark.unit
def test_resume_with_owner_choice_is_idempotent(
    bad_python_synthesis_repo: Path,
) -> None:
    """Retry/resume with same Owner choice does not duplicate work."""

    repo = bad_python_synthesis_repo
    preview = run_preview(repo)
    _, side_a, _ = (
        None,
        read_stage_content(repo, BAD_MODULE_PATH, 2),
        read_stage_content(repo, BAD_MODULE_PATH, 3),
    )

    first = run_go(
        repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )
    resumed = run_go(
        repo,
        resume_run_id=first.run_id,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
        owner_choices={BAD_MODULE_PATH: "side_a"},
    )
    again = run_go(
        repo,
        resume_run_id=first.run_id,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
        owner_choices={BAD_MODULE_PATH: "side_a"},
    )

    completed = again.execution_state.get("completed_paths", [])
    assert completed.count(BAD_MODULE_PATH) == 1
    assert (repo / BAD_MODULE_PATH).read_text(encoding="utf-8") == side_a
    assert resumed.run_id == again.run_id
