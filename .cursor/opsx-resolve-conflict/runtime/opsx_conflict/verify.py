"""RESOLUTION_VERIFICATION и CANDIDATE_VERIFICATION."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

from opsx_conflict.conflict_markers import has_unresolved_merge_markers
from opsx_conflict.git_capture import read_stage_content
from opsx_conflict.models import (
    ClassifiedConflict,
    ConflictManifest,
    ResolutionClass,
    ResolutionLedgerEntry,
)

_DEF_RE = re.compile(r"^def\s+(\w+)", re.MULTILINE)
_CALL_RE = re.compile(r"\b(\w+)\s*\(")


def validate_synthesis_candidate(
    path: str,
    content: str | None,
    *,
    allow_delete: bool = False,
) -> tuple[bool, list[str]]:
    """Pre-write validation для synthesized candidate (off-index, до mutation).

    Для ``.py`` включает ``compile``-level syntax check. Не мутирует worktree/index.
  """

    if content is None:
        if allow_delete:
            return True, ["validation:delete_candidate_ok"]
        return False, ["validation:missing_content"]

    if has_unresolved_merge_markers(content):
        return False, ["validation:conflict_markers_present"]

    refs: list[str] = [f"validation:no_markers:{path}"]
    if path.endswith(".py"):
        try:
            compile(content, path, "exec")
            refs.append("validation:python_syntax_ok")
        except SyntaxError as exc:
            return False, [f"validation:python_syntax_error:{exc.msg}"]

    refs.append(f"validation:structural_ok:{path}")
    return True, refs


def verify_resolution_unit(
    repo_root: Path,
    path: str,
    classified: ClassifiedConflict,
    resolution_kind: str | None = None,
) -> tuple[bool, list[str]]:
    """A. RESOLUTION_VERIFICATION для одного path/cluster."""

    refs: list[str] = []
    target = repo_root / path
    effective_kind = resolution_kind or classified.resolution_kind.value
    if effective_kind == "DELETE":
        if target.exists():
            return False, ["delete_expected_missing_file"]
        refs.append("resolution:delete_verified")
        return True, refs

    if not target.is_file():
        return False, ["missing_resolved_file"]

    text = target.read_text(encoding="utf-8", errors="replace")
    if has_unresolved_merge_markers(text):
        return False, ["conflict_markers_remain"]

    refs.append(f"resolution:no_markers:{path}")
    if path.endswith(".py"):
        try:
            compile(text, path, "exec")
            refs.append("resolution:python_syntax_ok")
        except SyntaxError as exc:
            return False, [f"python_syntax_error:{exc.msg}"]

    refs.append(f"resolution:structural_ok:{path}")
    return True, refs


def verify_no_unmerged_in_scope(
    repo_root: Path,
    scope_paths: list[str],
) -> tuple[bool, list[str]]:
    """J: terminal READY requires closed unmerged set in scope."""

    result = subprocess.run(
        ["git", "status", "--porcelain", "-u"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False, ["git_status_failed"]
    unmerged_in_scope: list[str] = []
    scope_set = set(scope_paths)
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        xy = line[:2]
        if "U" in xy or xy in ("AA", "DD", "AU", "UA", "DU", "UD"):
            path = line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            if path in scope_set:
                unmerged_in_scope.append(path)
    if unmerged_in_scope:
        return False, [f"unmerged_remain:{','.join(unmerged_in_scope)}"]
    return True, ["candidate:no_unmerged_in_scope"]


def verify_candidate(
    repo_root: Path,
    manifest: ConflictManifest,
    resolved_paths: list[str],
    ledger: list[ResolutionLedgerEntry],
    prior_evidence_hashes: dict[str, str],
) -> tuple[bool, list[str], dict[str, str]]:
    """B. CANDIDATE_VERIFICATION — bind to exact candidate."""

    refs: list[str] = []
    new_evidence: dict[str, str] = dict(prior_evidence_hashes)

    fp = manifest.fingerprint
    refs.append(f"candidate:fingerprint:{fp}")

    ok_scope, scope_refs = verify_no_unmerged_in_scope(repo_root, resolved_paths)
    refs.extend(scope_refs)
    if not ok_scope:
        return False, refs, new_evidence

    # H: invalidate implementation-dependent evidence for affected paths
    for entry in ledger:
        semantic_classes = (
            ResolutionClass.AI_SEMANTIC.value,
            "AI_SEMANTIC",
            ResolutionClass.AUTO_SAFE.value,
            "AUTO_SAFE",
        )
        if entry.resolution_class in semantic_classes:
            old_key = f"pre_resolution:{entry.path}"
            if old_key in prior_evidence_hashes:
                refs.append(f"evidence_invalidated:{old_key}")
                new_evidence.pop(old_key, None)

        target = repo_root / entry.path
        if target.is_file():
            content_hash = hashlib.sha256(target.read_bytes()).hexdigest()
            key = f"post_resolution:{entry.path}"
            new_evidence[key] = content_hash
            refs.append(f"candidate:bound:{key}:{content_hash}")

    refs.append("candidate:verification_complete")
    return True, refs, new_evidence


def detect_logical_conflict_in_cluster(
    repo_root: Path,
    paths: list[str],
    auto_merged: list[str],
) -> tuple[bool, str]:
    """F: bounded logical conflict — producer/consumer contract mismatch."""

    producer_defs: dict[str, set[str]] = {}
    for cluster_path in paths:
        defs: set[str] = set()
        for stage in (2, 3):
            content = read_stage_content(repo_root, cluster_path, stage)
            if content:
                defs.update(_DEF_RE.findall(content))
        p = repo_root / cluster_path
        if p.is_file():
            defs.update(_DEF_RE.findall(p.read_text(encoding="utf-8", errors="replace")))
        producer_defs[cluster_path] = defs

    related_files: list[str] = []
    # Same-directory relatedness only (siblings). Do not scan the whole merge
    # auto-merged set — that produces cross-domain false positives.
    cluster_dirs: set[str] = set()
    for cluster_path in paths:
        if "/" in cluster_path:
            cluster_dirs.add(cluster_path.rsplit("/", 1)[0])
    for am in auto_merged:
        am_dir = am.rsplit("/", 1)[0] if "/" in am else ""
        if am_dir in cluster_dirs:
            related_files.append(am)
    for d in cluster_dirs:
        dir_path = repo_root / d
        if dir_path.is_dir():
            for f in dir_path.glob("*.py"):
                rel = f.relative_to(repo_root).as_posix()
                if rel not in paths and rel not in related_files:
                    related_files.append(rel)

    for am in related_files:
        if not am.endswith(".py"):
            continue
        # Cluster members are producers under check, not external consumers.
        if am in paths:
            continue
        p = repo_root / am
        if not p.is_file():
            continue
        consumer_text = p.read_text(encoding="utf-8", errors="replace")
        # Strip string/bytes literals so fixture/demo source embedded in tests
        # does not look like live producer API calls.
        code_only = re.sub(
            r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"\\]*(?:\\.[^"\\]*)*"|'
            r"\'[^\'\\]*(?:\\.[^\'\\]*)*\'|b\"[^\"\\]*(?:\\.[^\"\\]*)*\"|"
            r"b\'[^\'\\]*(?:\\.[^\'\\]*)*\')",
            '""',
            consumer_text,
        )
        calls = set(_CALL_RE.findall(code_only))
        # Local defs in the consumer are not producer API dependencies.
        local_defs = set(_DEF_RE.findall(consumer_text))
        calls -= local_defs
        # filter common keywords
        keywords = {"if", "for", "while", "def", "return", "print", "len", "str", "int"}
        calls -= keywords

        # Skip test modules for the loose api-name heuristic: fixture helpers
        # (WBApi, *_api_*) are not producer contracts of sibling conflict files.
        if am.startswith("tests/") or "/tests/" in am:
            continue
        am_dir = am.rsplit("/", 1)[0] if "/" in am else ""
        for cluster_path, defs in producer_defs.items():
            prod_dir = cluster_path.rsplit("/", 1)[0] if "/" in cluster_path else ""
            # Only same-directory producer/consumer pairs.
            if am_dir != prod_dir:
                continue
            for call in calls:
                if call in defs:
                    continue
                if ("api" in call.lower() or call.endswith("_api")) and defs:
                    if call not in defs:
                        return True, (
                            f"logical:consumer_calls_missing_api:"
                            f"{am}:{call}:producer:{cluster_path}"
                        )
        # marker in related cluster path
        for cluster_path in paths:
            if cluster_path.endswith(".py"):
                cp = repo_root / cluster_path
                if cp.is_file() and has_unresolved_merge_markers(
                    cp.read_text(encoding="utf-8", errors="replace")
                ):
                    if am in auto_merged:
                        return True, f"logical:marker_in_related:{cluster_path}"
    return False, ""