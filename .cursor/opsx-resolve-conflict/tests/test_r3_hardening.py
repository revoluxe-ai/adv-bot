"""R3: trusted entrypoint outside conflicted worktree."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import _git, run_trusted_cli


@pytest.mark.unit
def test_r3_conflicted_bootstrap_still_previews(r3_full_self_conflict_repo: Path) -> None:
    """R3: launcher materializes HEAD bootstrap; PREVIEW_READY with full manifest."""

    repo = r3_full_self_conflict_repo
    trusted_boot = repo / ".opsx" / "tools" / "trusted_resolver_boot.py"
    worktree_boot = (
        repo / ".cursor" / "opsx-resolve-conflict" / "runtime" / "boot_opsx_conflict.py"
    )
    assert re.search(r"^<<<<<<< ", trusted_boot.read_text(encoding="utf-8"), re.MULTILINE)
    assert re.search(r"^<<<<<<< ", worktree_boot.read_text(encoding="utf-8"), re.MULTILINE)

    head_oid = _git(repo, "rev-parse", "HEAD")
    code, report = run_trusted_cli(repo, "PREVIEW")
    assert code == 0
    assert report["STATUS"] == "PREVIEW_READY"
    assert report["BOOTSTRAP_SOURCE_REVISION"] == head_oid
    assert report["RUNTIME_SOURCE_REVISION"] == head_oid

    paths = report.get("PATH_INVENTORY", [])
    assert ".opsx/tools/trusted_resolver_boot.py" in paths
    assert ".cursor/opsx-resolve-conflict/runtime/boot_opsx_conflict.py" in paths
    assert "app/example.py" in paths
    assert report.get("STAGED_PATHS") == []


@pytest.mark.unit
def test_r3_worktree_bootstrap_bytes_not_executed(r3_full_self_conflict_repo: Path) -> None:
    """R3: committed HEAD bootstrap is clean; worktree copy has conflict markers."""

    repo = r3_full_self_conflict_repo
    head_oid = _git(repo, "rev-parse", "HEAD")
    trusted_from_head = subprocess.run(
        ["git", "show", "HEAD:.opsx/tools/trusted_resolver_boot.py"],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout or ""
    worktree = (repo / ".opsx" / "tools" / "trusted_resolver_boot.py").read_text(
        encoding="utf-8"
    )
    assert re.search(r"^<<<<<<< ", worktree, re.MULTILINE)
    assert not re.search(r"^<<<<<<< ", trusted_from_head, re.MULTILINE)

    _, report = run_trusted_cli(repo, "PREVIEW")
    assert report["BOOTSTRAP_SOURCE_REVISION"] == head_oid
    assert report["RUNTIME_SOURCE_REVISION"] == head_oid


@pytest.mark.unit
def test_r3_missing_bootstrap_fail_closed(missing_bootstrap_repo: Path) -> None:
    """Negative: no bootstrap at HEAD → fail-closed, no worktree fallback."""

    repo = missing_bootstrap_repo
    code, report = run_trusted_cli(repo, "PREVIEW")
    assert code == 2
    assert report["STATUS"] == "FAILED"
    assert "EXECUTION_CAPABILITY_OR_COMPATIBILITY_MISSING" in report.get("STOP_REASON", "")
