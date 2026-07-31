# -*- coding: utf-8 -*-
"""Durable Owner production / closure GO receipts (BF-004)."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple  # Any used by forbidden stubs

SCHEMA_VERSION = "1"


def _sha(obj: Dict[str, Any]) -> str:
    # Hash without RECEIPT_SHA256 field
    payload = {k: v for k, v in obj.items() if k != "RECEIPT_SHA256"}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def production_go_path(case_root: Path, finding_id: str) -> Path:
    return Path(case_root) / "gates" / f"OWNER-PRODUCTION-GO-{finding_id}.json"


def closure_go_path(case_root: Path, finding_id: str) -> Path:
    return Path(case_root) / "gates" / f"OWNER-FINAL-CLOSURE-{finding_id}.json"


def create_production_go(*_a: Any, **_k: Any) -> Dict[str, Any]:
    """REMOVED from worker-visible path (BF-V2-003).

    Valid receipts are created only via
    ``runtime.owner_decision_host.register_production_go`` with
    OWNER_AUTHORITY_TOKEN (host-only).
    """
    raise RuntimeError(
        "WORKER_OWNER_GO_CREATION_FORBIDDEN: use owner_decision_host.register_production_go"
    )


def create_closure_go(*_a: Any, **_k: Any) -> Dict[str, Any]:
    """REMOVED from worker-visible path — use owner_decision_host.register_closure_go."""
    raise RuntimeError(
        "WORKER_OWNER_GO_CREATION_FORBIDDEN: use owner_decision_host.register_closure_go"
    )


def validate_production_go_for_executor(
    receipt: Dict[str, Any],
    *,
    case_id: str,
    finding_id: str,
    red_evidence_sha256: str,
    frozen_test_hashes: Dict[str, str],
    expected_execution_route: str,
    checkpoint_generation: int,
    now: Optional[float] = None,
) -> Tuple[str, str]:
    """Return (PASS|BLOCKED_*, reason)."""
    now = now if now is not None else time.time()
    if receipt.get("GATE_TYPE") != "OWNER_PRODUCTION_GO":
        return "BLOCKED_OWNER_GO_MISMATCH", "wrong_gate_type"
    if receipt.get("CASE_ID") != case_id or receipt.get("FINDING_ID") != finding_id:
        return "BLOCKED_OWNER_GO_MISMATCH", "case_finding"
    if receipt.get("RED_EVIDENCE_SHA256") != red_evidence_sha256:
        return "BLOCKED_OWNER_GO_MISMATCH", "red_hash"
    if receipt.get("FROZEN_TEST_HASHES") != frozen_test_hashes:
        return "BLOCKED_OWNER_GO_MISMATCH", "frozen_hashes"
    if receipt.get("EXPECTED_EXECUTION_ROUTE") != expected_execution_route:
        return "BLOCKED_OWNER_GO_MISMATCH", "execution_route"
    if receipt.get("CHECKPOINT_GENERATION") != checkpoint_generation:
        return "BLOCKED_OWNER_GO_MISMATCH", "checkpoint_generation"
    if float(receipt.get("EXPIRES_AT", 0)) < now:
        return "BLOCKED_OWNER_GO_MISMATCH", "expired"
    if receipt.get("CONSUMED") is True:
        return "BLOCKED_OWNER_GO_REPLAY", "already_consumed"
    if receipt.get("RECEIPT_SHA256") != _sha(receipt):
        return "BLOCKED_OWNER_GO_MISMATCH", "receipt_tamper"
    return "PASS", "ok"


def consume_production_go(
    case_root: Path, finding_id: str, worker_execution_id: str
) -> Dict[str, Any]:
    path = production_go_path(case_root, finding_id)
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("CONSUMED"):
        raise RuntimeError("BLOCKED_OWNER_GO_REPLAY")
    receipt["CONSUMED"] = True
    receipt["CONSUMED_BY_WORKER_EXECUTION_ID"] = worker_execution_id
    receipt["CONSUMED_AT"] = time.time()
    receipt["RECEIPT_SHA256"] = _sha(receipt)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt
