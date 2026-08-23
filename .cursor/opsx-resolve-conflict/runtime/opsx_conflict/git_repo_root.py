"""Git worktree root discovery — supports linked worktrees (.git file)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _is_git_marker(candidate: Path) -> bool:
    """`.git` directory or linked-worktree `.git` file."""

    git_marker = candidate / ".git"
    return git_marker.is_dir() or git_marker.is_file()


def discover_worktree_root(start: Path) -> Path:
    """
    Authoritative worktree root via ``git rev-parse --show-toplevel``.

    Ascends from ``start`` until a Git marker (.git dir or file) is found,
    then stops — never continues to a parent repository.
    """

    resolved_start = start.resolve()
    for candidate in [resolved_start, *resolved_start.parents]:
        if not _is_git_marker(candidate):
            continue
        result = subprocess.run(
            ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0 or not (result.stdout or "").strip():
            raise RuntimeError(
                f"REPO_ROOT_DISCOVERY_FAILED:git_top_level:{candidate}"
            )
        top = Path((result.stdout or "").strip()).resolve()
        if not top.is_dir():
            raise RuntimeError(
                f"REPO_ROOT_DISCOVERY_FAILED:invalid_top_level:{top}"
            )
        return top
    raise RuntimeError("REPO_ROOT_DISCOVERY_FAILED:not_in_git_worktree")
