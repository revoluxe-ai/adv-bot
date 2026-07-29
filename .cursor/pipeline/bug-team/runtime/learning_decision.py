# -*- coding: utf-8 -*-
"""Mandatory LEARNING_DECISION artifact — validation and closure gate.

Canonical locations (exactly one per case):
  family/LEARNING_DECISION.json  when family/ exists
  results/LEARNING_DECISION.json episode-only compatibility

Learning stage is mandatory before CLOSURE_OPERATOR / close_family.
Full LEARNING_PACKET.json is conditional on LEARNING_VERDICT.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LEARNING_VERDICTS = (
    "NO_REUSABLE_LESSON",
    "LOCAL_CASE_NOTE_ONLY",
    "EXISTING_POLICY_COMPLIANCE_FAILURE",
    "COMPLIANCE_ENFORCEMENT_CANDIDATE",
    "CLASS_LESSON_CANDIDATE",
    "SUPERCLASS_SEED_EVIDENCE",
    "OWNER_DECISION_REQUIRED",
    "LEARNING_BLOCKED",
)

CLOSURE_ALLOWED_VERDICTS = (
    "NO_REUSABLE_LESSON",
    "LOCAL_CASE_NOTE_ONLY",
    "EXISTING_POLICY_COMPLIANCE_FAILURE",
    "COMPLIANCE_ENFORCEMENT_CANDIDATE",
    "CLASS_LESSON_CANDIDATE",
    "SUPERCLASS_SEED_EVIDENCE",
)

PACKET_REQUIRED_VERDICTS = (
    "COMPLIANCE_ENFORCEMENT_CANDIDATE",
    "CLASS_LESSON_CANDIDATE",
    "SUPERCLASS_SEED_EVIDENCE",
)

PACKET_FREE_VERDICTS = (
    "NO_REUSABLE_LESSON",
    "LOCAL_CASE_NOTE_ONLY",
    "EXISTING_POLICY_COMPLIANCE_FAILURE",
)

CLOSURE_BLOCKING_VERDICTS = (
    "OWNER_DECISION_REQUIRED",
    "LEARNING_BLOCKED",
)

PROMOTION_ALLOWED_FOR_CLOSURE = (
    "NONE",
    "DEFERRED",
    "RESOLVED_NO_PROMOTE",
    "QUEUED",
)

CANDIDATE_PROMOTION_REQUIRED = (
    "DEFERRED",
    "RESOLVED_NO_PROMOTE",
    "QUEUED",
)

LEARNING_STATUSES = ("COMPLETE", "BLOCKED", "OWNER_WAIT")

REQUIRED_FIELDS = (
    "LEARNING_DECISION_ID",
    "CASE_ID",
    "BUG_FAMILY_ID",
    "INVARIANT_ID",
    "LEARNING_STAGE_INVOKED",
    "LEARNING_VERDICT",
    "POLICY_ALREADY_EXISTS",
    "POLICY_REFS",
    "ENFORCEMENT_GAP",
    "PROMOTION_DECISION",
    "RECOMMENDATIONS",
    "FULL_PACKET_REQUIRED",
    "FULL_PACKET_PATH",
    "SOURCE_FANIN_PATH",
    "SOURCE_FANIN_HASH",
    "SOURCE_ARTIFACT_PATHS",
    "SOURCE_ARTIFACT_HASHES",
    "LEARNING_STATUS",
    "DECISION_RATIONALE",
    "CREATED_AT",
    "DECISION_HASH",
)

RECOMMENDATION_KEYS = (
    "STATIC_CHECK_CANDIDATE",
    "PROJECT_WIDE_HUNT_REQUEST",
    "TESTING_RULES_CANDIDATE",
)

# Live WAVE_4 terminal edges after mandatory-learning corrective.
LIVE_TERMINAL_PATH = (
    "FAN_IN_ASSEMBLER",
    "FAMILY_LEARNING_WORKER",
    "CLOSURE_OPERATOR",
)

LIVE_TERMINAL_EDGES = (
    ("FAN_IN_ASSEMBLER", "FAMILY_LEARNING_WORKER"),
    ("FAMILY_LEARNING_WORKER", "CLOSURE_OPERATOR"),
)


class LearningDecisionError(Exception):
    """Learning decision / closure-gate rejection."""

    def __init__(self, code: str, detail: str = "", payload: Optional[Dict[str, Any]] = None) -> None:
        self.code = code
        self.detail = detail
        self.payload = payload or {}
        super().__init__(f"{code}: {detail}" if detail else code)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_text(text: str) -> str:
    return _sha_bytes(text.encode("utf-8"))


def file_sha(path: Path) -> Optional[str]:
    """SHA-256 of file bytes, or None if missing."""
    if not path.exists():
        return None
    return _sha_bytes(path.read_bytes())


def family_dir_exists(case_root: Path) -> bool:
    """True when a materialized family/ directory is present."""
    return (Path(case_root) / "family").is_dir()


def canonical_decision_path(case_root: Path) -> Path:
    """Exactly one canonical LEARNING_DECISION path for the case."""
    case_root = Path(case_root)
    if family_dir_exists(case_root):
        return case_root / "family" / "LEARNING_DECISION.json"
    return case_root / "results" / "LEARNING_DECISION.json"


def resolve_decision_path(case_root: Path) -> Optional[Path]:
    """Return existing canonical path, or any present compat path."""
    case_root = Path(case_root)
    preferred = canonical_decision_path(case_root)
    if preferred.exists():
        return preferred
    # Prefer family when both somehow exist and family dir was created later
    family_path = case_root / "family" / "LEARNING_DECISION.json"
    results_path = case_root / "results" / "LEARNING_DECISION.json"
    if family_path.exists():
        return family_path
    if results_path.exists():
        return results_path
    return None


def full_packet_required_for_verdict(verdict: str) -> bool:
    """Whether LEARNING_PACKET.json is mandatory for this verdict."""
    return verdict in PACKET_REQUIRED_VERDICTS


def compute_decision_hash(decision: Dict[str, Any]) -> str:
    """Stable hash excluding DECISION_HASH itself."""
    payload = {k: v for k, v in decision.items() if k != "DECISION_HASH"}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return _sha_text(raw)


def build_learning_decision(
    *,
    case_id: str,
    learning_verdict: str,
    learning_status: str = "COMPLETE",
    bug_family_id: Optional[str] = None,
    invariant_id: Optional[str] = None,
    policy_already_exists: Optional[bool] = None,
    policy_refs: Optional[List[str]] = None,
    enforcement_gap: Optional[str] = None,
    promotion_decision: str = "NONE",
    recommendations: Optional[Dict[str, bool]] = None,
    source_fanin_path: str = "",
    source_fanin_hash: Optional[str] = None,
    source_artifact_paths: Optional[Dict[str, str]] = None,
    source_artifact_hashes: Optional[Dict[str, Optional[str]]] = None,
    decision_rationale: str = "",
    full_packet_path: Optional[str] = None,
    product_closure_valid: Optional[bool] = None,
    process_metadata_corrected: Optional[bool] = None,
    learning_stage_invoked: bool = True,
) -> Dict[str, Any]:
    """Construct a LEARNING_DECISION dict with required fields."""
    if learning_verdict not in LEARNING_VERDICTS:
        raise LearningDecisionError("BLOCKED_LEARNING_DECISION_INVALID", f"verdict={learning_verdict}")
    if learning_status not in LEARNING_STATUSES:
        raise LearningDecisionError("BLOCKED_LEARNING_DECISION_INVALID", f"status={learning_status}")

    recs = {k: False for k in RECOMMENDATION_KEYS}
    if recommendations:
        recs.update({k: bool(recommendations.get(k, False)) for k in RECOMMENDATION_KEYS})

    packet_required = full_packet_required_for_verdict(learning_verdict)
    if learning_verdict in CLOSURE_BLOCKING_VERDICTS and promotion_decision == "NONE":
        # blocking verdicts keep NONE unless owner queues something later
        pass

    decision: Dict[str, Any] = {
        "LEARNING_DECISION_ID": f"LDEC/{case_id}/{uuid.uuid4().hex[:10]}",
        "CASE_ID": case_id,
        "BUG_FAMILY_ID": bug_family_id,
        "INVARIANT_ID": invariant_id,
        "LEARNING_STAGE_INVOKED": bool(learning_stage_invoked),
        "LEARNING_VERDICT": learning_verdict,
        "POLICY_ALREADY_EXISTS": policy_already_exists,
        "POLICY_REFS": list(policy_refs or []),
        "ENFORCEMENT_GAP": enforcement_gap,
        "PROMOTION_DECISION": promotion_decision,
        "RECOMMENDATIONS": recs,
        "FULL_PACKET_REQUIRED": packet_required,
        "FULL_PACKET_PATH": full_packet_path if packet_required else None,
        "SOURCE_FANIN_PATH": source_fanin_path,
        "SOURCE_FANIN_HASH": source_fanin_hash,
        "SOURCE_ARTIFACT_PATHS": dict(source_artifact_paths or {}),
        "SOURCE_ARTIFACT_HASHES": dict(source_artifact_hashes or {}),
        "LEARNING_STATUS": learning_status,
        "DECISION_RATIONALE": decision_rationale,
        "CREATED_AT": _now(),
    }
    if product_closure_valid is not None:
        decision["PRODUCT_CLOSURE_VALID"] = product_closure_valid
    if process_metadata_corrected is not None:
        decision["PROCESS_METADATA_CORRECTED"] = process_metadata_corrected
    decision["DECISION_HASH"] = compute_decision_hash(decision)
    return decision


def write_learning_decision(case_root: Path, decision: Dict[str, Any]) -> Path:
    """Persist decision at the canonical path for this case."""
    case_root = Path(case_root)
    path = canonical_decision_path(case_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Recompute hash before write
    decision = dict(decision)
    decision["DECISION_HASH"] = compute_decision_hash(decision)
    path.write_text(json.dumps(decision, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Enforce single canonical location: remove the other if present
    other = (
        case_root / "results" / "LEARNING_DECISION.json"
        if path.parts[-2] == "family"
        else case_root / "family" / "LEARNING_DECISION.json"
    )
    if other.exists() and other.resolve() != path.resolve():
        other.unlink()
    return path


def load_learning_decision(case_root: Path) -> Optional[Dict[str, Any]]:
    """Load LEARNING_DECISION.json if present."""
    path = resolve_decision_path(case_root)
    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def validate_learning_decision(
    decision: Dict[str, Any],
    *,
    case_root: Optional[Path] = None,
    expect_fanin_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate schema, hash, verdict rules, and optional fan-in linkage."""
    missing = [f for f in REQUIRED_FIELDS if f not in decision]
    if missing:
        raise LearningDecisionError(
            "BLOCKED_LEARNING_DECISION_INVALID",
            f"missing={missing}",
            {"MISSING": missing},
        )

    if decision.get("LEARNING_STAGE_INVOKED") is not True:
        raise LearningDecisionError(
            "BLOCKED_LEARNING_DECISION_INVALID",
            "LEARNING_STAGE_INVOKED must be true",
        )

    verdict = decision.get("LEARNING_VERDICT")
    if verdict not in LEARNING_VERDICTS:
        raise LearningDecisionError("BLOCKED_LEARNING_DECISION_INVALID", f"verdict={verdict}")

    status = decision.get("LEARNING_STATUS")
    if status not in LEARNING_STATUSES:
        raise LearningDecisionError("BLOCKED_LEARNING_DECISION_INVALID", f"status={status}")

    promo = decision.get("PROMOTION_DECISION")
    if promo not in PROMOTION_ALLOWED_FOR_CLOSURE:
        raise LearningDecisionError("BLOCKED_LEARNING_DECISION_INVALID", f"promotion={promo}")

    recs = decision.get("RECOMMENDATIONS") or {}
    if not isinstance(recs, dict) or any(k not in recs for k in RECOMMENDATION_KEYS):
        raise LearningDecisionError(
            "BLOCKED_LEARNING_DECISION_INVALID",
            "RECOMMENDATIONS incomplete",
        )

    expected_packet = full_packet_required_for_verdict(str(verdict))
    if bool(decision.get("FULL_PACKET_REQUIRED")) != expected_packet:
        raise LearningDecisionError(
            "BLOCKED_LEARNING_DECISION_INVALID",
            "FULL_PACKET_REQUIRED mismatch for verdict",
        )

    stored_hash = decision.get("DECISION_HASH")
    if stored_hash != compute_decision_hash(decision):
        raise LearningDecisionError("BLOCKED_LEARNING_DECISION_INVALID", "DECISION_HASH mismatch")

    fanin_hash = decision.get("SOURCE_FANIN_HASH")
    if expect_fanin_hash is not None and fanin_hash != expect_fanin_hash:
        raise LearningDecisionError(
            "BLOCKED_LEARNING_DECISION_INVALID",
            "invalid fan-in hash",
            {"EXPECTED": expect_fanin_hash, "GOT": fanin_hash},
        )

    if case_root is not None:
        case_root = Path(case_root)
        fanin_rel = decision.get("SOURCE_FANIN_PATH") or ""
        if fanin_rel:
            fanin_path = case_root / fanin_rel.replace("\\", "/")
            if fanin_path.exists() and fanin_hash:
                actual = file_sha(fanin_path)
                if actual != fanin_hash:
                    raise LearningDecisionError(
                        "BLOCKED_LEARNING_DECISION_INVALID",
                        "invalid fan-in hash",
                        {"PATH": str(fanin_rel), "EXPECTED": fanin_hash, "GOT": actual},
                    )

        if expected_packet:
            pkt_rel = decision.get("FULL_PACKET_PATH")
            if not pkt_rel:
                raise LearningDecisionError(
                    "BLOCKED_LEARNING_DECISION_INVALID",
                    "FULL_PACKET_PATH required",
                )
            pkt_path = case_root / str(pkt_rel).replace("\\", "/")
            if not pkt_path.exists():
                raise LearningDecisionError(
                    "BLOCKED_LEARNING_INCOMPLETE",
                    "full packet required but absent",
                    {"FULL_PACKET_PATH": str(pkt_rel)},
                )

    return {
        "STATUS": "PASS",
        "LEARNING_DECISION_VALIDATED": True,
        "LEARNING_VERDICT": verdict,
        "LEARNING_STATUS": status,
    }


