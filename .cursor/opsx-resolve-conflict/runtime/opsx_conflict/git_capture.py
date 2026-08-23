"""Typed read-only Git operations для conflict capture."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from opsx_conflict.models import (
    ConflictKind,
    ConflictManifest,
    OperationIdentity,
    OperationType,
    StageBlob,
    UnmergedPath,
)


class GitCaptureError(Exception):
    """Git state не позволяет capture."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitCaptureError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout}"
        )
    return result.stdout.strip()


def _oid(repo_root: Path, ref: str) -> str | None:
    try:
        out = _run_git(repo_root, "rev-parse", "-q", "--verify", ref)
        return out if out else None
    except GitCaptureError:
        return None


def _detect_operation(repo_root: Path) -> tuple[OperationType, str | None]:
    merge_head = _oid(repo_root, "MERGE_HEAD")
    cherry_pick = _oid(repo_root, "CHERRY_PICK_HEAD")
    rebase_head = _oid(repo_root, "REBASE_HEAD")
    rebase_merge = (repo_root / ".git" / "rebase-merge").exists()
    rebase_apply = (repo_root / ".git" / "rebase-apply").exists()

    if merge_head and not (rebase_merge or rebase_apply):
        return OperationType.MERGE, merge_head
    if rebase_merge or rebase_apply or rebase_head:
        op_head = rebase_head or cherry_pick
        return OperationType.REBASE, op_head
    if cherry_pick:
        return OperationType.CHERRY_PICK, cherry_pick
    return OperationType.NONE, None


def _status_to_kind(code: str) -> ConflictKind:
    mapping = {
        "UU": ConflictKind.BOTH_MODIFIED,
        "AA": ConflictKind.BOTH_ADDED,
        "DU": ConflictKind.DELETED_BY_US,
        "UD": ConflictKind.DELETED_BY_THEM,
        "DD": ConflictKind.BOTH_DELETED,
        "AU": ConflictKind.ADDED_BY_US,
        "UA": ConflictKind.ADDED_BY_THEM,
    }
    return mapping.get(code, ConflictKind.OTHER)


