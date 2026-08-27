"""S: linked worktree root discovery for launcher."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import run_launcher_cwd


@pytest.mark.unit
def test_s1_linked_worktree_root_not_parent(linked_worktree_pair: tuple[Path, Path]) -> None:
    """S1: launcher resolves linked worktree root, not parent repository."""

    main, linked = linked_worktree_pair
    assert (linked / ".git").is_file()
    assert (main / ".git").is_dir()

    code, report = run_launcher_cwd(linked, "PREVIEW")
    assert code in (0, 2, 3)
    assert report.get("REPO_ROOT")
    resolved = Path(report["REPO_ROOT"]).resolve()
    assert resolved == linked.resolve()
    assert resolved != main.resolve()


@pytest.mark.unit
def test_s2_linked_worktree_merge_preview_without_repo(
    linked_worktree_merge_pair: tuple[Path, Path],
) -> None:
    """S2: active merge in linked worktree — PREVIEW without --repo."""

    main, linked = linked_worktree_merge_pair
    code, report = run_launcher_cwd(linked, "PREVIEW")
    assert code == 0
    assert report["STATUS"] == "PREVIEW_READY"
    assert report.get("OPERATION") == "merge"
    assert Path(report["REPO_ROOT"]).resolve() == linked.resolve()
    assert Path(report["REPO_ROOT"]).resolve() != main.resolve()
    assert report.get("UNMERGED_COUNT", 0) >= 1


@pytest.mark.unit
def test_s3_normal_repo_root_without_explicit_repo(normal_resolver_repo: Path) -> None:
    """S3: normal clone with .git/ directory resolves correctly."""

    repo = normal_resolver_repo
    assert (repo / ".git").is_dir()
    code, report = run_launcher_cwd(repo, "PREVIEW")
    assert code in (0, 2, 3)
    assert Path(report["REPO_ROOT"]).resolve() == repo.resolve()