def evaluate_closure_learning_gate(
    case_root: Path,
    *,
    decision: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Gate CLOSURE_OPERATOR / close_family on a validated LEARNING_DECISION.

    Returns PASS dict or raises LearningDecisionError with required BLOCKED_* codes.
    """
    case_root = Path(case_root)
    loaded = decision if decision is not None else load_learning_decision(case_root)
    if loaded is None:
        raise LearningDecisionError("BLOCKED_LEARNING_DECISION_MISSING")

    try:
        validation = validate_learning_decision(loaded, case_root=case_root)
    except LearningDecisionError as exc:
        if exc.code == "BLOCKED_LEARNING_INCOMPLETE":
            raise
        if exc.code == "BLOCKED_LEARNING_DECISION_MISSING":
            raise
        # Normalize schema/hash failures
        if exc.code not in {
            "BLOCKED_LEARNING_DECISION_INVALID",
            "BLOCKED_LEARNING_INCOMPLETE",
            "BLOCKED_OWNER_LEARNING_DECISION_REQUIRED",
        }:
            raise LearningDecisionError(
                "BLOCKED_LEARNING_DECISION_INVALID",
                exc.detail,
                exc.payload,
            ) from exc
        raise

    status = loaded.get("LEARNING_STATUS")
    verdict = loaded.get("LEARNING_VERDICT")
    promo = loaded.get("PROMOTION_DECISION")

    if loaded.get("LEARNING_STAGE_INVOKED") is not True:
        raise LearningDecisionError("BLOCKED_LEARNING_DECISION_INVALID", "stage not invoked")

    if verdict == "OWNER_DECISION_REQUIRED" or status == "OWNER_WAIT":
        raise LearningDecisionError(
            "BLOCKED_OWNER_LEARNING_DECISION_REQUIRED",
            loaded.get("DECISION_RATIONALE") or "owner learning decision required",
        )

    if verdict == "LEARNING_BLOCKED" or status == "BLOCKED":
        raise LearningDecisionError(
            "BLOCKED_LEARNING_INCOMPLETE",
            loaded.get("DECISION_RATIONALE") or "learning blocked",
        )

    if status != "COMPLETE":
        raise LearningDecisionError("BLOCKED_LEARNING_INCOMPLETE", f"status={status}")

    if verdict not in CLOSURE_ALLOWED_VERDICTS:
        raise LearningDecisionError("BLOCKED_LEARNING_DECISION_INVALID", f"verdict={verdict}")

    if verdict in PACKET_REQUIRED_VERDICTS:
        if promo not in CANDIDATE_PROMOTION_REQUIRED:
            raise LearningDecisionError(
                "BLOCKED_LEARNING_DECISION_INVALID",
                f"candidate verdict requires promotion in {CANDIDATE_PROMOTION_REQUIRED}",
            )
        pkt_rel = loaded.get("FULL_PACKET_PATH")
        if not pkt_rel or not (case_root / str(pkt_rel).replace("\\", "/")).exists():
            raise LearningDecisionError(
                "BLOCKED_LEARNING_INCOMPLETE",
                "full packet required but absent",
            )
    else:
        if promo not in PROMOTION_ALLOWED_FOR_CLOSURE:
            raise LearningDecisionError("BLOCKED_LEARNING_DECISION_INVALID", f"promotion={promo}")

    # Promotion must never claim activation here
    if loaded.get("GLOBAL_RULES_ACTIVATED") is True:
        raise LearningDecisionError("BLOCKED_LEARNING_DECISION_INVALID", "global rules activated")
    if loaded.get("SUPERCLASS_ACTIVATED") is True:
        raise LearningDecisionError("BLOCKED_LEARNING_DECISION_INVALID", "superclass activated")

    return {
        "STATUS": "PASS",
        "LEARNING_DECISION_VALIDATED": True,
        "LEARNING_STAGE_INVOKED": True,
        "LEARNING_STATUS": "COMPLETE",
        "LEARNING_VERDICT": verdict,
        "PROMOTION_DECISION": promo,
        "FULL_PACKET_REQUIRED": loaded.get("FULL_PACKET_REQUIRED"),
        **validation,
    }


def mark_learning_timeout(case_root: Path, *, case_id: str, rationale: str = "learning timeout") -> Dict[str, Any]:
    """Persist LEARNING_BLOCKED decision after timeout; closure remains forbidden."""
    decision = build_learning_decision(
        case_id=case_id,
        learning_verdict="LEARNING_BLOCKED",
        learning_status="BLOCKED",
        promotion_decision="NONE",
        decision_rationale=rationale,
        source_fanin_path="",
        source_fanin_hash=None,
    )
    write_learning_decision(case_root, decision)
    return decision


def expected_next_after_fanin(case_root: Path) -> Tuple[str, Dict[str, Any]]:
    """Resume helper: after fan-in ready, dispatch learning or closure.

    Returns (EXPECTED_NEXT_COMMAND, detail).
    """
    case_root = Path(case_root)
    loaded = load_learning_decision(case_root)
    if loaded is None:
        return "FAMILY_LEARNING_WORKER", {
            "REASON": "LEARNING_DECISION_MISSING",
            "EXPECTED_NEXT_COMMAND": "FAMILY_LEARNING_WORKER",
        }
    try:
        evaluate_closure_learning_gate(case_root, decision=loaded)
        return "CLOSURE_OPERATOR", {
            "REASON": "LEARNING_COMPLETE",
            "EXPECTED_NEXT_COMMAND": "CLOSURE_OPERATOR",
        }
    except LearningDecisionError as exc:
        if exc.code == "BLOCKED_OWNER_LEARNING_DECISION_REQUIRED":
            return "OWNER_LEARNING_DECISION", {
                "REASON": exc.code,
                "EXPECTED_NEXT_COMMAND": "OWNER_LEARNING_DECISION",
            }
        return "FAMILY_LEARNING_WORKER", {
            "REASON": exc.code,
            "EXPECTED_NEXT_COMMAND": "FAMILY_LEARNING_WORKER",
            "DETAIL": exc.detail,
        }


def assert_no_auto_promotion_side_effects(decision: Dict[str, Any]) -> None:
    """T15 helper: existing-policy / deferred candidates must not launch remediations."""
    recs = decision.get("RECOMMENDATIONS") or {}
    # Recommendations may be recorded as candidates, but activation flags must be false/absent
    if decision.get("STATIC_CHECK_LAUNCHED") or decision.get("PROJECT_HUNT_LAUNCHED"):
        raise LearningDecisionError(
            "BLOCKED_LEARNING_DECISION_INVALID",
            "auto remediation launched from learning stage",
        )
    if decision.get("TESTING_RULES_MUTATED") or decision.get("GLOBAL_RULES_ACTIVATED"):
        raise LearningDecisionError(
            "BLOCKED_LEARNING_DECISION_INVALID",
            "rules mutated from learning stage",
        )
    if decision.get("SUPERCLASS_ACTIVATED"):
        raise LearningDecisionError(
            "BLOCKED_LEARNING_DECISION_INVALID",
            "superclass activated from learning stage",
        )
    # Recording True in RECOMMENDATIONS is allowed (candidate only)
    _ = recs
