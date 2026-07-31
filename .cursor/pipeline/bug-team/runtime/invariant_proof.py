# -*- coding: utf-8 -*-
"""V9 invariant root-proof validation (BF-V9-001).

Ensures family/INVARIANT.md agrees with machine-readable ROOT-GREEN-PROOF.json.
Shadow V8/V9 only — does not change ACTIVE_V1 defaults.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from . import bug_family


class InvariantProofError(Exception):
    """Invariant/root-proof rejection (BF-V9-001)."""

    def __init__(self, code: str, detail: str = "", payload: Optional[Dict[str, Any]] = None) -> None:
        self.code = code
        self.detail = detail
        self.payload = payload or {}
        super().__init__(f"{code}: {detail}" if detail else code)


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def root_proof_path(case_root: Path) -> Path:
    return bug_family.family_dir(case_root) / "ROOT-GREEN-PROOF.json"


def invariant_projection_path(case_root: Path) -> Path:
    return bug_family.family_dir(case_root) / "INVARIANT.json"


def write_root_green_proof(
    case_root: Path,
    *,
    invariant_id: str,
    root_finding_id: str,
    root_red_claims: List[str],
    root_failure_behavior: str,
    root_fix_claims: List[str],
    root_green_claims: List[str],
    required_behavior_proven: List[str],
    forbidden_behavior_proven: List[str],
    evidence_paths: Dict[str, str],
    scope_tokens: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Write family/ROOT-GREEN-PROOF.json with evidence hashes."""
    case_root = Path(case_root)
    fdir = bug_family.family_dir(case_root)
    fdir.mkdir(parents=True, exist_ok=True)
    hashes: Dict[str, str] = {}
    for key, rel in evidence_paths.items():
        p = case_root / rel if not Path(rel).is_absolute() else Path(rel)
        if not p.exists():
            raise InvariantProofError("BLOCKED_ROOT_PROOF_EVIDENCE_MISSING", rel)
        hashes[key] = _sha_file(p)
    proof = {
        "INVARIANT_ID": invariant_id,
        "ROOT_FINDING_ID": root_finding_id,
        "ROOT_RED_CLAIMS": list(root_red_claims),
        "ROOT_FAILURE_BEHAVIOR": root_failure_behavior,
        "ROOT_FIX_CLAIMS": list(root_fix_claims),
        "ROOT_GREEN_CLAIMS": list(root_green_claims),
        "REQUIRED_BEHAVIOR_PROVEN": list(required_behavior_proven),
        "FORBIDDEN_BEHAVIOR_PROVEN": list(forbidden_behavior_proven),
        "EVIDENCE_PATHS": dict(evidence_paths),
        "EVIDENCE_HASHES": hashes,
        "SCOPE_TOKENS": list(scope_tokens or []),
    }
    root_proof_path(case_root).write_text(
        json.dumps(proof, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return proof


def write_invariant_projection(
    case_root: Path,
    *,
    invariant_id: str,
    required_behavior: str,
    forbidden_behavior: str,
    entry_conditions: str,
    scope: str,
    contradicts_root_green: bool = False,
    contradicts_root_fix: bool = False,
    introduces_unrelated_rule: bool = False,
) -> Dict[str, Any]:
    """Machine-readable companion for INVARIANT.md."""
    proj = {
        "INVARIANT_ID": invariant_id,
        "INVARIANT_REQUIRED_BEHAVIOR": required_behavior.strip(),
        "INVARIANT_FORBIDDEN_BEHAVIOR": forbidden_behavior.strip(),
        "INVARIANT_ENTRY_CONDITIONS": entry_conditions.strip(),
        "INVARIANT_SCOPE": scope.strip(),
        "CONTRADICTS_ROOT_GREEN": contradicts_root_green,
        "CONTRADICTS_ROOT_FIX": contradicts_root_fix,
        "INTRODUCES_UNRELATED_RULE": introduces_unrelated_rule,
    }
    path = invariant_projection_path(case_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return proj


def _norm_tokens(text: str) -> Set[str]:
    return {t for t in re.findall(r"[a-z0-9_]{3,}", text.lower())}


def validate_invariant_against_root_proof(
    case_root: Path,
    *,
    projection: Optional[Dict[str, Any]] = None,
    proof: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Reject invariants that contradict or ignore root GREEN proof."""
    case_root = Path(case_root)
    proof_path = root_proof_path(case_root)
    if proof is None:
        if not proof_path.exists():
            raise InvariantProofError(
                "BLOCKED_INVARIANT_ROOT_PROOF_MISSING",
                str(proof_path),
            )
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
    if projection is None:
        proj_path = invariant_projection_path(case_root)
        if not proj_path.exists():
            raise InvariantProofError("BLOCKED_INVARIANT_PROJECTION_MISSING", str(proj_path))
        projection = json.loads(proj_path.read_text(encoding="utf-8"))

    diagnostics: Dict[str, Any] = {
        "CONTRADICTING_INVARIANT_CLAIMS": [],
        "ROOT_GREEN_CLAIMS": list(proof.get("ROOT_GREEN_CLAIMS") or []),
        "MISSING_SUPPORT": [],
        "EVIDENCE_PATHS": dict(proof.get("EVIDENCE_PATHS") or {}),
    }

    for key, rel in (proof.get("EVIDENCE_PATHS") or {}).items():
        p = case_root / rel if not Path(rel).is_absolute() else Path(rel)
        if not p.exists():
            raise InvariantProofError(
                "BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH",
                f"missing_evidence:{rel}",
                diagnostics,
            )
        actual = _sha_file(p)
        expected = (proof.get("EVIDENCE_HASHES") or {}).get(key)
        if expected and actual != expected:
            diagnostics["MISSING_SUPPORT"].append(f"stale_hash:{key}")
            raise InvariantProofError(
                "BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH",
                "stale_evidence_hash",
                diagnostics,
            )

    inv_req = projection.get("INVARIANT_REQUIRED_BEHAVIOR") or ""
    inv_forb = projection.get("INVARIANT_FORBIDDEN_BEHAVIOR") or ""
    inv_scope = projection.get("INVARIANT_SCOPE") or ""
    green_claims = " ".join(proof.get("ROOT_GREEN_CLAIMS") or [])
    fix_claims = " ".join(proof.get("ROOT_FIX_CLAIMS") or [])
    proven_req = " ".join(proof.get("REQUIRED_BEHAVIOR_PROVEN") or [])
    scope_tokens = {t.lower() for t in (proof.get("SCOPE_TOKENS") or [])}

    inv_scope_tokens = _norm_tokens(inv_scope)
    if scope_tokens and inv_scope_tokens.isdisjoint(scope_tokens):
        diagnostics["MISSING_SUPPORT"].append("scope_unrelated")
        raise InvariantProofError(
            "BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH",
            "scope_unrelated",
            diagnostics,
        )

    if projection.get("CONTRADICTS_ROOT_GREEN") is True:
        diagnostics["CONTRADICTING_INVARIANT_CLAIMS"].append(inv_req)
        raise InvariantProofError(
            "BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH",
            "required_contradicts_green",
            {**diagnostics, "CONTRADICTING_INVARIANT_CLAIMS": [inv_req]},
        )

    # Phrase-level contradiction: green requires apply; invariant required forbids apply
    green_l = green_claims.lower()
    req_l = inv_req.lower()
    if ("fail" in green_l and "off" in green_l and ("exactly once" in green_l or "must" in green_l)) and (
        "never apply" in req_l or "must not apply" in req_l or "skip fail" in req_l
    ):
        diagnostics["CONTRADICTING_INVARIANT_CLAIMS"].append(inv_req)
        raise InvariantProofError(
            "BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH",
            "required_contradicts_green",
            diagnostics,
        )

    if projection.get("CONTRADICTS_ROOT_FIX") is True:
        diagnostics["CONTRADICTING_INVARIANT_CLAIMS"].append(inv_forb)
        raise InvariantProofError(
            "BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH",
            "forbidden_contradicts_fix",
            diagnostics,
        )

    proven_pool = _norm_tokens(proven_req + " " + green_claims + " " + fix_claims)
    inv_req_tokens = _norm_tokens(inv_req)
    if proven_pool and inv_req_tokens:
        overlap = inv_req_tokens & proven_pool
        if not overlap:
            diagnostics["MISSING_SUPPORT"].append("required_behavior_unsupported")
            raise InvariantProofError(
                "BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH",
                "unsupported_behavior",
                diagnostics,
            )

    if projection.get("INTRODUCES_UNRELATED_RULE") is True:
        diagnostics["MISSING_SUPPORT"].append("unrelated_new_rule")
        raise InvariantProofError(
            "BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH",
            "unrelated_new_rule",
            diagnostics,
        )

    return {"STATUS": "PASS", "INVARIANT_ID": projection.get("INVARIANT_ID"), **diagnostics}