def _has_conflict_markers(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "<<<<<<<" in text or ">>>>>>>" in text


def _stage_blob(repo_root: Path, path: str, stage: int) -> StageBlob:
    try:
        out = _run_git(repo_root, "ls-files", "-u", "--stage", path)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4 and int(parts[2]) == stage:
                return StageBlob(
                    stage=stage,
                    role=f"stage_{stage}",
                    oid=parts[1],
                    mode=parts[0],
                )
    except GitCaptureError:
        pass
    return StageBlob(stage=stage, role=f"stage_{stage}", oid=None, mode=None)


def compute_fingerprint(repo_root: Path, extra_paths: list[str] | None = None) -> str:
    """State fingerprint для drift detection."""

    parts: list[str] = []
    head = _oid(repo_root, "HEAD") or ""
    parts.append(f"HEAD:{head}")
    for marker in ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "ORIG_HEAD"):
        oid = _oid(repo_root, marker)
        if oid:
            parts.append(f"{marker}:{oid}")
    try:
        unmerged = _run_git(repo_root, "diff", "--name-only", "--diff-filter=U")
        parts.append(f"unmerged:{unmerged}")
    except GitCaptureError:
        parts.append("unmerged:")
    for rel in extra_paths or []:
        p = repo_root / rel
        if p.is_file():
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            parts.append(f"path:{rel}:{h}")
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def capture_operation(repo_root: Path) -> ConflictManifest:
    """CAPTURE: whole conflict set + operation identity."""

    repo_root = repo_root.resolve()
    if not (repo_root / ".git").exists():
        raise GitCaptureError("not_a_git_repository")

    op_type, op_head = _detect_operation(repo_root)
    head_oid = _oid(repo_root, "HEAD") or ""
    orig_head = _oid(repo_root, "ORIG_HEAD")

    side_a_label = "ACCUMULATED_HEAD"
    side_b_label = "OPERATION_HEAD"
    side_a_oid = head_oid
    side_b_oid = op_head
    base_oid: str | None = None

    if op_type == OperationType.MERGE and op_head:
        try:
            base_oid = _run_git(repo_root, "merge-base", "HEAD", op_head)
        except GitCaptureError:
            base_oid = None
        side_a_label = "CURRENT_HEAD"
        side_b_label = "INCOMING_MERGE_HEAD"
    elif op_type in (OperationType.REBASE, OperationType.CHERRY_PICK) and op_head:
        parent = _oid(repo_root, f"{op_head}^")
        base_oid = parent
        side_a_label = "ACCUMULATED_ONTO"
        side_b_label = "REPLAYED_COMMIT"

    operation = OperationIdentity(
        operation_type=op_type,
        head_oid=head_oid,
        orig_head_oid=orig_head,
        operation_head_oid=op_head,
        base_oid=base_oid,
        side_a_label=side_a_label,
        side_b_label=side_b_label,
        side_a_oid=side_a_oid,
        side_b_oid=side_b_oid,
    )

    unmerged: list[UnmergedPath] = []
    try:
        status_out = _run_git(repo_root, "status", "--porcelain", "-u")
    except GitCaptureError:
        status_out = ""

    for line in status_out.splitlines():
        if len(line) < 4:
            continue
        xy = line[:2]
        if "U" not in xy and xy not in ("AA", "DD", "AU", "UA", "DU", "UD"):
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        kind = _status_to_kind(xy)
        worktree = repo_root / path
        stages = [_stage_blob(repo_root, path, s) for s in (1, 2, 3)]
        unmerged.append(
            UnmergedPath(
                path=path,
                kind=kind,
                stages=stages,
                worktree_has_markers=_has_conflict_markers(worktree),
            )
        )

    auto_merged: list[str] = []
    if op_head:
        try:
            if op_type == OperationType.MERGE:
                diff_out = _run_git(
                    repo_root,
                    "diff",
                    "--name-only",
                    base_oid or "",
                    op_head,
                )
            else:
                diff_out = _run_git(
                    repo_root,
                    "diff",
                    "--name-only",
                    f"{op_head}^",
                    op_head,
                )
            unmerged_set = {p.path for p in unmerged}
            auto_merged = [p for p in diff_out.splitlines() if p and p not in unmerged_set]
        except GitCaptureError:
            pass

    manifest = ConflictManifest(
        operation=operation,
        unmerged_paths=unmerged,
        auto_merged_paths=auto_merged,
        repo_root=str(repo_root),
    )
    manifest.fingerprint = compute_fingerprint(repo_root)
    return manifest


def read_stage_content(repo_root: Path, path: str, stage: int) -> str | None:
    """Читает blob content из index stage."""

    repo_root = repo_root.resolve()
    blob = _stage_blob(repo_root, path, stage)
    if not blob.oid:
        return None
    try:
        return _run_git(repo_root, "cat-file", "-p", blob.oid)
    except GitCaptureError:
        return None


def stage_file(repo_root: Path, path: str) -> None:
    """Stage exact path — typed write для GO."""

    _run_git(repo_root, "add", "--", path)


def has_unmerged_entries(repo_root: Path) -> bool:
    """True если index содержит unmerged entries."""

    try:
        out = _run_git(repo_root, "diff", "--name-only", "--diff-filter=U")
        return bool(out.strip())
    except GitCaptureError:
        return True


def list_staged_paths(repo_root: Path) -> list[str]:
    """Все paths в index stage (staged candidate surface)."""

    try:
        out = _run_git(repo_root, "diff", "--cached", "--name-only", "--diff-filter=ACDMRTUXB")
        return sorted([p for p in out.splitlines() if p])
    except GitCaptureError:
        return []


def compute_candidate_tree_oid(repo_root: Path) -> str:
    """Canonical full staged candidate identity via git write-tree."""

    repo_root = repo_root.resolve()
    if has_unmerged_entries(repo_root):
        raise GitCaptureError("unmerged_entries_present")
    return _run_git(repo_root, "write-tree")
