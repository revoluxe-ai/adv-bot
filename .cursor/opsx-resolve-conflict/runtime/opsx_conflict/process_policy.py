"""Process lane policy — extracted from admin resolver allowlist semantics."""

from __future__ import annotations

from pathlib import Path

from opsx_conflict.partition import _inventory_class, _load_sources, _matches_any


def process_lane_may_write(path: str, repo_root: Path) -> tuple[bool, str]:
    """Who may write: process lane Class A only."""

    allowlist, hard_exclude = _load_sources(repo_root)
    inv = _inventory_class(path, allowlist, hard_exclude)
    if inv == "A_IN_SCOPE":
        return True, "process_lane_class_a"
    if inv == "B_ALLOWLIST_GAP":
        return False, "allowlist_gap_no_write"
    return False, f"inventory:{inv}"


def process_lane_may_stage(path: str, repo_root: Path) -> bool:
    ok, _ = process_lane_may_write(path, repo_root)
    return ok


def is_authority_sensitive_path(path: str) -> bool:
    sensitive = (
        ".cursor/commands/",
        ".cursor/pipeline/",
        "opsx-source-resolution",
        "opsx-execution-preflight",
    )
    norm = path.replace("\\", "/")
    return any(s in norm for s in sensitive)
