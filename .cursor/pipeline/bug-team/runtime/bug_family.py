# -*- coding: utf-8 -*-
"""Durable Bug Family data model (Corrective V8 shadow candidate).

Artifacts live under ``<case_root>/family/`` (or proof case family/).
Does not activate family fanout as the default ACTIVE_V1 path.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from . import family_policy


class BugFamilyError(Exception):
    """Bug-family model rejection."""

    def __init__(self, code: str, detail: str = "", payload: Optional[Dict[str, Any]] = None) -> None:
        self.code = code
        self.detail = detail
        self.payload = payload or {}
        super().__init__(f"{code}: {detail}" if detail else code)


def family_dir(case_root: Path) -> Path:
    return Path(case_root) / "family"


def branches_dir(case_root: Path) -> Path:
    return Path(case_root) / "branches"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def create_family(
    case_root: Path,
    *,
    case_id: str,
    root_finding_id: str,
    invariant_id: Optional[str] = None,
    fanout_generation: int = 1,
) -> Dict[str, Any]:
    """Create durable family artifacts skeleton."""
    case_root = Path(case_root)
    fdir = family_dir(case_root)
    fdir.mkdir(parents=True, exist_ok=True)
    branches_dir(case_root).mkdir(parents=True, exist_ok=True)
    inv_id = invariant_id or f"INV/{case_id}/{uuid.uuid4().hex[:8]}"
    family_id = f"BFAM/{case_id}/{uuid.uuid4().hex[:8]}"
    now = _now()
    family = {
        "BUG_FAMILY_ID": family_id,
        "CASE_ID": case_id,
        "INVARIANT_ID": inv_id,
        "INVARIANT_VERSION": 1,
        "ROOT_FINDING_ID": root_finding_id,
        "MEMBER_FINDING_IDS": [root_finding_id],
        "FANOUT_GENERATION": fanout_generation,
        "FAMILY_STATUS": "OPEN",
        "INTEGRATION_STATUS": "NOT_STARTED",
        "LEARNING_STATUS": "NOT_STARTED",
        "CREATED_AT": now,
        "UPDATED_AT": now,
        "V8_IMPLEMENTATION": "SHADOW_CANDIDATE",
    }
    _write_json(fdir / "FAMILY.json", family)
    _write_json(
        fdir / "DEPENDENCIES.json",
        {
            "BUG_FAMILY_ID": family_id,
            "WRITE_SET_CONFLICTS": [],
            "SERIALIZATION_ORDER": [],
            "PARALLEL_ALLOWED_PAIRS": [],
            "UPDATED_AT": now,
        },
    )
    _write_json(
        fdir / "INTEGRATION.json",
        {
            "BUG_FAMILY_ID": family_id,
            "INTEGRATION_STATUS": "NOT_STARTED",
            "APPLIED_PATCHES": [],
            "CONFLICTS": [],
            "UPDATED_AT": now,
        },
    )
    (fdir / "BRANCHES.jsonl").write_text("", encoding="utf-8")
    _write_json(
        fdir / "LEARNING_PACKET.json",
        {
            "BUG_FAMILY_ID": family_id,
            "LEARNING_STATUS": "NOT_STARTED",
            "UPDATED_AT": now,
        },
    )
    return family


def load_family(case_root: Path) -> Dict[str, Any]:
    path = family_dir(case_root) / "FAMILY.json"
    if not path.exists():
        raise BugFamilyError("BLOCKED_FAMILY_MISSING", str(path))
    return _read_json(path)


def save_family(case_root: Path, family: Dict[str, Any]) -> Dict[str, Any]:
    family = dict(family)
    family["UPDATED_AT"] = _now()
    _write_json(family_dir(case_root) / "FAMILY.json", family)
    return family


def update_family_status(
    case_root: Path,
    *,
    family_status: Optional[str] = None,
    integration_status: Optional[str] = None,
    learning_status: Optional[str] = None,
) -> Dict[str, Any]:
    family = load_family(case_root)
    if family_status is not None:
        family["FAMILY_STATUS"] = family_status
    if integration_status is not None:
        family["INTEGRATION_STATUS"] = integration_status
    if learning_status is not None:
        family["LEARNING_STATUS"] = learning_status
    return save_family(case_root, family)


def append_branch(case_root: Path, branch: Dict[str, Any]) -> Dict[str, Any]:
    """Append one branch record to BRANCHES.jsonl and update MEMBER_FINDING_IDS."""
    required = (
        "BRANCH_ID",
        "FINDING_ID",
        "RELATION_TO_INVARIANT",
        "BLOCKS_FAMILY_CLOSURE",
        "BRANCH_STATUS",
    )
    for key in required:
        if key not in branch:
            raise BugFamilyError("BLOCKED_BRANCH_SCHEMA", key)
    path = family_dir(case_root) / "BRANCHES.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(branch, ensure_ascii=False) + "\n")
    family = load_family(case_root)
    fid = branch["FINDING_ID"]
    members = list(family.get("MEMBER_FINDING_IDS") or [])
    if fid not in members and branch.get("RELATION_TO_INVARIANT") == "SAME_INVARIANT_FINDING":
        members.append(fid)
        family["MEMBER_FINDING_IDS"] = members
        save_family(case_root, family)
    return branch


def list_branches(case_root: Path) -> List[Dict[str, Any]]:
    path = family_dir(case_root) / "BRANCHES.jsonl"
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def upsert_branch(case_root: Path, branch: Dict[str, Any]) -> Dict[str, Any]:
    """Replace branch line for FINDING_ID (rewrite jsonl)."""
    rows = list_branches(case_root)
    found = False
    out: List[Dict[str, Any]] = []
    for row in rows:
        if row.get("FINDING_ID") == branch.get("FINDING_ID"):
            merged = {**row, **branch}
            out.append(merged)
            found = True
            branch = merged
        else:
            out.append(row)
    if not found:
        out.append(branch)
    path = family_dir(case_root) / "BRANCHES.jsonl"
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out),
        encoding="utf-8",
    )
    return branch


def new_branch_record(
    *,
    finding_id: str,
    source_hunt_id: Optional[str],
    relation: str,
    blocks_closure: bool,
    classification: Optional[str] = None,
    chosen_route: Optional[str] = None,
    dependency_finding_ids: Optional[List[str]] = None,
    expected_changed_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "BRANCH_ID": f"BR/{finding_id}/{uuid.uuid4().hex[:8]}",
        "FINDING_ID": finding_id,
        "SOURCE_HUNT_ID": source_hunt_id,
        "RELATION_TO_INVARIANT": relation,
        "BLOCKS_FAMILY_CLOSURE": blocks_closure,
        "DEPENDENCY_FINDING_IDS": dependency_finding_ids or [],
        "CLASSIFICATION": classification,
        "CHOSEN_ROUTE": chosen_route,
        "BRANCH_STATUS": "PENDING",
        "RED_STATUS": None,
        "IMPLEMENTATION_STATUS": None,
        "GREEN_STATUS": None,
        "INTEGRATION_STATUS": "NOT_STARTED",
        "WORKER_EXECUTION_IDS": [],
        "EXPECTED_CHANGED_PATHS": expected_changed_paths or [],
        "ACTUAL_CHANGED_PATHS": [],
        "CREATED_AT": _now(),
        "UPDATED_AT": _now(),
    }


def blocking_open_branches(case_root: Path) -> List[Dict[str, Any]]:
    terminal = {
        "GREEN_CONFIRMED",
        "TASK_COMPLETE",
        "INTEGRATED",
        "REJECTED_FALSE_POSITIVE",
        "HANDED_OFF_OUT_OF_SCOPE",
    }
    # GREEN_FAILED / RED_FAILED / BLOCKED remain open-blocking
    out = []
    for b in list_branches(case_root):
        if not b.get("BLOCKS_FAMILY_CLOSURE"):
            continue
        status = b.get("BRANCH_STATUS")
        if status not in terminal:
            out.append(b)
    return out


def write_set_overlap(paths_a: Iterable[str], paths_b: Iterable[str]) -> Set[str]:
    return set(paths_a) & set(paths_b)


def record_write_set_plan(
    case_root: Path,
    branch_write_sets: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Detect overlapping write sets and record DEPENDENCIES.json."""
    findings = sorted(branch_write_sets.keys())
    conflicts: List[Dict[str, Any]] = []
    parallel_pairs: List[List[str]] = []
    for i, a in enumerate(findings):
        for b in findings[i + 1 :]:
            overlap = sorted(write_set_overlap(branch_write_sets[a], branch_write_sets[b]))
            if overlap:
                conflicts.append(
                    {
                        "FINDING_A": a,
                        "FINDING_B": b,
                        "OVERLAPPING_PATHS": overlap,
                        "PARALLEL_MAIN_WORKTREE_WRITES": "FORBIDDEN",
                    }
                )
            else:
                parallel_pairs.append([a, b])
    # Deterministic serialization: lexicographic FINDING_ID when conflicts exist
    serialization = sorted(findings) if conflicts else []
    deps = {
        "BUG_FAMILY_ID": load_family(case_root).get("BUG_FAMILY_ID"),
        "WRITE_SETS": branch_write_sets,
        "WRITE_SET_CONFLICTS": conflicts,
        "SERIALIZATION_ORDER": serialization,
        "PARALLEL_ALLOWED_PAIRS": parallel_pairs,
        "PARALLEL_IMPLEMENTATION_ALLOWED": len(conflicts) == 0,
        "UPDATED_AT": _now(),
    }
    _write_json(family_dir(case_root) / "DEPENDENCIES.json", deps)
    return deps


def assert_no_concurrent_overlapping_writes(
    *,
    active_main_writers: List[str],
    write_sets: Dict[str, List[str]],
) -> None:
    """Reject concurrent main-worktree writers with overlapping paths."""
    if len(active_main_writers) <= 1:
        return
    for i, a in enumerate(active_main_writers):
        for b in active_main_writers[i + 1 :]:
            overlap = write_set_overlap(write_sets.get(a, []), write_sets.get(b, []))
            if overlap:
                raise BugFamilyError(
                    "BLOCKED_CONCURRENT_OVERLAPPING_MAIN_WORKTREE_WRITES",
                    f"{a}∩{b}={sorted(overlap)}",
                    {"OVERLAP": sorted(overlap), "WRITERS": active_main_writers},
                )


def policy_relation_types() -> List[str]:
    return list(family_policy.load_policy().get("RELATION_TYPES") or [])
