# -*- coding: utf-8 -*-
"""Filesystem write-boundary enforcement via before/after snapshot (BF-003)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


def _file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class FsSnapshot:
    """Map of relative path → sha256 for files under root."""

    root: Path
    digests: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def take(cls, root: Path, ignore_dirs: Optional[Set[str]] = None) -> "FsSnapshot":
        ignore_dirs = ignore_dirs or {".git", "__pycache__"}
        root = Path(root)
        digests: Dict[str, str] = {}
        if not root.exists():
            return cls(root=root, digests={})
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if any(part in ignore_dirs for part in p.parts):
                continue
            rel = str(p.relative_to(root)).replace("\\", "/")
            digests[rel] = _file_digest(p)
        return cls(root=root, digests=digests)


@dataclass
class FsDiff:
    created: List[str]
    modified: List[str]
    deleted: List[str]

    @property
    def all_touched(self) -> List[str]:
        return sorted(set(self.created) | set(self.modified) | set(self.deleted))


def diff_snapshots(before: FsSnapshot, after: FsSnapshot) -> FsDiff:
    b, a = before.digests, after.digests
    created = sorted(set(a) - set(b))
    deleted = sorted(set(b) - set(a))
    modified = sorted(p for p in (set(a) & set(b)) if a[p] != b[p])
    return FsDiff(created=created, modified=modified, deleted=deleted)


# Worker allowlists relative to case/proof root
WORKER_ALLOWLISTS: Dict[str, List[str]] = {
    "MATERIALIZER": [
        "intakes/",
        "findings/",
        "CASE.md",
        "LEDGER.md",
        "team/packets/",
        "team/heartbeats/",
        "results/PROOF-",
    ],
    "CLAIM_WORKER": [
        "findings/",
        "CASE.md",
        "LEDGER.md",
        "intakes/",
        "team/packets/",
        "team/heartbeats/",
        "results/PROOF-",
    ],
    "CLASSIFIER": [
        "results/ROUTE-TRACE.jsonl",
        "LEDGER.md",
        "team/packets/",
        "team/heartbeats/",
        "results/PROOF-",
    ],
    "SPEC_UPDATE_WORKER": [
        "results/TASK-DELTA-",
        "team/packets/",
        "team/heartbeats/",
        "results/",
    ],
    "RED_TEST_WORKER": [
        "results/RED-",
        "LEDGER.md",
        "findings/",
        "team/packets/",
        "team/heartbeats/",
        "results/",
    ],
    "IMPLEMENTATION_EXECUTOR": [
        "results/FIX-",
        "team/packets/",
        "team/heartbeats/",
        "results/",
        # Local uncommitted worktree writes after valid RED (V7)
        "app/",
        "tests/",
        "openspec/changes/",
        ".cursor/rules/",
    ],
    "GREEN_VERIFIER": ["results/GREEN-", "team/packets/", "team/heartbeats/", "results/"],
    "TASK_COMPLETION_WORKER": [
        "results/TASK-COMPLETION-",
        "team/packets/",
        "team/heartbeats/",
        "results/",
    ],
    "BOUNDED_HUNTER": ["findings/", "team/packets/", "team/heartbeats/", "results/"],
    "FAN_IN_ASSEMBLER": ["results/FANIN.md"],  # ONLY (legacy ACTIVE_V1)
    "FAMILY_FAN_IN_ASSEMBLER": [
        "results/FAMILY-FANIN.md",
        "results/FAMILY-FANIN.json",
        # write_family_fanin updates FAMILY_STATUS → FANIN_READY
        "family/FAMILY.json",
        "team/packets/",
        "team/heartbeats/",
    ],
    "INVARIANT_CAPTURE_WORKER": [
        # Full family skeleton + invariant proof (V9): INVARIANT.md/.json,
        # ROOT-GREEN-PROOF.json, FAMILY.json, DEPENDENCIES/INTEGRATION/
        # BRANCHES/LEARNING_PACKET, plus optional ROOT-GREEN-REUSED marker.
        "family/",
        "results/ROOT-GREEN-REUSED-",
        "team/packets/",
        "team/heartbeats/",
    ],
    "RELATION_CLASSIFIER": [
        "findings/",
        "family/",
        "results/LINKED-CASE-",
        "results/OUT-OF-SCOPE-",
        "results/INCONCLUSIVE-",
        "team/packets/",
        "team/heartbeats/",
    ],
    "INTEGRATION_OPERATOR": [
        "family/INTEGRATION.json",
        "family/DEPENDENCIES.json",
        "family/FAMILY.json",
        "family/BRANCHES.jsonl",
        "branches/",
        "results/FAMILY-GREEN-REPORT.md",
        "team/packets/",
        "team/heartbeats/",
    ],
    "FAMILY_LEARNING_WORKER": [
        "family/LEARNING_DECISION.json",
        "family/LEARNING_PACKET.json",
        "family/FAMILY.json",
        "results/LEARNING_DECISION.json",
        "results/LEARNING_REPORT.md",
        "team/packets/",
        "team/heartbeats/",
    ],
    "CLOSURE_OPERATOR": [
        "results/OWNER-CLOSURE-",
        "results/HUMAN_SUMMARY.md",
        "results/CLOSURE-",
        "results/ROUTE-TRACE.jsonl",
        "CASE.md",
        "LEDGER.md",
        "findings/",
        "INDEX.md",
        "family/",
        "team/packets/",
        "team/heartbeats/",
        "results/",
    ],
}


def path_allowed(worker_id: str, rel_path: str) -> bool:
    rel = rel_path.replace("\\", "/")
    # Ignore orchestrator-owned team DISPATCH/CHECKPOINT updates if worker
    # somehow touches them — for FAN_IN still forbidden
    allow = WORKER_ALLOWLISTS.get(worker_id, [])
    if worker_id == "FAN_IN_ASSEMBLER":
        return rel == "results/FANIN.md" or rel.endswith("/results/FANIN.md")
    if worker_id == "CLOSURE_OPERATOR":
        allowed_exact = {
            "results/HUMAN_SUMMARY.md",
            "CASE.md",
            "LEDGER.md",
            "INDEX.md",
            "results/ROUTE-TRACE.jsonl",
        }
        if rel in allowed_exact or any(rel.endswith("/" + x) for x in allowed_exact):
            return True
        if rel.startswith("results/OWNER-CLOSURE-") or "/results/OWNER-CLOSURE-" in rel:
            return True
        if rel.startswith("findings/") or "/findings/" in rel:
            return True
        if rel.startswith("results/CLOSURE-") or "/results/CLOSURE-" in rel:
            return True
        if rel.startswith("team/packets/") or rel.startswith("team/heartbeats/"):
            return True
        if rel.startswith("family/") or "/family/" in rel:
            return True
        if (rel.startswith("results/") or "/results/" in rel) and "FANIN.md" not in rel:
            return True
        return False
    for prefix in allow:
        if rel == prefix.rstrip("/") or rel.startswith(prefix) or prefix.rstrip("/") in rel:
            # Prefer prefix match
            if rel.startswith(prefix) or rel == prefix.rstrip("/"):
                return True
            if prefix.endswith("-") and prefix in rel:
                return True
    # team/packets and heartbeats for any non-fanin worker output are ok if listed
    if rel.startswith("team/packets/") or rel.startswith("team/heartbeats/"):
        return worker_id != "FAN_IN_ASSEMBLER" or False
    return False


def evaluate_write_boundary(
    worker_id: str,
    fs_diff: FsDiff,
    *,
    case_rel_prefix: str = "",
    ignore_prefixes: Optional[List[str]] = None,
) -> Tuple[str, List[str]]:
    """Return (PASS|VIOLATION|UNRESOLVED, violating_paths).

    Transport channels (team/packets, team/heartbeats) are ignored — they are
    orchestrator-mandated I/O, not business writes. FAN_IN business write remains
    only results/FANIN.md.
    """
    ignore_prefixes = ignore_prefixes or [
        "team/packets/",
        "team/heartbeats/",
        "team/DISPATCH.jsonl",
        "team/CHECKPOINT.json",
        "team/CHECKPOINT.md",
        "team/intents/",
        "team/snapshots/",
        # V10 host-owned identity / retry authority (written by finalize, not workers)
        "team/executions/",
        "team/retries/",
        "gates/",
        "results/ROUTE-TRACE.jsonl",
    ]
    violations: List[str] = []
    for rel in fs_diff.all_touched:
        check = rel
        if case_rel_prefix and rel.startswith(case_rel_prefix):
            check = rel[len(case_rel_prefix) :].lstrip("/")
        check_norm = check.replace("\\", "/")
        if any(check_norm == p or check_norm.startswith(p) for p in ignore_prefixes):
            continue
        if not path_allowed(worker_id, check_norm):
            violations.append(rel)
    if violations:
        return "VIOLATION", violations
    return "PASS", []


def write_boundary_report(
    path: Path,
    *,
    worker_id: str,
    result: str,
    violations: List[str],
    fs_diff: FsDiff,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "WORKER_ID": worker_id,
                "WRITE_BOUNDARY_RESULT": result,
                "VIOLATIONS": violations,
                "CREATED": fs_diff.created,
                "MODIFIED": fs_diff.modified,
                "DELETED": fs_diff.deleted,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
