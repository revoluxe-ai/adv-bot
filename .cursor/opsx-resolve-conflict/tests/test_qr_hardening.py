"""Q/R hardening: whole-operation PREVIEW and trusted bootstrap."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
sys.path.insert(0, str(RUNTIME))

from conftest import _git, run_trusted_cli
from opsx_conflict.pipeline import run_preview


@pytest.mark.unit
def test_q1_preview_whole_operation_without_path(multi_path_preview_repo: Path) -> None:
    """Q1: PREVIEW without --path captures all unmerged paths."""

    result = run_preview(multi_path_preview_repo)
    assert result.status == "PREVIEW_READY"
    assert result.manifest is not None
    assert len(result.manifest.unmerged_paths) >= 3
    assert result.clusters
    assert result.classified
    assert result.staged_paths == []


@pytest.mark.unit
def test_q2_preview_path_drill_down_preserves_manifest(multi_path_preview_repo: Path) -> None:
    """Q2: --path drill-down keeps whole-operation identity."""

    full = run_preview(multi_path_preview_repo)
    target = ".opsx/proc_a.txt"
    drilled = run_preview(multi_path_preview_repo, drill_down_path=target)
    assert drilled.status == "PREVIEW_READY"
    assert drilled.fingerprint == full.fingerprint
    assert drilled.manifest is not None
    assert full.manifest is not None
    assert len(drilled.manifest.unmerged_paths) == len(full.manifest.unmerged_paths)
    assert drilled.drill_down_path == target
    assert drilled.path_detail is not None
    assert drilled.path_detail["path"] == target


@pytest.mark.unit
def test_r1_trusted_boot_with_conflicted_worktree_boot(self_conflict_boot_repo: Path) -> None:
    """R1: conflicted worktree boot; trusted runtime still PREVIEW_READY."""

    repo = self_conflict_boot_repo
    boot = repo / ".cursor" / "opsx-resolve-conflict" / "runtime" / "boot_opsx_conflict.py"
    assert "<<<<<<<" in boot.read_text(encoding="utf-8")

    head_oid = _git(repo, "rev-parse", "HEAD")
    code, report = run_trusted_cli(repo, "PREVIEW")
    assert code == 0
    assert report["STATUS"] == "PREVIEW_READY"
    assert report["RUNTIME_SOURCE_REVISION"] == head_oid
    paths = report.get("PATH_INVENTORY", [])
    assert ".cursor/opsx-resolve-conflict/runtime/boot_opsx_conflict.py" in paths


@pytest.mark.unit
def test_r2_trusted_runtime_provenance_not_worktree_bytes(
    self_conflict_boot_repo: Path,
) -> None:
    """R2: runtime executes HEAD revision, not incoming conflicted boot."""

    repo = self_conflict_boot_repo
    head_oid = _git(repo, "rev-parse", "HEAD")
    trusted_boot = subprocess.run(
        [
            "git",
            "show",
            "HEAD:.cursor/opsx-resolve-conflict/runtime/boot_opsx_conflict.py",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    worktree_boot = (
        repo / ".cursor" / "opsx-resolve-conflict" / "runtime" / "boot_opsx_conflict.py"
    ).read_text(encoding="utf-8")
    assert re.search(r"^<<<<<<< ", worktree_boot, re.MULTILINE)
    assert not re.search(r"^<<<<<<< ", trusted_boot, re.MULTILINE)

    _, report = run_trusted_cli(repo, "PREVIEW")
    assert report["RUNTIME_SOURCE_REVISION"] == head_oid


@pytest.mark.unit
def test_combined_qr_multi_path_self_conflict(combined_qr_repo: Path) -> None:
    """Combined: trusted bootstrap + whole-operation manifest with resolver conflicts."""

    repo = combined_qr_repo
    code, report = run_trusted_cli(repo, "PREVIEW")
    assert code == 0
    assert report["STATUS"] == "PREVIEW_READY"
    assert report["UNMERGED_COUNT"] >= 3
    paths = report.get("PATH_INVENTORY", [])
    assert ".cursor/opsx-resolve-conflict/runtime/boot_opsx_conflict.py" in paths
    assert "app/module.py" in paths
    assert report.get("RUNTIME_SOURCE_REVISION")
