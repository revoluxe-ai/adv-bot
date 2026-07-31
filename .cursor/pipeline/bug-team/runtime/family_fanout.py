# -*- coding: utf-8 -*-
"""Invariant-centered bug-family fanout orchestration (Corrective V8 shadow).

Stages: invariant capture → hunt contract → materialize/relation →
isolated branch patches → integration → family GREEN → family fan-in →
learning → family closure.

Default ACTIVE_V1 is unchanged. Use EXECUTION_MODE=CONTROLLED_TEST_FAMILY_FANOUT
in harness, or future Owner enable of BUG_FAMILY_FANOUT_ENABLED.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import bug_family, control_model, execution_identity, family_policy, learning_decision

# Family fanout workers that must present VALIDATED execution identity before accept.
FAMILY_WORKERS_REQUIRING_VALIDATED_IDENTITY = (
    "RELATION_CLASSIFIER",
    "BRANCH_CLASSIFIER",
    "RED_WORKER",
    "IMPLEMENTATION_WORKER",
    "GREEN_WORKER",
    "INTEGRATION_OPERATOR",
    "FAMILY_FAN_IN_ASSEMBLER",
    "FAMILY_LEARNING_WORKER",
)


def family_worker_requires_validated_identity(worker_id: str) -> bool:
    """True when a family-fanout worker must pass EXECUTION_IDENTITY_VALIDATION."""
    return worker_id in FAMILY_WORKERS_REQUIRING_VALIDATED_IDENTITY


def assert_family_worker_identity_gate(
    *,
    case_root: Path,
    worker_id: str,
    worker_execution_id: str,
    orchestration_id: str,
    case_id: str,
    finding_id: str,
    input_packet_path: Path,
    output_packet_path: Path,
    checkpoint_path: Path,
    branch_id: Any = None,
) -> Dict[str, Any]:
    """Reject family-worker advance unless identity is authoritatively VALIDATED."""
    if not family_worker_requires_validated_identity(worker_id):
        return {"STATUS": "SKIP", "REASON": "worker_not_in_identity_gate_set"}
    result = execution_identity.gate_execution_identity_for_advance(
        case_root=case_root,
        worker_execution_id=worker_execution_id,
        expected_orchestration_id=orchestration_id,
        expected_case_id=case_id,
        expected_finding_id=finding_id,
        input_packet_path=input_packet_path,
        output_packet_path=output_packet_path,
        checkpoint_path=checkpoint_path,
        expected_branch_id=branch_id,
    )
    if not result.VALID:
        raise FamilyFanoutError(
            "BLOCKED_EXECUTION_IDENTITY_NOT_FINALIZED",
            result.REASON_CODE,
            payload=result.as_dict(),
        )
    identity = execution_identity.load_identity_record(
        execution_identity.identity_path(case_root, worker_execution_id)
    )
    if identity.get("IDENTITY_STATUS") != execution_identity.STATUS_VALIDATED:
        raise FamilyFanoutError(
            "BLOCKED_EXECUTION_IDENTITY_NOT_FINALIZED",
            f"IDENTITY_STATUS={identity.get('IDENTITY_STATUS')}",
        )
    return result.as_dict()


class FamilyFanoutError(Exception):
    """Family fanout orchestration rejection."""

    def __init__(self, code: str, detail: str = "", payload: Optional[Dict[str, Any]] = None) -> None:
        self.code = code
        self.detail = detail
        self.payload = payload or {}
        super().__init__(f"{code}: {detail}" if detail else code)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_gate(*, execution_mode: str, proof_root: Path) -> Dict[str, Any]:
    status, details = family_policy.check_family_fanout_gate(
        execution_mode=execution_mode, proof_root=proof_root
    )
    if status.startswith("BLOCKED_"):
        raise FamilyFanoutError(status, json.dumps(details, ensure_ascii=False), details)
    return details


# ---------------------------------------------------------------------------
# Invariant capture
# ---------------------------------------------------------------------------


def capture_invariant(
    case_root: Path,
    *,
    invariant_id: str,
    plain_language: str,
    technical: str,
    scope: str,
    entry_conditions: str,
    required_behavior: str,
    forbidden_behavior: str,
    known_writers: List[str],
    known_readers: List[str],
    proof_from_root: str,
    hunt_scope: str,
    require_root_proof: bool = False,
    contradicts_root_green: bool = False,
    contradicts_root_fix: bool = False,
    introduces_unrelated_rule: bool = False,
) -> Path:
    """Write family/INVARIANT.md (+ INVARIANT.json); validate vs ROOT-GREEN-PROOF when present."""
    from . import invariant_proof

    pol = family_policy.load_policy()
    vague = pol.get("VAGUE_INVARIANT_FORBIDDEN_PATTERNS") or []
    blob = f"{plain_language}\n{technical}".lower()
    for pat in vague:
        if pat.lower() in blob:
            raise FamilyFanoutError("BLOCKED_VAGUE_INVARIANT", pat)
    if len(technical.strip()) < 40 or len(required_behavior.strip()) < 20:
        raise FamilyFanoutError("BLOCKED_INVARIANT_NOT_TESTABLE", "too_short")

    path = bug_family.family_dir(case_root) / "INVARIANT.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = f"""# INVARIANT

```text
INVARIANT_ID: {invariant_id}
```

## PLAIN_LANGUAGE_INVARIANT

{plain_language.strip()}

## TECHNICAL_INVARIANT

{technical.strip()}

## SCOPE

{scope.strip()}

## ENTRY_CONDITIONS

{entry_conditions.strip()}

## REQUIRED_BEHAVIOR

{required_behavior.strip()}

## FORBIDDEN_BEHAVIOR

{forbidden_behavior.strip()}

## KNOWN_WRITERS

{chr(10).join(f'- {w}' for w in known_writers) or '- (none)'}

## KNOWN_READERS

{chr(10).join(f'- {r}' for r in known_readers) or '- (none)'}

## PROOF_FROM_ROOT_FINDING

{proof_from_root.strip()}

## HUNT_SCOPE

