"""Textual resolution strategies для AUTO_SAFE и AI_SEMANTIC."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from opsx_conflict.authority_policy import synthesize_under_target_authority
from opsx_conflict.conflict_markers import has_unresolved_merge_markers
from opsx_conflict.models import (
    ClassifiedConflict,
    ResolutionClass,
    ResolutionKind,
)

_MARKER_START = re.compile(r"^<<<<<<<.*$", re.MULTILINE)
_MARKER_MID = re.compile(r"^=======.*$", re.MULTILINE)
_MARKER_END = re.compile(r"^>>>>>>>.*$", re.MULTILINE)

_VALID_OWNER_CHOICES = frozenset({"side_a", "side_b", "delete", "keep"})


def _resolve_explicit_owner_choice(
    owner_choice: str,
    side_a: str | None,
    side_b: str | None,
    worktree: str | None,
) -> tuple[str | None, ResolutionKind]:
    """Явное Owner-решение по пути; приоритет над классификатором и синтезом."""

    if owner_choice == "side_a" and side_a is not None:
        return side_a, ResolutionKind.KEEP_SIDE_A
    if owner_choice == "side_b" and side_b is not None:
        return side_b, ResolutionKind.KEEP_SIDE_B
    if owner_choice == "keep":
        content = worktree if worktree is not None else (side_a or side_b)
        if content is not None:
            return content, ResolutionKind.KEEP_SIDE_A
    if owner_choice == "delete":
        return None, ResolutionKind.DELETE
    return None, ResolutionKind.UNRESOLVED


def _remove_markers_take_union(text: str) -> str:
    """Mechanical union: both sides без markers."""

    parts = re.split(r"^<<<<<<<.*?$", text, flags=re.MULTILINE)
    result_lines: list[str] = []
    for part in parts:
        if "=======" in part:
            before, after = part.split("=======", 1)
            after = re.sub(r"^>>>>>>>.*$", "", after, flags=re.MULTILINE)
            result_lines.append(before)
            result_lines.append(after)
        else:
            result_lines.append(part)
    return "".join(result_lines)


def _remove_markers_take_side(text: str, side: str) -> str:
    """Extract one side from conflict markers."""

    pattern = re.compile(
        r"^<<<<<<<.*?$\n(.*?)^=======\n(.*?)^>>>>>>>.*?$",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return _strip_markers(text)
    ours, theirs = match.group(1), match.group(2)
    if side == "side_a":
        return ours
    return theirs


def _strip_markers(text: str) -> str:
    text = _MARKER_START.sub("", text)
    text = _MARKER_MID.sub("", text)
    text = _MARKER_END.sub("", text)
    return text


def _synthesis_union(side_a: str, side_b: str) -> str:
    """Compatible union: concatenate unique non-overlapping tails."""

    if side_a == side_b:
        return side_a
    a_lines = side_a.splitlines(keepends=True)
    b_lines = side_b.splitlines(keepends=True)
    common = 0
    for i, (la, lb) in enumerate(zip(a_lines, b_lines, strict=False)):
        if la != lb:
            break
        common = i + 1
    merged = "".join(a_lines[:common])
    tail_a = a_lines[common:]
    tail_b = b_lines[common:]
    merged += "".join(tail_a)
    for line in tail_b:
        if line not in tail_a:
            merged += line
    return merged


def resolve_text(
    classified: ClassifiedConflict,
    side_a: str | None,
    side_b: str | None,
    worktree: str | None,
    owner_choice: str | None = None,
) -> tuple[str | None, ResolutionKind]:
    """RESOLVE: produce candidate text for path."""

    if owner_choice is not None:
        if owner_choice not in _VALID_OWNER_CHOICES:
            return None, ResolutionKind.UNRESOLVED
        explicit = _resolve_explicit_owner_choice(
            owner_choice, side_a, side_b, worktree
        )
        if explicit[1] != ResolutionKind.UNRESOLVED:
            return explicit
        return None, ResolutionKind.UNRESOLVED

    source = worktree or ""
    if classified.resolution_class == ResolutionClass.AUTO_SAFE:
        if has_unresolved_merge_markers(source):
            resolved = _remove_markers_take_union(source)
            return resolved, ResolutionKind.UNION
        if side_a and side_b:
            return _synthesis_union(side_a, side_b), ResolutionKind.UNION
        return side_a or side_b, ResolutionKind.KEEP_SIDE_A

    if classified.resolution_class == ResolutionClass.AI_SEMANTIC:
        if classified.applied_policy_id and classified.reason.startswith("policy_target"):
            if side_a and side_b:
                return (
                    synthesize_under_target_authority(side_a, side_b),
                    ResolutionKind.SYNTHESIS,
                )
        if has_unresolved_merge_markers(source):
            resolved = _remove_markers_take_union(source)
            return resolved, ResolutionKind.SYNTHESIS
        if side_a and side_b:
            return _synthesis_union(side_a, side_b), ResolutionKind.SYNTHESIS
        return side_a or side_b, ResolutionKind.SYNTHESIS

    return None, ResolutionKind.UNRESOLVED


def write_resolved_file(repo_root: Path, path: str, content: str | None) -> str | None:
    """Write candidate to worktree."""

    target = repo_root / path
    if content is None:
        if target.exists():
            target.unlink()
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    return hashlib.sha256(content.encode()).hexdigest()


def restore_worktree_path(
    repo_root: Path,
    path: str,
    prior_content: str | None,
) -> None:
    """Восстановить worktree path до pre-resolution содержимого (recovery)."""

    target = repo_root / path
    if prior_content is None:
        if target.exists():
            target.unlink()
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(prior_content, encoding="utf-8", newline="\n")
