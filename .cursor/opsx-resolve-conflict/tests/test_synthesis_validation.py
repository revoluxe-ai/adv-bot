"""Regression: pre-write synthesis validation for invalid Python candidates."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from opsx_conflict.git_capture import read_stage_content
from opsx_conflict.models import ResolutionClass
from opsx_conflict.pipeline import run_go, run_preview
from opsx_conflict.resolve_text import _synthesis_union
from opsx_conflict.verify import validate_synthesis_candidate


MANIFEST_PATH = ".opsx/00_manifest_stub.json"
BAD_MODULE_PATH = ".opsx/bad_module.py"


def _git_index_stage(repo: Path, rel_path: str) -> str | None:
    """Return git index stage (0=resolved, 1/2/3=unmerged) or None if absent."""

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


@pytest.mark.unit
def test_synthesis_union_produces_invalid_python_for_docstring_fixture() -> None:
    """Fixture sides merge to syntax-invalid Python (mechanical synthesis defect)."""

    side_a = (
        '"""OPSX runtime module.\n\n'
        "Line A only.\n"
        "Extra A1.\n"
        "Extra A2.\n"
        "Extra A3.\n"
        '"""\n\n'
        '__version__ = "1.0.0"\n'
        'helper_a = "from-a"\n'
    )
    side_b = (
        '"""OPSX runtime module.\n\n'
        "Line B only.\n"
        "Extra B1.\n"
        "Extra B2.\n"
        "Extra B3.\n"
        '"""\n\n'
        '__version__ = "1.0.0"\n'
        'helper_b = "from-b"\n'
    )
    merged = _synthesis_union(side_a, side_b)
    ok, refs = validate_synthesis_candidate(BAD_MODULE_PATH, merged)
    assert not ok
    assert any("python_syntax_error" in ref for ref in refs)


@pytest.mark.unit
def test_w_invalid_synthesis_rejected_before_mutation(bad_python_synthesis_repo: Path) -> None:
    """W: invalid AI_SEMANTIC synthesis must not write/stage; path escalates OWNER_REQUIRED."""

    repo = bad_python_synthesis_repo
    preview = run_preview(repo)
    bad_cls = next(c for c in preview.classified if c.path == BAD_MODULE_PATH)
    assert bad_cls.resolution_class == ResolutionClass.AI_SEMANTIC

    pre_worktree = (repo / BAD_MODULE_PATH).read_text(encoding="utf-8")
    pre_index = _git_index_stage(repo, BAD_MODULE_PATH)
    assert "<<<<<<<" not in pre_worktree
    assert pre_index == "unmerged"

    result = run_go(
        repo,
        frozen_fingerprint=preview.fingerprint,
        lanes=["process"],
    )

    assert result.status == "PAUSED"
    assert result.stage.value == "PAUSED"
    assert result.stop_reason
    assert BAD_MODULE_PATH in result.stop_reason
    assert "synthesis_validation_failed" in result.stop_reason
    assert "python_syntax_error" in result.stop_reason

    post_worktree = (repo / BAD_MODULE_PATH).read_text(encoding="utf-8")
    assert post_worktree == pre_worktree
    assert _git_index_stage(repo, BAD_MODULE_PATH) == pre_index
    compile(post_worktree, BAD_MODULE_PATH, "exec")  # pre-state is valid; candidate was rejected

    escalated = next(c for c in result.classified if c.path == BAD_MODULE_PATH)
    assert escalated.resolution_class == ResolutionClass.OWNER_REQUIRED
    assert "synthesis_validation_escalation" in escalated.reason

    assert result.execution_state is not None
    assert MANIFEST_PATH in result.execution_state.get("completed_paths", [])
    assert BAD_MODULE_PATH not in result.execution_state.get("completed_paths", [])
    assert BAD_MODULE_PATH in result.execution_state.get("owner_escalated_paths", {})
    assert result.execution_state.get("status") == "PAUSED_OWNER_REQUIRED"

    assert MANIFEST_PATH in (result.staged_paths or [])
    assert BAD_MODULE_PATH not in (result.staged_paths or [])

    assert result.status not in (
        "RESOLVED_PENDING_VERIFICATION",
        "VERIFIED_READY_FOR_CONTINUE",
    )

    side_a = read_stage_content(repo, BAD_MODULE_PATH, 2)
    assert side_a is not None
    resumed = run_go(
        repo,
        resume_run_id=result.run_id,
        lanes=["process"],
        owner_choices={BAD_MODULE_PATH: "side_a"},
    )
    assert BAD_MODULE_PATH in resumed.execution_state.get("completed_paths", [])
    assert BAD_MODULE_PATH not in resumed.execution_state.get(
        "owner_escalated_paths", {}
    )
    assert (repo / BAD_MODULE_PATH).read_text(encoding="utf-8") == side_a