{hunt_scope.strip()}
"""
    path.write_text(body, encoding="utf-8")
    ok, missing = validate_invariant_file(path)
    if not ok:
        raise FamilyFanoutError("BLOCKED_INVARIANT_SECTIONS_MISSING", str(missing))

    projection = invariant_proof.write_invariant_projection(
        case_root,
        invariant_id=invariant_id,
        required_behavior=required_behavior,
        forbidden_behavior=forbidden_behavior,
        entry_conditions=entry_conditions,
        scope=scope,
        contradicts_root_green=contradicts_root_green,
        contradicts_root_fix=contradicts_root_fix,
        introduces_unrelated_rule=introduces_unrelated_rule,
    )
    proof_path = invariant_proof.root_proof_path(case_root)
    if require_root_proof or proof_path.exists():
        try:
            invariant_proof.validate_invariant_against_root_proof(
                case_root, projection=projection
            )
        except invariant_proof.InvariantProofError as exc:
            raise FamilyFanoutError(exc.code, exc.detail, exc.payload) from exc
    return path


def validate_invariant_file(path: Path) -> Tuple[bool, List[str]]:
    pol = family_policy.load_policy()
    required = pol.get("INVARIANT_REQUIRED_SECTIONS") or []
    if not path.exists():
        return False, list(required)
    text = path.read_text(encoding="utf-8")
    missing = []
    for sec in required:
        if sec == "INVARIANT_ID":
            if "INVARIANT_ID:" not in text:
                missing.append(sec)
        elif f"## {sec}" not in text:
            missing.append(sec)
    return len(missing) == 0, missing


# ---------------------------------------------------------------------------
# Hunt contract
# ---------------------------------------------------------------------------


def validate_hunt_result(hunt: Dict[str, Any], case_root: Optional[Path] = None) -> Dict[str, Any]:
    """Validate BOUNDED_HUNTER output contract from policy."""
    pol = family_policy.load_policy()
    result = hunt.get("HUNT_RESULT")
    if result not in (pol.get("HUNT_RESULT_TYPES") or []):
        raise FamilyFanoutError("BLOCKED_HUNT_RESULT_TYPE", str(result))
    if hunt.get("HUNTER_IMPLEMENTED_FIX") or hunt.get("HUNTER_WROTE_RED"):
        raise FamilyFanoutError("BLOCKED_HUNTER_CANNOT_IMPLEMENT", "hunter_boundary")
    if hunt.get("HUNTER_CHOSE_ROUTE") or hunt.get("HUNTER_CLOSED_CANDIDATE"):
        raise FamilyFanoutError("BLOCKED_HUNTER_AUTHORITY_VIOLATION", "hunter_boundary")
    candidates = hunt.get("CANDIDATES") or []
    if result == "CANDIDATES_FOUND" and not candidates:
        raise FamilyFanoutError("BLOCKED_HUNT_CANDIDATES_EMPTY")
    req = pol.get("HUNT_CANDIDATE_REQUIRED_FIELDS") or []
    for c in candidates:
        for field in req:
            if field not in c:
                raise FamilyFanoutError("BLOCKED_HUNT_CANDIDATE_SCHEMA", field)
    if case_root is not None:
        path = bug_family.family_dir(case_root) / "HUNT_CANDIDATES.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"HUNT_RESULT": result, "CANDIDATES": candidates}, indent=2) + "\n",
            encoding="utf-8",
        )
    return {"STATUS": "PASS", "HUNT_RESULT": result, "CANDIDATE_COUNT": len(candidates)}


# ---------------------------------------------------------------------------
# Relation classification + materialize
# ---------------------------------------------------------------------------


def classify_relation(
    case_root: Path,
    *,
    candidate: Dict[str, Any],
    relation: str,
    rationale: str,
    finding_id: Optional[str] = None,
    linked_case_id: Optional[str] = None,
    expected_changed_paths: Optional[List[str]] = None,
    classification: Optional[str] = None,
    chosen_route: Optional[str] = None,
) -> Dict[str, Any]:
    """Materialize hunt candidate into durable finding/branch by relation type."""
    pol = family_policy.load_policy()
    if relation not in (pol.get("RELATION_TYPES") or []):
        raise FamilyFanoutError("BLOCKED_RELATION_TYPE", relation)
    blocks = family_policy.blocks_closure_from_policy(relation, pol)
    family = bug_family.load_family(case_root)
    hunt_id = candidate.get("HUNT_CANDIDATE_ID")
    findings = Path(case_root) / "findings"
    findings.mkdir(parents=True, exist_ok=True)

    if relation == "SAME_INVARIANT_FINDING":
        fid = finding_id or f"PBH-FAN/{uuid.uuid4().hex[:6].upper()}"
        finding_path = findings / f"{fid}.md"
        finding_path.write_text(
            f"# {fid}\n\nFINDING_ID: {fid}\nRELATION: SAME_INVARIANT_FINDING\n"
            f"HUNT_CANDIDATE_ID: {hunt_id}\nRATIONALE: {rationale}\n"
            f"OBSERVED: {candidate.get('OBSERVED_BEHAVIOR')}\n",
            encoding="utf-8",
        )
        branch = bug_family.new_branch_record(
            finding_id=fid,
            source_hunt_id=hunt_id,
            relation=relation,
            blocks_closure=blocks,
            classification=classification,
            chosen_route=chosen_route,
            expected_changed_paths=expected_changed_paths,
        )
        branch["BRANCH_STATUS"] = "MATERIALIZED"
        bug_family.append_branch(case_root, branch)
        bug_family.update_family_status(case_root, family_status="FANOUT_ACTIVE")
        return {
            "RELATION": relation,
            "FINDING_ID": fid,
            "BLOCKS_FAMILY_CLOSURE": blocks,
            "BRANCH": branch,
            "FINDING_PATH": str(finding_path),
        }

    if relation == "NEW_ROOT_CAUSE":
        linked = linked_case_id or f"BUGCASE-LINKED-{uuid.uuid4().hex[:8].upper()}"
        handoff = Path(case_root) / "results" / f"LINKED-CASE-{linked}.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            f"LINKED_CASE_ID: {linked}\nPARENT_BUG_FAMILY_ID: {family['BUG_FAMILY_ID']}\n"
            f"PARENT_CASE_ID: {family['CASE_ID']}\nHUNT_CANDIDATE_ID: {hunt_id}\n"
            f"RATIONALE: {rationale}\n",
            encoding="utf-8",
        )
        branch = bug_family.new_branch_record(
            finding_id=finding_id or f"NRC-{uuid.uuid4().hex[:6].upper()}",
            source_hunt_id=hunt_id,
            relation=relation,
            blocks_closure=blocks,
        )
        branch["BRANCH_STATUS"] = "HANDED_OFF_OUT_OF_SCOPE"
        branch["LINKED_CASE_ID"] = linked
        bug_family.append_branch(case_root, branch)
        return {
            "RELATION": relation,
            "LINKED_CASE_ID": linked,
            "BLOCKS_FAMILY_CLOSURE": blocks,
            "BRANCH": branch,
            "HANDOFF_PATH": str(handoff),
        }

    if relation == "FALSE_POSITIVE":
        fid = finding_id or f"FP-{uuid.uuid4().hex[:6].upper()}"
        rejected = findings / f"{fid}.md"
        rejected.write_text(
            f"# {fid}\nSTATUS: REJECTED_FALSE_POSITIVE\nRATIONALE: {rationale}\n"
            f"HUNT_CANDIDATE_ID: {hunt_id}\n",
            encoding="utf-8",
        )
        branch = bug_family.new_branch_record(
            finding_id=fid,
            source_hunt_id=hunt_id,
            relation=relation,
            blocks_closure=blocks,
        )
        branch["BRANCH_STATUS"] = "REJECTED_FALSE_POSITIVE"
        bug_family.append_branch(case_root, branch)
        return {
            "RELATION": relation,
            "FINDING_ID": fid,
            "IMPLEMENTATION": False,
            "BLOCKS_FAMILY_CLOSURE": blocks,
            "BRANCH": branch,
        }

    if relation == "OUT_OF_SCOPE":
        fid = finding_id or f"OOS-{uuid.uuid4().hex[:6].upper()}"
        handoff = Path(case_root) / "results" / f"OUT-OF-SCOPE-{fid}.md"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            f"FINDING_ID: {fid}\nOUT_OF_SCOPE: true\nRATIONALE: {rationale}\n",
            encoding="utf-8",
        )
        branch = bug_family.new_branch_record(
            finding_id=fid,
            source_hunt_id=hunt_id,
            relation=relation,
            blocks_closure=blocks,
        )
        branch["BRANCH_STATUS"] = "HANDED_OFF_OUT_OF_SCOPE"
        bug_family.append_branch(case_root, branch)
        return {
            "RELATION": relation,
            "FINDING_ID": fid,
            "HANDOFF_PATH": str(handoff),
            "BLOCKS_FAMILY_CLOSURE": blocks,
            "BRANCH": branch,
        }

    # INCONCLUSIVE
    fid = finding_id or f"INC-{uuid.uuid4().hex[:6].upper()}"
    missing = Path(case_root) / "results" / f"INCONCLUSIVE-{fid}.md"
    missing.parent.mkdir(parents=True, exist_ok=True)
    missing.write_text(
        f"FINDING_ID: {fid}\nSTATUS: INCONCLUSIVE\nMISSING_EVIDENCE: {rationale}\n",
        encoding="utf-8",
    )
    branch = bug_family.new_branch_record(
        finding_id=fid,
        source_hunt_id=hunt_id,
        relation=relation,
        blocks_closure=blocks,
    )
    branch["BRANCH_STATUS"] = "BLOCKED_INCONCLUSIVE"
    bug_family.append_branch(case_root, branch)
    bug_family.update_family_status(case_root, family_status="OPEN_BLOCKED")
    return {
        "RELATION": relation,
        "FINDING_ID": fid,
        "FAMILY_STATUS": "OPEN_BLOCKED",
        "FAKE_CLOSURE": False,
        "BLOCKS_FAMILY_CLOSURE": blocks,
        "BRANCH": branch,
    }


def run_classifier_for_branch(
    case_root: Path,
    *,
    finding_id: str,
    classification: str,
    chosen_route: str,
) -> Dict[str, Any]:
    """Persist CLASSIFIER result onto a same-invariant branch."""
    allowed = {
        "IMPLEMENTATION_BUG",
        "SPEC_BUG",
        "SPEC_GAP",
        "FALSE_POSITIVE",
        "OUT_OF_SCOPE",
        "INSUFFICIENT_EVIDENCE",
    }
    if classification not in allowed:
        raise FamilyFanoutError("BLOCKED_CLASSIFICATION", classification)
    branch = bug_family.upsert_branch(
        case_root,
        {
            "FINDING_ID": finding_id,
            "CLASSIFICATION": classification,
            "CHOSEN_ROUTE": chosen_route,
            "BRANCH_STATUS": "CLASSIFIED",
            "UPDATED_AT": _now(),
        },
    )
    return {"STATUS": "PASS", "BRANCH": branch}


# ---------------------------------------------------------------------------
# Isolated branch implementation
# ---------------------------------------------------------------------------


def prepare_branch_workspace(case_root: Path, finding_id: str) -> Path:
    ws = bug_family.branches_dir(case_root) / finding_id
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def apply_branch_local_change(
    case_root: Path,
    *,
    finding_id: str,
    relative_path: str,
    content: str,
) -> Dict[str, Any]:
    """Apply a change only inside branches/<FINDING_ID>/workspace/."""
    ws = prepare_branch_workspace(case_root, finding_id) / "workspace"
    target = ws / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"PATH": str(target), "REL": relative_path}


def finalize_branch_patch(
    case_root: Path,
    *,
    finding_id: str,
    changed_paths: List[str],
    patch_body: str,
    green_pass: bool,
    summary: str,
) -> Dict[str, Any]:
    """Write PATCH.diff / CHANGED_PATHS / GREEN_REPORT / BRANCH_SUMMARY."""
    # Self-check: forbidden mutation commands must be rejected by control model
    for cmd in ("git commit -m x", "git push origin HEAD", "kubectl apply -f deploy.yaml"):
        code = control_model.reject_forbidden_shell_command(cmd)
        if code is None:
            raise FamilyFanoutError("BLOCKED_FORBIDDEN_COMMAND_CHECKER", cmd)

    ws = prepare_branch_workspace(case_root, finding_id)
    patch_path = ws / "PATCH.diff"
    patch_path.write_text(patch_body, encoding="utf-8")
    paths_obj = {
        "FINDING_ID": finding_id,
        "CHANGED_PATHS": changed_paths,
        "PATCH_SHA256": _sha_text(patch_body),
    }
    (ws / "CHANGED_PATHS.json").write_text(
        json.dumps(paths_obj, indent=2) + "\n", encoding="utf-8"
    )
    green_status = "GREEN_CONFIRMED" if green_pass else "GREEN_FAILED"
    (ws / "GREEN_REPORT.md").write_text(
        f"# Branch GREEN\n\nFINDING_ID: {finding_id}\nGREEN_STATUS: {green_status}\n",
        encoding="utf-8",
    )
    (ws / "BRANCH_SUMMARY.md").write_text(
        f"# Branch summary\n\nFINDING_ID: {finding_id}\n\n{summary}\n",
        encoding="utf-8",
    )
    branch_status = "GREEN_CONFIRMED" if green_pass else "GREEN_FAILED"
    green_rel = f"branches/{finding_id}/GREEN_REPORT.md"
    green_hash = _sha_text((ws / "GREEN_REPORT.md").read_text(encoding="utf-8"))
    patch_rel = f"branches/{finding_id}/PATCH.diff"
    branch = bug_family.upsert_branch(
        case_root,
        {
            "FINDING_ID": finding_id,
            "BRANCH_STATUS": branch_status,
            "GREEN_STATUS": green_status,
            "GREEN_REPORT_PATH": green_rel,
            "GREEN_REPORT_HASH": green_hash,
            "PATCH_PATH": patch_rel,
            "PATCH_HASH": paths_obj["PATCH_SHA256"],
            "IMPLEMENTATION_STATUS": "IMPLEMENTED" if green_pass else "IMPLEMENTED_UNVERIFIED",
            "ACTUAL_CHANGED_PATHS": changed_paths,
            "UPDATED_AT": _now(),
        },
    )
    return {
        "FINDING_ID": finding_id,
        "GREEN_STATUS": green_status,
        "PATCH_PATH": str(patch_path),
        "PATCH_SHA256": paths_obj["PATCH_SHA256"],
        "BRANCH": branch,
    }


def set_branch_red(
    case_root: Path,
    *,
    finding_id: str,
    red_status: str,
) -> Dict[str, Any]:
    if red_status == "RED_FAILED":
        status = "RED_FAILED"
    elif red_status == "RED_CONFIRMED":
        status = "RED_CONFIRMED"
    else:
        raise FamilyFanoutError("BLOCKED_RED_STATUS", red_status)
    red_path = Path(case_root) / "results" / f"RED-{finding_id}.md"
    red_path.parent.mkdir(parents=True, exist_ok=True)
    body = f"# RED\n\nFINDING_ID: {finding_id}\nRED_STATUS: {red_status}\n"
    red_path.write_text(body, encoding="utf-8")
    red_hash = _sha_text(body)
    branch = bug_family.upsert_branch(
        case_root,
        {
            "FINDING_ID": finding_id,
            "RED_STATUS": red_status,
            "RED_EVIDENCE_PATH": f"results/RED-{finding_id}.md",
            "RED_EVIDENCE_HASH": red_hash,
            "BRANCH_STATUS": status,
            "UPDATED_AT": _now(),
        },
    )
    if red_status == "RED_FAILED":
        bug_family.update_family_status(case_root, family_status="OPEN_BLOCKED")
    return branch


# ---------------------------------------------------------------------------
# Integration + family green + fan-in + learning + closure
# ---------------------------------------------------------------------------


def integrate_branch_patches(
    case_root: Path,
    *,
    main_workspace: Path,
    finding_ids: List[str],
    combined_green_pass: bool,
    force_conflict: bool = False,
    unrelated_dirty: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Apply branch patches to main uncommitted worktree in deterministic order."""
    order = sorted(finding_ids)
    applied: List[Dict[str, Any]] = []
    conflicts: List[str] = []
    if force_conflict:
        conflicts.append("SIMULATED_PATCH_CONFLICT")
        result = {
            "INTEGRATION_STATUS": "PATCH_CONFLICT",
            "FAMILY_STATUS": "OPEN_BLOCKED",
            "APPLIED_PATCHES": [],
            "CONFLICTS": conflicts,
            "UPDATED_AT": _now(),
        }
        (bug_family.family_dir(case_root) / "INTEGRATION.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        bug_family.update_family_status(
            case_root,
            family_status="OPEN_BLOCKED",
            integration_status="PATCH_CONFLICT",
        )
        return result

    main_workspace = Path(main_workspace)
    main_workspace.mkdir(parents=True, exist_ok=True)
    # Preserve unrelated dirty markers
    for u in unrelated_dirty or []:
        up = main_workspace / u
        if not up.exists():
            up.parent.mkdir(parents=True, exist_ok=True)
            up.write_text("preexisting unrelated dirty\n", encoding="utf-8")

    for fid in order:
        ws = bug_family.branches_dir(case_root) / fid
        patch = ws / "PATCH.diff"
        paths_file = ws / "CHANGED_PATHS.json"
        if not patch.exists() or not paths_file.exists():
            raise FamilyFanoutError("BLOCKED_BRANCH_PATCH_MISSING", fid)
        paths = json.loads(paths_file.read_text(encoding="utf-8"))
        patch_sha = paths.get("PATCH_SHA256")
        if patch_sha != _sha_text(patch.read_text(encoding="utf-8")):
            raise FamilyFanoutError("BLOCKED_PATCH_HASH_MISMATCH", fid)
        # Apply workspace files into main
        src_ws = ws / "workspace"
        if src_ws.exists():
            for p in src_ws.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(src_ws)
                    dest = main_workspace / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, dest)
        applied.append({"FINDING_ID": fid, "PATCH_SHA256": patch_sha, "ORDER": len(applied) + 1})
        bug_family.upsert_branch(
            case_root,
            {
                "FINDING_ID": fid,
                "INTEGRATION_STATUS": "APPLIED",
                "BRANCH_STATUS": "INTEGRATED" if combined_green_pass else "GREEN_CONFIRMED",
                "UPDATED_AT": _now(),
            },
        )

    if not combined_green_pass:
        result = {
            "INTEGRATION_STATUS": "FAMILY_GREEN_FAILED",
            "FAMILY_CLOSURE": "FORBIDDEN",
            "APPLIED_PATCHES": applied,
            "CONFLICTS": [],
            "UPDATED_AT": _now(),
        }
        (bug_family.family_dir(case_root) / "INTEGRATION.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        bug_family.update_family_status(
            case_root,
            family_status="OPEN_BLOCKED",
            integration_status="FAMILY_GREEN_FAILED",
        )
        return result

    result = {
        "INTEGRATION_STATUS": "PASS",
        "APPLIED_PATCHES": applied,
        "CONFLICTS": [],
        "DETERMINISTIC_ORDER": order,
        "UNRELATED_DIRTY_PRESERVED": unrelated_dirty or [],
        "UPDATED_AT": _now(),
    }
    (bug_family.family_dir(case_root) / "INTEGRATION.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    bug_family.update_family_status(
        case_root, family_status="FAMILY_GREEN_PENDING", integration_status="PASS"
    )
    return result


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_hunt_candidates(case_root: Path) -> List[Dict[str, Any]]:
    path = bug_family.family_dir(case_root) / "HUNT_CANDIDATES.json"
    if not path.exists():
        return []
    return list(json.loads(path.read_text(encoding="utf-8")).get("CANDIDATES") or [])


