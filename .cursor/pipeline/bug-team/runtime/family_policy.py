# -*- coding: utf-8 -*-
"""V8 shadow feature gate for invariant-centered bug-family fanout.

ACTIVE_V1 remains the default runtime. Family fanout is enabled only when:
- BUG_FAMILY_FANOUT_ENABLED is true in policy (Owner future activation), or
- EXECUTION_MODE == CONTROLLED_TEST_FAMILY_FANOUT (harness only).

LIVE_RUNTIME_AUTHORITY: none for product defaults; this module is shadow policy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

POLICY_PATH = Path(".cursor/pipeline/bug-team/policy/BUG_FAMILY_FANOUT_POLICY.json")
CONTROLLED_TEST_MODE = "CONTROLLED_TEST_FAMILY_FANOUT"


def load_policy(path: Path = POLICY_PATH) -> Dict[str, Any]:
    """Load canonical BUG_FAMILY_FANOUT_POLICY.json."""
    if not path.exists():
        raise FileNotFoundError(f"missing family fanout policy: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def bug_family_fanout_enabled(policy: Dict[str, Any] | None = None) -> bool:
    """Return whether family fanout is the active default (normally False)."""
    pol = policy or load_policy()
    return bool(pol.get("BUG_FAMILY_FANOUT_ENABLED") is True)


def is_controlled_family_test(execution_mode: str) -> bool:
    return execution_mode == CONTROLLED_TEST_MODE


def blocks_closure_from_policy(
    relation: str,
    policy: Dict[str, Any] | None = None,
) -> bool:
    """Derive BLOCKS_FAMILY_CLOSURE from policy RELATION_RULES (NF-V9-003)."""
    pol = policy or load_policy()
    rules = (pol.get("RELATION_RULES") or {}).get(relation) or {}
    if "BLOCKS_FAMILY_CLOSURE" in rules:
        return bool(rules["BLOCKS_FAMILY_CLOSURE"])
    # Fallbacks for older policy shapes
    if relation == "SAME_INVARIANT_FINDING":
        return True
    if relation == "INCONCLUSIVE":
        return True
    if relation == "NEW_ROOT_CAUSE":
        return bool(rules.get("BLOCKS_PARENT_FAMILY_CLOSURE", False))
    return False


def check_family_fanout_gate(
    *,
    execution_mode: str,
    proof_root: Path | None = None,
    policy: Dict[str, Any] | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """Gate family-fanout orchestration.

    Returns (STATUS, details).
    """
    pol = policy or load_policy()
    details: Dict[str, Any] = {
        "V8_IMPLEMENTATION": pol.get("V8_IMPLEMENTATION", "SHADOW_CANDIDATE"),
        "CURRENT_ACTIVE_RUNTIME": pol.get("CURRENT_ACTIVE_RUNTIME", "ACTIVE_V1"),
        "BUG_FAMILY_FANOUT_ENABLED": bool(pol.get("BUG_FAMILY_FANOUT_ENABLED")),
        "EXECUTION_MODE": execution_mode,
    }
    if is_controlled_family_test(execution_mode):
        if proof_root is None:
            return "BLOCKED_PROOF_ROOT_REQUIRED", details
        proof = Path(proof_root).resolve()
        allowed = Path(".tmp/opsx-bug-team-harness").resolve()
        try:
            proof.relative_to(allowed)
        except ValueError:
            return "BLOCKED_PROOF_ROOT_OUTSIDE_HARNESS", details
        details["PROOF_MODE"] = True
        details["FAMILY_FANOUT_ALLOWED"] = True
        return "CONTROLLED_TEST_FAMILY_FANOUT_ALLOWED", details

    if bug_family_fanout_enabled(pol):
        details["FAMILY_FANOUT_ALLOWED"] = True
        return "FAMILY_FANOUT_ACTIVE_ALLOWED", details

    details["FAMILY_FANOUT_ALLOWED"] = False
    details["STATUS"] = "SHADOW_DISABLED"
    return "BLOCKED_FAMILY_FANOUT_SHADOW_DISABLED", details
