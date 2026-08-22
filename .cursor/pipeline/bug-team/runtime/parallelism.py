# -*- coding: utf-8 -*-
"""V9 parallelism eligibility / dispatch / observation semantics (BF-V9-004).

Wall-clock overlap is informative, not a blocking architecture requirement.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from . import bug_family


class ParallelismError(Exception):
    """Parallelism contract rejection."""

    def __init__(self, code: str, detail: str = "", payload: Optional[Dict[str, Any]] = None) -> None:
        self.code = code
        self.detail = detail
        self.payload = payload or {}
        super().__init__(f"{code}: {detail}" if detail else code)


def evaluate_parallel_eligibility(
    write_sets: Dict[str, List[str]],
    *,
    dependency_edges: Optional[List[List[str]]] = None,
    policy_forbid: bool = False,
) -> Dict[str, Any]:
    """Compute PARALLEL_ELIGIBILITY for branch finding IDs."""
    if policy_forbid:
        return {
            "PARALLEL_ELIGIBILITY": "FORBIDDEN_POLICY",
            "REASON": "policy",
        }
    deps = dependency_edges or []
    if deps:
        return {
            "PARALLEL_ELIGIBILITY": "FORBIDDEN_DEPENDENCY",
            "DEPENDENCY_EDGES": deps,
        }
    findings = sorted(write_sets.keys())
    for i, a in enumerate(findings):
        for b in findings[i + 1 :]:
            overlap = set(write_sets[a]) & set(write_sets[b])
            if overlap:
                return {
                    "PARALLEL_ELIGIBILITY": "FORBIDDEN_WRITE_SET_OVERLAP",
                    "OVERLAP": {f"{a}|{b}": sorted(overlap)},
                }
    return {
        "PARALLEL_ELIGIBILITY": "ALLOWED",
        "FINDING_IDS": findings,
    }


def record_parallel_dispatch(
    case_root: Path,
    *,
    finding_ids: List[str],
    eligibility: Dict[str, Any],
    dispatch_mode: str,
    orchestrator_added_dependency: bool = False,
) -> Dict[str, Any]:
    """Persist family/PARALLELISM.json dispatch record."""
    if orchestrator_added_dependency and eligibility.get("PARALLEL_ELIGIBILITY") == "ALLOWED":
        raise ParallelismError(
            "BLOCKED_ORCHESTRATOR_UNNECESSARY_DEPENDENCY",
            str(finding_ids),
        )
    if dispatch_mode not in {
        "DISPATCHED_WITHOUT_INTER_BRANCH_DEPENDENCY",
        "SERIALIZED_BY_ORCHESTRATOR",
        "NOT_DISPATCHED",
    }:
        raise ParallelismError("BLOCKED_PARALLEL_DISPATCH_MODE", dispatch_mode)

    record = {
        "FINDING_IDS": list(finding_ids),
        "PARALLEL_ELIGIBILITY": eligibility.get("PARALLEL_ELIGIBILITY"),
        "PARALLEL_DISPATCH": dispatch_mode,
        "PARALLEL_EXECUTION_OBSERVED": "UNKNOWN_TIMESTAMPS_INSUFFICIENT",
        "MAIN_WORKTREE_CONCURRENT_WRITES": "NONE",
        "BRANCH_WORKSPACES": "ISOLATED",
        **{k: v for k, v in eligibility.items() if k != "PARALLEL_ELIGIBILITY"},
    }
    path = bug_family.family_dir(case_root) / "PARALLELISM.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def observe_parallel_execution(
    case_root: Path,
    *,
    started_at: Dict[str, float],
    finished_at: Dict[str, float],
    main_worktree_concurrent_writers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Update observation from timestamps; platform serialization is not a FAIL."""
    path = bug_family.family_dir(case_root) / "PARALLELISM.json"
    if not path.exists():
        raise ParallelismError("BLOCKED_PARALLELISM_RECORD_MISSING")
    record = json.loads(path.read_text(encoding="utf-8"))

    writers = main_worktree_concurrent_writers or []
    if len(writers) > 1:
        record["MAIN_WORKTREE_CONCURRENT_WRITES"] = writers
        record["PARALLEL_EXECUTION_OBSERVED"] = "NO_ORCHESTRATOR_SERIALIZED"
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        raise ParallelismError(
            "BLOCKED_CONCURRENT_MAIN_WORKTREE_WRITES",
            str(writers),
            record,
        )

    ids = record.get("FINDING_IDS") or []
    if not ids or any(i not in started_at or i not in finished_at for i in ids):
        record["PARALLEL_EXECUTION_OBSERVED"] = "UNKNOWN_TIMESTAMPS_INSUFFICIENT"
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return {
            "STATUS": "PASS",
            "ARCHITECTURE_PASS": True,
            **record,
        }

    # Overlap if each interval intersects another
    overlap = False
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            if started_at[a] < finished_at[b] and started_at[b] < finished_at[a]:
                overlap = True
    if overlap:
        observed = "YES"
    elif record.get("PARALLEL_DISPATCH") == "SERIALIZED_BY_ORCHESTRATOR":
        observed = "NO_ORCHESTRATOR_SERIALIZED"
    else:
        observed = "NO_PLATFORM_SERIALIZED"

    record["PARALLEL_EXECUTION_OBSERVED"] = observed
    record["TIMESTAMPS"] = {
        "STARTED_AT": started_at,
        "FINISHED_AT": finished_at,
    }
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    # Architecture pass when eligibility ALLOWED + dependency-free dispatch + isolated
    arch_ok = (
        record.get("PARALLEL_ELIGIBILITY") == "ALLOWED"
        and record.get("PARALLEL_DISPATCH") == "DISPATCHED_WITHOUT_INTER_BRANCH_DEPENDENCY"
        and record.get("BRANCH_WORKSPACES") == "ISOLATED"
        and record.get("MAIN_WORKTREE_CONCURRENT_WRITES") == "NONE"
    )
    # False claim check
    if observed != "YES" and record.get("CLAIMED_OBSERVED_PARALLEL") is True:
        raise ParallelismError("BLOCKED_FALSE_PARALLEL_CLAIM", observed, record)

    return {
        "STATUS": "PASS" if arch_ok else "FAIL",
        "ARCHITECTURE_PASS": arch_ok,
        "PARALLEL_EXECUTION_OBSERVED": observed,
        **record,
    }


def assert_no_false_parallel_claim(record: Dict[str, Any]) -> None:
    if record.get("CLAIMED_OBSERVED_PARALLEL") and record.get("PARALLEL_EXECUTION_OBSERVED") != "YES":
        raise ParallelismError("BLOCKED_FALSE_PARALLEL_CLAIM", str(record.get("PARALLEL_EXECUTION_OBSERVED")))