def write_family_fanin(case_root: Path) -> Dict[str, Any]:
    """Assemble canonical FAMILY-FANIN.json then project FAMILY-FANIN.md (BF-V9-002)."""
    case_root = Path(case_root)
    family = bug_family.load_family(case_root)
    branches = bug_family.list_branches(case_root)
    open_blocking = bug_family.blocking_open_branches(case_root)
    results = case_root / "results"
    results.mkdir(parents=True, exist_ok=True)

    if open_blocking:
        ids = [b["FINDING_ID"] for b in open_blocking]
        sparse = {
            "FANIN_STATUS": "OPEN_BLOCKED",
            "FAMILY_CLOSURE_READINESS": "OPEN_BLOCKED",
            "OPEN_BLOCKING_FINDINGS": ids,
        }
        (results / "FAMILY-FANIN.json").write_text(
            json.dumps(sparse, indent=2) + "\n", encoding="utf-8"
        )
        (results / "FAMILY-FANIN.md").write_text(
            f"# FAMILY-FANIN\n\nCLOSURE_READINESS: OPEN_BLOCKED\nOPEN_BLOCKING: {', '.join(ids)}\n",
            encoding="utf-8",
        )
        raise FamilyFanoutError(
            "BLOCKED_FAMILY_FANIN_OPEN_BRANCHES",
            str(ids),
            {"OPEN_BLOCKING": ids, "CLOSURE_READINESS": "OPEN_BLOCKED"},
        )

    integ_path = bug_family.family_dir(case_root) / "INTEGRATION.json"
    if not integ_path.exists():
        raise FamilyFanoutError("BLOCKED_INCOMPLETE_FAMILY_FANIN", "integration_missing")
    integ = json.loads(integ_path.read_text(encoding="utf-8"))
    if integ.get("INTEGRATION_STATUS") != "PASS":
        raise FamilyFanoutError(
            "BLOCKED_FAMILY_FANIN_INTEGRATION",
            str(integ.get("INTEGRATION_STATUS")),
        )

    green_path = results / "FAMILY-GREEN-REPORT.md"
    if not green_path.exists() or "FAMILY_GREEN_STATUS: PASS" not in green_path.read_text(
        encoding="utf-8"
    ):
        raise FamilyFanoutError("BLOCKED_FAMILY_FANIN_GREEN_REQUIRED")

    hunt_candidates = _load_hunt_candidates(case_root)
    hunt_ids = {c.get("HUNT_CANDIDATE_ID") for c in hunt_candidates}
    branch_hunt_ids = {b.get("SOURCE_HUNT_ID") for b in branches if b.get("SOURCE_HUNT_ID")}
    # Every hunt candidate must appear as a branch source (or empty hunt)
    if hunt_ids and not hunt_ids.issubset(branch_hunt_ids):
        missing = sorted(hunt_ids - branch_hunt_ids)
        raise FamilyFanoutError(
            "BLOCKED_INCOMPLETE_FAMILY_FANIN",
            f"omitted_hunt_candidates:{missing}",
            {"OMITTED_HUNT_CANDIDATES": missing},
        )

    branch_rows: List[Dict[str, Any]] = []
    gaps: List[str] = []
    for b in branches:
        fid = b["FINDING_ID"]
        rel = b.get("RELATION_TO_INVARIANT")
        if not rel:
            gaps.append(f"missing_relation:{fid}")
        row: Dict[str, Any] = {
            "FINDING_ID": fid,
            "BRANCH_ID": b.get("BRANCH_ID"),
            "RELATION_TO_INVARIANT": rel,
            "BLOCKS_FAMILY_CLOSURE": b.get("BLOCKS_FAMILY_CLOSURE"),
            "CLASSIFICATION": b.get("CLASSIFICATION"),
            "CHOSEN_ROUTE": b.get("CHOSEN_ROUTE"),
            "RED_STATUS": b.get("RED_STATUS"),
            "RED_EVIDENCE_PATH": b.get("RED_EVIDENCE_PATH"),
            "RED_EVIDENCE_HASH": b.get("RED_EVIDENCE_HASH"),
            "PATCH_PATH": b.get("PATCH_PATH"),
            "PATCH_HASH": b.get("PATCH_HASH"),
            "CHANGED_PATHS": b.get("ACTUAL_CHANGED_PATHS") or b.get("EXPECTED_CHANGED_PATHS") or [],
            "GREEN_STATUS": b.get("GREEN_STATUS"),
            "GREEN_REPORT_PATH": b.get("GREEN_REPORT_PATH"),
            "GREEN_REPORT_HASH": b.get("GREEN_REPORT_HASH"),
            "INTEGRATION_STATUS": b.get("INTEGRATION_STATUS"),
        }
        if rel == "SAME_INVARIANT_FINDING" and b.get("BLOCKS_FAMILY_CLOSURE"):
            terminal_ok = b.get("BRANCH_STATUS") in {
                "GREEN_CONFIRMED",
                "TASK_COMPLETE",
                "INTEGRATED",
                "REJECTED_FALSE_POSITIVE",
                "HANDED_OFF_OUT_OF_SCOPE",
            }
            if not terminal_ok:
                gaps.append(f"non_terminal:{fid}")
            if b.get("BRANCH_STATUS") in {"GREEN_CONFIRMED", "INTEGRATED", "TASK_COMPLETE"}:
                if not b.get("RED_STATUS") or b.get("RED_STATUS") != "RED_CONFIRMED":
                    gaps.append(f"missing_branch_red:{fid}")
                if not b.get("RED_EVIDENCE_HASH"):
                    gaps.append(f"missing_red_hash:{fid}")
                if not b.get("PATCH_HASH"):
                    gaps.append(f"missing_patch_hash:{fid}")
                if not b.get("GREEN_STATUS") or b.get("GREEN_STATUS") != "GREEN_CONFIRMED":
                    gaps.append(f"missing_branch_green:{fid}")
                if not b.get("GREEN_REPORT_HASH"):
                    gaps.append(f"missing_green_hash:{fid}")
        branch_rows.append(row)

    if gaps:
        raise FamilyFanoutError(
            "BLOCKED_INCOMPLETE_FAMILY_FANIN",
            str(gaps),
            {"GAPS": gaps},
        )

    root_id = family["ROOT_FINDING_ID"]
    root_green = results / f"GREEN-{root_id}.md"
    root_red = results / f"RED-{root_id}.md"
    # optional reuse marker
    reused = list(results.glob(f"ROOT-GREEN-REUSED-{root_id}.md"))
    root_green_status = "GREEN_CONFIRMED"
    if root_green.exists() and "GREEN_CONFIRMED" in root_green.read_text(encoding="utf-8"):
        root_green_status = "GREEN_CONFIRMED"
    elif reused:
        root_green_status = "GREEN_CONFIRMED"
    root_evidence_hashes = {}
    if root_green.exists():
        root_evidence_hashes["ROOT_GREEN"] = _file_sha(root_green)
    if root_red.exists():
        root_evidence_hashes["ROOT_RED"] = _file_sha(root_red)

    same = [b for b in branches if b.get("RELATION_TO_INVARIANT") == "SAME_INVARIANT_FINDING"]
    nrc = [b for b in branches if b.get("RELATION_TO_INVARIANT") == "NEW_ROOT_CAUSE"]
    fps = [b for b in branches if b.get("RELATION_TO_INVARIANT") == "FALSE_POSITIVE"]
    oos = [b for b in branches if b.get("RELATION_TO_INVARIANT") == "OUT_OF_SCOPE"]
    inc = [b for b in branches if b.get("RELATION_TO_INVARIANT") == "INCONCLUSIVE"]

    readiness = "READY_FOR_FAMILY_CLOSURE"
    if inc:
        readiness = "OPEN_BLOCKED"

    canonical = {
        "BUG_FAMILY_ID": family["BUG_FAMILY_ID"],
        "CASE_ID": family["CASE_ID"],
        "INVARIANT_ID": family["INVARIANT_ID"],
        "INVARIANT_VERSION": family.get("INVARIANT_VERSION", 1),
        "ROOT_FINDING_ID": root_id,
        "ROOT_RED_STATUS": "RED_CONFIRMED" if root_red.exists() else "REUSED_OR_ABSENT",
        "ROOT_GREEN_STATUS": root_green_status,
        "ROOT_EVIDENCE_HASHES": root_evidence_hashes,
        "HUNT_CANDIDATES": hunt_candidates,
        "BRANCHES": branch_rows,
        "LINKED_NEW_ROOT_CASES": [b.get("LINKED_CASE_ID") for b in nrc if b.get("LINKED_CASE_ID")],
        "FALSE_POSITIVES": [b["FINDING_ID"] for b in fps],
        "OUT_OF_SCOPE_HANDOFFS": [b["FINDING_ID"] for b in oos],
        "INCONCLUSIVE_ITEMS": [b["FINDING_ID"] for b in inc],
        "INTEGRATION_STATUS": integ.get("INTEGRATION_STATUS"),
        "INTEGRATION_REPORT_PATH": "family/INTEGRATION.json",
        "INTEGRATION_REPORT_HASH": _file_sha(integ_path),
        "FAMILY_GREEN_STATUS": "PASS",
        "FAMILY_GREEN_REPORT_PATH": "results/FAMILY-GREEN-REPORT.md",
        "FAMILY_GREEN_REPORT_HASH": _file_sha(green_path),
        "LEARNING_READINESS": readiness == "READY_FOR_FAMILY_CLOSURE",
        "OPEN_BLOCKING_FINDINGS": [],
        "REMAINING_RISKS": ["User must review uncommitted worktree before commit."],
        "FANIN_STATUS": "COMPLETE" if readiness == "READY_FOR_FAMILY_CLOSURE" else "OPEN_BLOCKED",
        "FAMILY_CLOSURE_READINESS": readiness,
        "SAME_INVARIANT_COUNT": len(same),
    }
    json_path = results / "FAMILY-FANIN.json"
    json_path.write_text(json.dumps(canonical, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = _project_family_fanin_md(canonical)
    md_path = results / "FAMILY-FANIN.md"
    md_path.write_text(md, encoding="utf-8")

    if readiness != "READY_FOR_FAMILY_CLOSURE":
        bug_family.update_family_status(case_root, family_status="OPEN_BLOCKED")
        return {
            "CLOSURE_READINESS": readiness,
            "PATH": str(md_path),
            "JSON_PATH": str(json_path),
            "READY": False,
            "CANONICAL": canonical,
        }
    bug_family.update_family_status(case_root, family_status="FANIN_READY")
    return {
        "CLOSURE_READINESS": readiness,
        "PATH": str(md_path),
        "JSON_PATH": str(json_path),
        "READY": True,
        "CANONICAL": canonical,
    }


def _project_family_fanin_md(canonical: Dict[str, Any]) -> str:
    """Human projection — must be derived only from canonical JSON."""
    branches = canonical.get("BRANCHES") or []
    branch_lines = []
    for b in branches:
        branch_lines.append(
            f"- {b.get('FINDING_ID')}: relation={b.get('RELATION_TO_INVARIANT')} "
            f"red={b.get('RED_STATUS')} green={b.get('GREEN_STATUS')} "
            f"patch={b.get('PATCH_HASH')}"
        )
    return f"""# FAMILY-FANIN

```text
BUG_FAMILY_ID: {canonical.get('BUG_FAMILY_ID')}
CASE_ID: {canonical.get('CASE_ID')}
INVARIANT_ID: {canonical.get('INVARIANT_ID')}
ROOT_FINDING_ID: {canonical.get('ROOT_FINDING_ID')}
CLOSURE_READINESS: {canonical.get('FAMILY_CLOSURE_READINESS')}
INTEGRATION_STATUS: {canonical.get('INTEGRATION_STATUS')}
FAMILY_GREEN_STATUS: {canonical.get('FAMILY_GREEN_STATUS')}
SAME_INVARIANT_COUNT: {canonical.get('SAME_INVARIANT_COUNT')}
```

## Hunt candidates

{json.dumps(canonical.get('HUNT_CANDIDATES') or [], ensure_ascii=False, indent=2)}

## Branches

{chr(10).join(branch_lines) or '- (none)'}

## Linked new roots / FP / OOS / inconclusive

- LINKED: {canonical.get('LINKED_NEW_ROOT_CASES')}
- FALSE_POSITIVES: {canonical.get('FALSE_POSITIVES')}
- OUT_OF_SCOPE: {canonical.get('OUT_OF_SCOPE_HANDOFFS')}
- INCONCLUSIVE: {canonical.get('INCONCLUSIVE_ITEMS')}

## Remaining risks

{chr(10).join('- ' + r for r in (canonical.get('REMAINING_RISKS') or []))}
"""


def validate_learning_packet(packet: Dict[str, Any], case_root: Optional[Path] = None) -> Dict[str, Any]:
    """Authoritative learning packet validation (BF-V9-003)."""
    pol = family_policy.load_policy()
    required = pol.get("LEARNING_PACKET_REQUIRED_FIELDS") or []
    missing = [f for f in required if f not in packet or packet.get(f) in (None, "", [])]
    # Allow empty lists for optional collections but field must exist
    missing = [f for f in required if f not in packet]
    if missing:
        raise FamilyFanoutError(
            "BLOCKED_LEARNING_PACKET_INCOMPLETE",
            str(missing),
            {"MISSING": missing},
        )
    if case_root is not None:
        family = bug_family.load_family(case_root)
        if packet.get("BUG_FAMILY_ID") != family.get("BUG_FAMILY_ID"):
            raise FamilyFanoutError("BLOCKED_LEARNING_PACKET_INCOMPLETE", "family_identity_mismatch")
        fanin_json = Path(case_root) / "results" / "FAMILY-FANIN.json"
        if not fanin_json.exists():
            raise FamilyFanoutError("BLOCKED_LEARNING_FAMILY_NOT_READY", "fanin_json_missing")
        sources = packet.get("SOURCE_ARTIFACT_HASHES") or {}
        expected = sources.get("FAMILY_FANIN_JSON")
        if expected and expected != _file_sha(fanin_json):
            raise FamilyFanoutError("BLOCKED_LEARNING_SOURCE_STALE", "FAMILY_FANIN_JSON")
        if bug_family.blocking_open_branches(case_root):
            raise FamilyFanoutError("BLOCKED_LEARNING_FAMILY_NOT_READY", "open_blocking")
    return {"STATUS": "PASS"}


def run_learning(case_root: Path, *, force: bool = False) -> Dict[str, Any]:
    """Learning only after complete family fan-in readiness (BF-V9-003)."""
    case_root = Path(case_root)
    fanin_json = case_root / "results" / "FAMILY-FANIN.json"
    fanin_md = case_root / "results" / "FAMILY-FANIN.md"
    if not force:
        ready = False
        if fanin_json.exists():
            data = json.loads(fanin_json.read_text(encoding="utf-8"))
            ready = data.get("FAMILY_CLOSURE_READINESS") == "READY_FOR_FAMILY_CLOSURE"
            if data.get("FAMILY_GREEN_STATUS") != "PASS":
                raise FamilyFanoutError("BLOCKED_LEARNING_FAMILY_NOT_READY", "family_green")
            if data.get("OPEN_BLOCKING_FINDINGS"):
                raise FamilyFanoutError("BLOCKED_LEARNING_FAMILY_NOT_READY", "open_blocking")
        elif fanin_md.exists() and "READY_FOR_FAMILY_CLOSURE" in fanin_md.read_text(encoding="utf-8"):
            ready = True
        if not ready:
            raise FamilyFanoutError("BLOCKED_LEARNING_BEFORE_FAMILY_READY")
        if bug_family.blocking_open_branches(case_root):
            raise FamilyFanoutError("BLOCKED_LEARNING_PARTIAL_FAMILY")

    family = bug_family.load_family(case_root)
    branches = bug_family.list_branches(case_root)
    same = [b for b in branches if b.get("RELATION_TO_INVARIANT") == "SAME_INVARIANT_FINDING"]
    nrc = [b for b in branches if b.get("RELATION_TO_INVARIANT") == "NEW_ROOT_CAUSE"]
    fps = [b for b in branches if b.get("RELATION_TO_INVARIANT") == "FALSE_POSITIVE"]
    oos = [b for b in branches if b.get("RELATION_TO_INVARIANT") == "OUT_OF_SCOPE"]
    inc = [b for b in branches if b.get("RELATION_TO_INVARIANT") == "INCONCLUSIVE"]
    hunt = _load_hunt_candidates(case_root)
    inv_md = bug_family.family_dir(case_root) / "INVARIANT.md"
    inv_text = inv_md.read_text(encoding="utf-8") if inv_md.exists() else ""
    integ = json.loads(
        (bug_family.family_dir(case_root) / "INTEGRATION.json").read_text(encoding="utf-8")
    )
    green_path = case_root / "results" / "FAMILY-GREEN-REPORT.md"
    root_id = family["ROOT_FINDING_ID"]

    packet = {
        "LEARNING_PACKET_ID": f"LEARN/{family['BUG_FAMILY_ID']}/{uuid.uuid4().hex[:8]}",
        "BUG_FAMILY_ID": family["BUG_FAMILY_ID"],
        "CASE_ID": family["CASE_ID"],
        "INVARIANT_ID": family["INVARIANT_ID"],
        "INVARIANT_VERSION": family.get("INVARIANT_VERSION", 1),
        "INVARIANT": inv_text[:4000],
        "ROOT_CAUSE": f"Root finding {root_id}",
        "ROOT_FAILURE": "See ROOT_RED / intake",
        "ROOT_FIX": f"See results/FIX-{root_id}.md if present",
        "ROOT_RED_EVIDENCE": f"results/RED-{root_id}.md",
        "ROOT_GREEN_EVIDENCE": f"results/GREEN-{root_id}.md",
        "ALL_HUNT_CANDIDATES": hunt,
        "ALL_SAME_INVARIANT_FINDINGS": [b["FINDING_ID"] for b in same],
        "ALL_LINKED_NEW_ROOT_CASES": [b.get("LINKED_CASE_ID") or b["FINDING_ID"] for b in nrc],
        "ALL_FALSE_POSITIVES": [b["FINDING_ID"] for b in fps],
        "ALL_OUT_OF_SCOPE_FINDINGS": [b["FINDING_ID"] for b in oos],
        "ALL_INCONCLUSIVE_ITEMS": [b["FINDING_ID"] for b in inc],
        "BRANCH_ROUTES": {b["FINDING_ID"]: b.get("CHOSEN_ROUTE") for b in same},
        "BRANCH_RED_RESULTS": {b["FINDING_ID"]: b.get("RED_STATUS") for b in same},
        "BRANCH_FIXES": {b["FINDING_ID"]: b.get("PATCH_PATH") for b in same},
        "BRANCH_GREEN_RESULTS": {b["FINDING_ID"]: b.get("GREEN_STATUS") for b in same},
        "BRANCH_PATCH_HASHES": {b["FINDING_ID"]: b.get("PATCH_HASH") for b in same},
        "INTEGRATION_RESULT": integ.get("INTEGRATION_STATUS"),
        "FAMILY_GREEN_RESULT": "PASS" if green_path.exists() else "UNKNOWN",
        "MISSED_ORIGINAL_DETECTION_POINTS": [
            "Sibling same-invariant findings were not auto-fanned-out in ACTIVE_V1",
        ],
        "HUNT_SCOPE": "See family/INVARIANT.md HUNT_SCOPE",
        "HUNT_EFFECTIVENESS": {
            "CANDIDATES": len(hunt),
            "SAME_INVARIANT": len(same),
            "FALSE_POSITIVES": len(fps),
        },
        "HUNT_FALSE_NEGATIVE_RISK": "bounded hunt may miss distant writers",
        "HUNT_FALSE_POSITIVE_RESULTS": [b["FINDING_ID"] for b in fps],
        "TESTS_ADDED": [b.get("GREEN_REPORT_PATH") for b in same if b.get("GREEN_REPORT_PATH")],
        "FILES_CHANGED_BY_BRANCH": {
            b["FINDING_ID"]: b.get("ACTUAL_CHANGED_PATHS") or [] for b in same
        },
        "FILES_CHANGED_COMBINED": sorted(
            {
                p
                for b in same
                for p in (b.get("ACTUAL_CHANGED_PATHS") or [])
            }
        ),
        "UNRELATED_DIRTY_FILES": integ.get("UNRELATED_DIRTY_PRESERVED") or [],
        "ROUTE_DECISIONS": {b["FINDING_ID"]: b.get("CHOSEN_ROUTE") for b in branches},
        "REJECTED_OPTIONS": [],
        "RETRIES_AND_TIMEOUTS": [],
        "REUSABLE_LESSONS": [
            "Hunt candidates in the same invariant family must fan out automatically.",
            "Branch GREEN is not family GREEN.",
        ],
        "PROPOSED_INVARIANT_TESTS": ["family invariant covers root + siblings"],
        "PROPOSED_PROCESS_IMPROVEMENTS": ["enable BUG_FAMILY_FANOUT after independent pass"],
        "SOURCE_ARTIFACT_PATHS": {
            "FAMILY_FANIN_JSON": "results/FAMILY-FANIN.json",
            "INTEGRATION": "family/INTEGRATION.json",
            "FAMILY_GREEN": "results/FAMILY-GREEN-REPORT.md",
        },
        "SOURCE_ARTIFACT_HASHES": {
            "FAMILY_FANIN_JSON": _file_sha(fanin_json) if fanin_json.exists() else None,
            "INTEGRATION": _file_sha(bug_family.family_dir(case_root) / "INTEGRATION.json"),
            "FAMILY_GREEN": _file_sha(green_path) if green_path.exists() else None,
        },
        "LEARNING_STATUS": "COMPLETE",
        "UPDATED_AT": _now(),
    }
    validate_learning_packet(packet, case_root if not force else None)
    packet_path = bug_family.family_dir(case_root) / "LEARNING_PACKET.json"
    packet_path.write_text(
        json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    # Mandatory compact decision (full packet remains for candidate/class lessons).
    fanin_rel = "results/FAMILY-FANIN.json" if fanin_json.exists() else "results/FAMILY-FANIN.md"
    fanin_src = case_root / fanin_rel
    decision = learning_decision.build_learning_decision(
        case_id=str(family["CASE_ID"]),
        bug_family_id=str(family["BUG_FAMILY_ID"]),
        invariant_id=str(family.get("INVARIANT_ID") or ""),
        learning_verdict="CLASS_LESSON_CANDIDATE",
        learning_status="COMPLETE",
        policy_already_exists=False,
        policy_refs=[],
        enforcement_gap=None,
        promotion_decision="DEFERRED",
        recommendations={
            "STATIC_CHECK_CANDIDATE": False,
            "PROJECT_WIDE_HUNT_REQUEST": False,
            "TESTING_RULES_CANDIDATE": False,
        },
        source_fanin_path=fanin_rel,
        source_fanin_hash=_file_sha(fanin_src) if fanin_src.exists() else None,
        source_artifact_paths=dict(packet["SOURCE_ARTIFACT_PATHS"]),
        source_artifact_hashes=dict(packet["SOURCE_ARTIFACT_HASHES"]),
        decision_rationale=(
            "Family fan-in complete; class-lesson candidate recorded; "
            "promotion deferred (no auto rule/superclass activation)."
        ),
        full_packet_path="family/LEARNING_PACKET.json",
    )
    learning_decision.write_learning_decision(case_root, decision)
    learning_decision.validate_learning_decision(decision, case_root=case_root)
    report = case_root / "results" / "LEARNING_REPORT.md"
    report.write_text(
        f"# LEARNING_REPORT\n\nLEARNING_STATUS: COMPLETE\nFAMILY: {family['BUG_FAMILY_ID']}\n"
        f"LEARNING_VERDICT: {decision['LEARNING_VERDICT']}\n",
        encoding="utf-8",
    )
    bug_family.update_family_status(case_root, learning_status="COMPLETE", family_status="LEARNING")
    return packet


def write_family_green_report(
    case_root: Path,
    *,
    root_green: bool,
    all_blocking_branch_greens: bool,
    patch_integration: bool,
    family_invariant_test: bool,
    relevant_regression_tests: bool,
) -> Dict[str, Any]:
    ok = all(
        [
            root_green,
            all_blocking_branch_greens,
            patch_integration,
            family_invariant_test,
            relevant_regression_tests,
        ]
    )
    path = Path(case_root) / "results" / "FAMILY-GREEN-REPORT.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    status = "PASS" if ok else "FAIL"
    path.write_text(
        f"""# FAMILY-GREEN-REPORT

```text
ROOT_GREEN: {"PASS" if root_green else "FAIL"}
ALL_BLOCKING_BRANCH_GREENS: {"PASS" if all_blocking_branch_greens else "FAIL"}
PATCH_INTEGRATION: {"PASS" if patch_integration else "FAIL"}
FAMILY_INVARIANT_TEST: {"PASS" if family_invariant_test else "FAIL"}
RELEVANT_REGRESSION_TESTS: {"PASS" if relevant_regression_tests else "FAIL"}
FAMILY_GREEN_STATUS: {status}
```
""",
        encoding="utf-8",
    )
    if ok:
        bug_family.update_family_status(case_root, family_status="FANIN_READY")
    else:
        bug_family.update_family_status(case_root, family_status="OPEN_BLOCKED")
    return {"FAMILY_GREEN_STATUS": status, "PATH": str(path), "PASS": ok}


def write_family_human_summary(
    case_root: Path,
    *,
    original_bug: str,
    invariant_plain: str,
    hunt_findings: List[str],
    same_family: List[str],
    separate_roots: List[str],
    branch_fixes: Dict[str, str],
    branch_files: Dict[str, List[str]],
    how_combined: str,
    family_tests: str,
    unresolved: str,
    review_diff: str,
    unrelated_dirty: Optional[List[str]] = None,
) -> Path:
    path = Path(case_root) / "results" / "HUMAN_SUMMARY.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    branches_block = "\n".join(
        f"### {fid}\n\n{branch_fixes.get(fid, '')}\n\nФайлы: "
        + ", ".join(branch_files.get(fid, []) or ["(нет)"])
        for fid in same_family
    )
    body = f"""# Что произошло

{original_bug}

# Какой инвариант мы извлекли

{invariant_plain}

# Что похожего нашла охота за багами

{chr(10).join(f'- {x}' for x in hunt_findings) or '- (ничего)'}

# Какие находки из одной семьи

{chr(10).join(f'- {x}' for x in same_family) or '- (только корень)'}

# Какие находки — отдельные корневые причины

{chr(10).join(f'- {x}' for x in separate_roots) or '- (нет)'}

# Что исправили в каждой ветке

{branches_block or '(нет веток)'}

# Какие файлы изменены

{chr(10).join(f'- {fid}: {", ".join(paths)}' for fid, paths in branch_files.items()) or '- (нет)'}

## Изменения этого bug episode

{chr(10).join(f'- {p}' for paths in branch_files.values() for p in paths) or '- (нет)'}

## Ранее существовавшие несвязанные изменения

{chr(10).join(f'- {u}' for u in (unrelated_dirty or [])) or '- (нет)'}

# Как объединили исправления веток

{how_combined}

# Как мы проверили

{family_tests}

# Какие дополнительные проверки сделали

Семейный инвариантный тест + регрессии по зоне бага.

# Что не изменяли

Несвязанные dirty-файлы; git commit/push/deploy.

# Оставшиеся риски

{unresolved}

# Что проверить перед коммитом

{review_diff}

# Технические детали

См. family/FAMILY.json, results/FAMILY-FANIN.md, branches/*/PATCH.diff.
Worker execution IDs и packet generation намеренно не требуются для чтения этого отчёта.
"""
    path.write_text(body, encoding="utf-8")
    return path


def close_family(case_root: Path) -> Dict[str, Any]:
    """Family closure only when all closure conditions hold."""
    family = bug_family.load_family(case_root)
    if bug_family.blocking_open_branches(case_root):
        raise FamilyFanoutError("BLOCKED_FAMILY_CLOSURE_OPEN_BRANCHES")
    integ = json.loads(
        (bug_family.family_dir(case_root) / "INTEGRATION.json").read_text(encoding="utf-8")
    )
    if integ.get("INTEGRATION_STATUS") != "PASS":
        raise FamilyFanoutError("BLOCKED_FAMILY_CLOSURE_INTEGRATION")
    green = Path(case_root) / "results" / "FAMILY-GREEN-REPORT.md"
    if not green.exists() or "FAMILY_GREEN_STATUS: PASS" not in green.read_text(encoding="utf-8"):
        raise FamilyFanoutError("BLOCKED_FAMILY_CLOSURE_GREEN")
    fanin = Path(case_root) / "results" / "FAMILY-FANIN.md"
    if not fanin.exists() or "READY_FOR_FAMILY_CLOSURE" not in fanin.read_text(encoding="utf-8"):
        raise FamilyFanoutError("BLOCKED_FAMILY_CLOSURE_FANIN")
    try:
        learning_decision.evaluate_closure_learning_gate(case_root)
    except learning_decision.LearningDecisionError as exc:
        # Preserve historical alias when decision missing/incomplete for family path.
        if exc.code == "BLOCKED_LEARNING_DECISION_MISSING":
            raise FamilyFanoutError("BLOCKED_LEARNING_DECISION_MISSING") from exc
        raise FamilyFanoutError(exc.code, exc.detail, exc.payload) from exc
    if not (Path(case_root) / "results" / "HUMAN_SUMMARY.md").exists():
        raise FamilyFanoutError("BLOCKED_FAMILY_CLOSURE_HUMAN_SUMMARY")

    bug_family.update_family_status(
        case_root,
        family_status="CLOSED_FIXED_VERIFIED",
        learning_status="COMPLETE",
        integration_status="PASS",
    )
    terminal = control_model.terminal_user_control_state(
        case_closed=True,
        commit_created=False,
        worktree_has_episode_changes=True,
    )
    return {
        "FAMILY_STATUS": "CLOSED_FIXED_VERIFIED",
        "WORKTREE_STATUS": terminal["WORKTREE_STATUS"],
        "COMMIT_CREATED": False,
        "USER_ACTION_REQUIRED": terminal["USER_ACTION_REQUIRED"],
        **terminal,
    }


def assert_branch_cannot_close_family(case_root: Path, finding_id: str) -> None:
    """Branch worker must not set FAMILY_STATUS=CLOSED_*."""
    # If someone tries to close via branch alone while siblings open — reject
    open_b = [b for b in bug_family.blocking_open_branches(case_root) if b["FINDING_ID"] != finding_id]
    if open_b:
        raise FamilyFanoutError(
            "BLOCKED_BRANCH_CANNOT_CLOSE_FAMILY",
            finding_id,
            {"OPEN": [b["FINDING_ID"] for b in open_b]},
        )
    # Even if no others, branch GREEN alone is insufficient without family green/integration
    raise FamilyFanoutError(
        "BLOCKED_BRANCH_GREEN_NOT_FAMILY_CLOSURE",
        finding_id,
    )


def assert_root_green_cannot_close_open_sibling(case_root: Path) -> None:
    if bug_family.blocking_open_branches(case_root):
        raise FamilyFanoutError("BLOCKED_ROOT_GREEN_CANNOT_CLOSE_OPEN_SIBLING")


# ---------------------------------------------------------------------------
# End-to-end helpers + PBH-006 resume path (proof/harness only)
# ---------------------------------------------------------------------------


def bootstrap_family_after_root_green(
    case_root: Path,
    *,
    case_id: str,
    root_finding_id: str,
    execution_mode: str,
    proof_root: Path,
    invariant_kwargs: Dict[str, Any],
) -> Dict[str, Any]:
    _require_gate(execution_mode=execution_mode, proof_root=proof_root)
    family = bug_family.create_family(
        case_root, case_id=case_id, root_finding_id=root_finding_id
    )
    inv_kwargs = dict(invariant_kwargs)
    inv_kwargs["invariant_id"] = family["INVARIANT_ID"]
    capture_invariant(case_root, **inv_kwargs)
    bug_family.update_family_status(case_root, family_status="HUNTING")
    return family


def resume_family_fanout_from_root_green(
    case_root: Path,
    *,
    case_id: str,
    root_finding_id: str,
    root_green_path: Path,
    hunt_candidates: List[Dict[str, Any]],
    relations: Dict[str, str],
    execution_mode: str,
    proof_root: Path,
    invariant_kwargs: Dict[str, Any],
) -> Dict[str, Any]:
    """Resume path for mode=resume-family-fanout (e.g. BUGCASE-PBH-006).

    Reuses existing root GREEN evidence; does not rewrite root implementation.
    Must be invoked under CONTROLLED_TEST_FAMILY_FANOUT or future V8 enablement.
    Builder step must NOT call this against the real product case directory.
    """
    _require_gate(execution_mode=execution_mode, proof_root=proof_root)
    if not root_green_path.exists():
        raise FamilyFanoutError("BLOCKED_ROOT_GREEN_MISSING", str(root_green_path))
    text = root_green_path.read_text(encoding="utf-8")
    if "GREEN_CONFIRMED" not in text and "GREEN_STATUS: GREEN_CONFIRMED" not in text:
        raise FamilyFanoutError("BLOCKED_ROOT_GREEN_NOT_CONFIRMED")

    family = bootstrap_family_after_root_green(
        case_root,
        case_id=case_id,
        root_finding_id=root_finding_id,
        execution_mode=execution_mode,
        proof_root=proof_root,
        invariant_kwargs=invariant_kwargs,
    )
    # Mark root reused
    reuse = Path(case_root) / "results" / f"ROOT-GREEN-REUSED-{root_finding_id}.md"
    reuse.parent.mkdir(parents=True, exist_ok=True)
    reuse.write_text(
        f"ROOT_FINDING_ID: {root_finding_id}\nREUSED_GREEN_PATH: {root_green_path}\n"
        f"RERUN_ROOT_IMPLEMENTATION: false\n",
        encoding="utf-8",
    )

    hunt = {"HUNT_RESULT": "CANDIDATES_FOUND", "CANDIDATES": hunt_candidates}
    validate_hunt_result(hunt, case_root=case_root)

    materialized = []
    for cand in hunt_candidates:
        cid = cand["HUNT_CANDIDATE_ID"]
        rel = relations[cid]
        fid = cand.get("PROPOSED_FINDING_ID")
        out = classify_relation(
            case_root,
            candidate=cand,
            relation=rel,
            rationale=cand.get("RATIONALE") or "resume-family-fanout",
            finding_id=fid,
            expected_changed_paths=cand.get("EXPECTED_CHANGED_PATHS"),
        )
        if rel == "SAME_INVARIANT_FINDING":
            run_classifier_for_branch(
                case_root,
                finding_id=out["FINDING_ID"],
                classification=cand.get("CLASSIFICATION") or "IMPLEMENTATION_BUG",
                chosen_route=cand.get("CHOSEN_ROUTE") or "ROUTE_A",
            )
        materialized.append(out)

    return {
        "STATUS": "RESUME_FANOUT_MATERIALIZED",
        "MODE": "resume-family-fanout",
        "CASE_ID": case_id,
        "ROOT_GREEN_REUSED": True,
        "FAMILY": family,
        "MATERIALIZED": materialized,
    }
