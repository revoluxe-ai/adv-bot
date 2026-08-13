"""Operation detection, NUL-safe fingerprint, conflict start gate (H01/H02)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .errors import StopRequired
from .git_typed import TypedGit
from .hashutil import sha256_bytes, sha256_canonical, sha256_text
from .process_surfaces import norm_rel


@dataclass(frozen=True)
class StageEntry:
    stage: int
    mode: str
    oid: str
    path: str


@dataclass
class OperationState:
    operation: str
    head: str
    operation_head: str | None
    branch: str
    fingerprint: str
    unmerged: tuple[StageEntry, ...]
    staged_paths: tuple[str, ...]
    unstaged_paths: tuple[str, ...]
    untracked_paths: tuple[str, ...]
    sequencer_tree_hash: str
    repository_identity: str
    git_dir: Path
    raw_status: str = ""
    details: dict[str, Any] = field(default_factory=dict)


def parse_unmerged_z(raw: str) -> tuple[StageEntry, ...]:
    """Parse `git ls-files -u -z` into stage entries (NUL-delimited)."""
    entries: list[StageEntry] = []
    for rec in raw.split("\0"):
        if not rec.strip():
            continue
        # format: <mode> <oid> <stage>\t<path>
        try:
            meta, path = rec.split("\t", 1)
            mode, oid, stage_s = meta.split()
            entries.append(
                StageEntry(int(stage_s), mode, oid, norm_rel(path))
            )
        except ValueError:
            raise StopRequired("UNMERGED_PARSE_FAILED", {"record": rec[:200]})
    return tuple(entries)


def _split_z(raw: str) -> list[str]:
    return [p for p in raw.split("\0") if p]


def parse_porcelain_v2_z(status: str) -> tuple[list[str], list[str], list[str]]:
    """
    NUL-safe porcelain v2 parser (RC-HIGH-005).

    Supports ordinary (1), rename/copy (2), untracked (?), and skips unmerged (u).
    Paths may contain spaces; rename orig-path is the following NUL record.
    """
    staged: list[str] = []
    unstaged: list[str] = []
    untracked: list[str] = []
    records = _split_z(status)
    i = 0
    while i < len(records):
        rec = records[i]
        i += 1
        if not rec or rec.startswith("#"):
            continue
        if rec.startswith("?"):
            path = rec[2:] if rec.startswith("? ") else rec[1:]
            untracked.append(norm_rel(path))
            continue
        if rec.startswith("u "):
            continue
        kind = rec[0]
        if kind == "1":
            parts = rec.split(" ", 8)
            if len(parts) < 9:
                raise StopRequired(
                    "PORCELAIN_V2_MALFORMED_RECORD",
                    {"kind": "1", "record": rec[:160]},
                )
            xy = parts[1]
            path = norm_rel(parts[8])
            if len(xy) >= 2:
                if xy[0] != ".":
                    staged.append(path)
                if xy[1] != ".":
                    unstaged.append(path)
        elif kind == "2":
            # 2 XY sub mH mI mW hH hI <X><score> <path>  + next record origPath
            parts = rec.split(" ", 9)
            if len(parts) < 10:
                raise StopRequired(
                    "PORCELAIN_V2_MALFORMED_RECORD",
                    {"kind": "2", "record": rec[:160]},
                )
            xy = parts[1]
            path = norm_rel(parts[9])
            if i < len(records):
                _orig = records[i]
                i += 1
            else:
                raise StopRequired(
                    "PORCELAIN_V2_MISSING_RENAME_SOURCE",
                    {"record": rec[:160]},
                )
            if len(xy) >= 2:
                if xy[0] != ".":
                    staged.append(path)
                if xy[1] != ".":
                    unstaged.append(path)
        else:
            # Unknown record — fail closed rather than silently drop
            raise StopRequired("PORCELAIN_V2_UNKNOWN_RECORD", {"record": rec[:80]})
    return staged, unstaged, untracked


def hash_sequencer_tree(git_dir: Path) -> str:
    """Hash state-bearing sequencer / merge markers (H02 / HF-003)."""
    h = hashlib.sha256()
    found = False
    for name in ("rebase-merge", "rebase-apply", "sequencer"):
        root = git_dir / name
        if not root.is_dir():
            continue
        found = True
        files = sorted(p for p in root.rglob("*") if p.is_file())
        for path in files:
            rel = path.relative_to(git_dir).as_posix()
            h.update(rel.encode("utf-8"))
            h.update(b"\0")
            h.update(path.read_bytes())
            h.update(b"\0")
    for marker in (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REBASE_HEAD",
        "ORIG_HEAD",
        "MERGE_MSG",
        "MERGE_MODE",
    ):
        p = git_dir / marker
        if p.exists() and p.is_file():
            found = True
            h.update(marker.encode("utf-8"))
            h.update(b"\0")
            h.update(p.read_bytes())
            h.update(b"\0")
    if not found:
        return sha256_text("NO_SEQUENCER")
    return h.hexdigest()


def repo_identity(repo_root: Path, git_dir: Path) -> str:
    """Stable identity for resume guards."""
    return sha256_canonical(
        {
            "repo_root": str(repo_root.resolve()),
            "git_dir": str(git_dir.resolve()),
            "git_common": str((git_dir / "HEAD").resolve()) if (git_dir / "HEAD").exists() else "",
        }
    )


def detect_operation_state(repo_root: Path, git: TypedGit | None = None) -> OperationState:
    """Detect active merge/rebase/cherry-pick and compute fingerprint."""
    git = git or TypedGit(repo_root)
    git_dir = git.git_dir()
    head = git.rev_parse_head()
    branch = git.branch_show_current()
    status = git.status_porcelain_v2_z()
    unmerged = parse_unmerged_z(git.ls_files_unmerged_z())

    has_rebase = (
        (git_dir / "REBASE_HEAD").exists()
        or (git_dir / "rebase-merge").is_dir()
        or (git_dir / "rebase-apply").is_dir()
    )
    has_merge = (git_dir / "MERGE_HEAD").exists()
    has_cherry = (git_dir / "CHERRY_PICK_HEAD").exists()

    # Mutually exclusive primary operations (HF-003). Rebase may expose
    # CHERRY_PICK_HEAD — that alone is not a contradiction.
    if has_merge and has_rebase:
        raise StopRequired(
            "CONTRADICTORY_GIT_OPERATION_MARKERS",
            {"markers": ["MERGE_HEAD", "rebase-*"]},
        )
    if has_merge and has_cherry and not has_rebase:
        raise StopRequired(
            "CONTRADICTORY_GIT_OPERATION_MARKERS",
            {"markers": ["MERGE_HEAD", "CHERRY_PICK_HEAD"]},
        )

    operation = None
    operation_head = None
    if has_rebase:
        operation = "rebase"
        if (git_dir / "REBASE_HEAD").exists():
            operation_head = (git_dir / "REBASE_HEAD").read_text(encoding="utf-8").strip()
        elif (git_dir / "rebase-merge" / "stopped-sha").exists():
            operation_head = (git_dir / "rebase-merge" / "stopped-sha").read_text(
                encoding="utf-8"
            ).strip()
        elif (git_dir / "rebase-apply" / "original-commit").exists():
            operation_head = (git_dir / "rebase-apply" / "original-commit").read_text(
                encoding="utf-8"
            ).strip()
        if not operation_head:
            raise StopRequired("REBASE_OPERATION_HEAD_MISSING")
    elif has_merge:
        operation = "merge"
        operation_head = (git_dir / "MERGE_HEAD").read_text(encoding="utf-8").strip()
    elif has_cherry:
        operation = "cherry-pick"
        operation_head = (git_dir / "CHERRY_PICK_HEAD").read_text(encoding="utf-8").strip()

    if operation is None:
        raise StopRequired("NO_ACTIVE_SUPPORTED_GIT_OPERATION")

    staged, unstaged, untracked = parse_porcelain_v2_z(status)

    seq_hash = hash_sequencer_tree(git_dir)
    identity = repo_identity(repo_root, git_dir)
    # Include worktree content hashes for unmerged/dirty tracked paths (HF-003).
    worktree_hashes: dict[str, str] = {}
    for entry in unmerged:
        p = repo_root / entry.path
        if p.is_file() and not p.is_symlink():
            worktree_hashes[entry.path] = sha256_bytes(p.read_bytes())
    for path in set(staged) | set(unstaged):
        p = repo_root / path
        if path not in worktree_hashes and p.is_file() and not p.is_symlink():
            worktree_hashes[path] = sha256_bytes(p.read_bytes())
    fp_body = {
        "operation": operation,
        "head": head,
        "operation_head": operation_head,
        "unmerged": [(e.stage, e.mode, e.oid, e.path) for e in unmerged],
        "status_sha256": sha256_text(status),
        "sequencer_tree_hash": seq_hash,
        "repository_identity": identity,
        "tracked_worktree_hashes": worktree_hashes,
    }
    fingerprint = sha256_canonical(fp_body)
    return OperationState(
        operation=operation,
        head=head,
        operation_head=operation_head,
        branch=branch,
        fingerprint=fingerprint,
        unmerged=unmerged,
        staged_paths=tuple(sorted(set(staged))),
        unstaged_paths=tuple(sorted(set(unstaged))),
        untracked_paths=tuple(sorted(set(untracked))),
        sequencer_tree_hash=seq_hash,
        repository_identity=identity,
        git_dir=git_dir,
        raw_status=status,
    )


def conflict_start_gate(
    state: OperationState,
    *,
    resume_manifest: Mapping[str, Any] | None = None,
) -> None:
    """Require non-empty conflict inventory unless exact resume lineage (H01)."""
    if state.unmerged:
        return
    if resume_manifest is not None:
        if resume_manifest.get("repository_identity") != state.repository_identity:
            raise StopRequired("RESUME_LINEAGE_MISMATCH", {"reason": "repository_identity"})
        if resume_manifest.get("had_conflicts") is True:
            prior_fp = resume_manifest.get("initial_state_fingerprint")
            if prior_fp:
                return
        raise StopRequired("RESUME_LINEAGE_MISMATCH", {"reason": "no prior conflict"})
    raise StopRequired("NO_CONFIRMED_CONFLICT_INVENTORY")


def contamination_gate(state: OperationState, *, scope_paths: set[str]) -> None:
    """STOP on unrelated dirty/staged/untracked paths."""
    if state.untracked_paths:
        raise StopRequired(
            "UNRELATED_DIRTY_WORKTREE",
            {"untracked": list(state.untracked_paths[:20])},
        )
    foreign_staged = [p for p in state.staged_paths if p not in scope_paths]
    foreign_unstaged = [
        p
        for p in state.unstaged_paths
        if p not in scope_paths and p not in {e.path for e in state.unmerged}
    ]
    if foreign_staged or foreign_unstaged:
        raise StopRequired(
            "UNRELATED_DIRTY_WORKTREE",
            {"staged": foreign_staged, "unstaged": foreign_unstaged},
        )
