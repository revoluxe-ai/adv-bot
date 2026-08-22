# -*- coding: utf-8 -*-
"""Machine-readable activation gate for Candidate /opsx-bug-team (BF-007)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ACTIVATION_PATH = Path(".cursor/pipeline/bug-team/ACTIVATION.json")


def load_activation(path: Path = ACTIVATION_PATH) -> Dict[str, Any]:
    """Load activation artifact; missing file ⇒ NOT_ACTIVE fail-closed."""
    if not path.exists():
        return {
            "SCHEMA_VERSION": 1,
            "COMMAND": "/opsx-bug-team",
            "RUNTIME_STATUS": "NOT_ACTIVE",
            "OWNER_ACTIVATION": "NOT_ISSUED",
            "ACTIVATION_RECEIPT": None,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def activation_state_hash(data: Optional[Dict[str, Any]] = None) -> str:
    """Stable hash of activation authority fields."""
    data = data or load_activation()
    payload = {
        "SCHEMA_VERSION": data.get("SCHEMA_VERSION"),
        "COMMAND": data.get("COMMAND"),
        "RUNTIME_STATUS": data.get("RUNTIME_STATUS"),
        "OWNER_ACTIVATION": data.get("OWNER_ACTIVATION"),
        "ACTIVATION_RECEIPT": data.get("ACTIVATION_RECEIPT"),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def is_active(data: Optional[Dict[str, Any]] = None) -> bool:
    data = data or load_activation()
    return (
        data.get("RUNTIME_STATUS") == "ACTIVE"
        and data.get("OWNER_ACTIVATION") == "ISSUED"
        and data.get("ACTIVATION_RECEIPT") is not None
    )


def check_invocation_gate(
    *,
    execution_mode: str,
    proof_root: Optional[Path] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Return (STATUS, details). Normal mode blocked while NOT_ACTIVE.

    REVIEW_PROOF_ONLY allowed only under .tmp/opsx-bug-team-harness/.
    """
    data = load_activation()
    state_hash = activation_state_hash(data)
    details: Dict[str, Any] = {
        "RUNTIME_STATUS": data.get("RUNTIME_STATUS"),
        "OWNER_ACTIVATION": data.get("OWNER_ACTIVATION"),
        "ACTIVATION_STATE_HASH": state_hash,
        "EXECUTION_MODE": execution_mode,
        "TASK_DISPATCH_COUNT": 0,
    }

    if execution_mode in ("REVIEW_PROOF_ONLY", "CONTROLLED_LIVE_UNCOMMITTED"):
        if proof_root is None:
            return "BLOCKED_PROOF_ROOT_REQUIRED", details
        proof = Path(proof_root).resolve()
        allowed = Path(".tmp/opsx-bug-team-harness").resolve()
        try:
            proof.relative_to(allowed)
        except ValueError:
            # Active live uncommitted may use real workspace — only when ACTIVE
            if execution_mode == "CONTROLLED_LIVE_UNCOMMITTED" and is_active(data):
                details["PROOF_MODE"] = False
                details["CONTROL_MODEL"] = "USER_REVIEWS_UNCOMMITTED_WORKTREE"
                details["LOCAL_WORKTREE_WRITES"] = "ALLOWED_AFTER_VALID_RED"
                details["OWNER_PRODUCTION_GATE"] = "NOT_REQUIRED_FOR_LOCAL_WORKTREE_WRITES"
                details["OWNER_CLOSURE_GATE"] = "NOT_REQUIRED"
                details["COMMIT_AUTHORITY"] = "USER_ONLY"
                details["EXTERNAL_MUTATIONS"] = "FORBIDDEN"
                return "ACTIVE_ALLOWED", details
            return "BLOCKED_PROOF_ROOT_OUTSIDE_HARNESS", details
        details["PROOF_MODE"] = True
        if execution_mode == "CONTROLLED_LIVE_UNCOMMITTED":
            details["CONTROL_MODEL"] = "USER_REVIEWS_UNCOMMITTED_WORKTREE"
            details["PRODUCT_WRITES"] = "ALLOWED_WITHIN_BOUNDARY_AFTER_RED_IN_PROOF"
            details["OWNER_PRODUCTION_GATE"] = "NOT_REQUIRED_FOR_LOCAL_WORKTREE_WRITES"
            details["OWNER_CLOSURE_GATE"] = "NOT_REQUIRED"
            details["COMMIT_AUTHORITY"] = "USER_ONLY"
            return "CONTROLLED_UNCOMMITTED_PROOF_ALLOWED", details
        details["PRODUCT_WRITES"] = "FORBIDDEN"
        return "PROOF_MODE_ALLOWED", details

    if execution_mode == "OWNER_GATED":
        if not is_active(data):
            details["STATUS"] = "BLOCKED_CANDIDATE_NOT_ACTIVE"
            return "BLOCKED_CANDIDATE_NOT_ACTIVE", details
        details["OWNER_PRODUCTION_GATE"] = "REQUIRED"
        details["OWNER_CLOSURE_GATE"] = "REQUIRED"
        return "ACTIVE_ALLOWED", details

    if not is_active(data):
        details["STATUS"] = "BLOCKED_CANDIDATE_NOT_ACTIVE"
        return "BLOCKED_CANDIDATE_NOT_ACTIVE", details

    return "ACTIVE_ALLOWED", details
