# -*- coding: utf-8 -*-
"""Host-only Owner decision registration (BF-V2-003 / BF-ICT-001).

Workers MUST NOT import create APIs from this module.
OWNER_AUTHORITY_TOKEN never enters worker packets / DISPATCH / TRACE / reports.

validate_and_reserve enforces RED_PACKET_ID + RED_RAW + RED_CANONICAL + frozen
hashes with distinct mismatch codes (BF-ICT-001).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

SCHEMA_VERSION = "1"


class OwnerAuthorityError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def mint_owner_authority_token() -> str:
    """Create random host-only token. Do not write to worker-readable artifacts."""
    return secrets.token_hex(32)


def _token_signature(token: str, material: str) -> str:
    return hmac.new(token.encode("utf-8"), material.encode("utf-8"), hashlib.sha256).hexdigest()


def _sha_receipt(obj: Dict[str, Any]) -> str:
    payload = {k: v for k, v in obj.items() if k != "RECEIPT_SHA256"}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def production_go_path(case_root: Path, finding_id: str) -> Path:
    return Path(case_root) / "gates" / f"OWNER-PRODUCTION-GO-{finding_id}.json"


def closure_go_path(case_root: Path, finding_id: str) -> Path:
    return Path(case_root) / "gates" / f"OWNER-FINAL-CLOSURE-{finding_id}.json"


def compute_red_identity(red_packet_path: Path) -> Dict[str, str]:
    """Authoritative RED identity from packet file bytes (not worker-supplied alone)."""
    from . import packets

    path = Path(red_packet_path)
    hashes = packets.packet_hashes(path)
    obj = packets.read_packet(path)
    return {
        "packet_id": str(obj.get("PACKET_ID") or ""),
        "raw_sha256": hashes["RAW_SHA256"],
        "canonical_sha256": hashes["CANONICAL_SHA256"],
    }


def register_production_go(
    case_root: Path,
    *,
    owner_authority_token: str,
    case_id: str,
    finding_id: str,
    owner_decision: str,
    owner_decision_source: str,
    red_packet_id: str,
    red_raw_sha256: str,
    red_canonical_sha256: str,
    frozen_test_hashes: Dict[str, str],
    expected_execution_route: str,
    current_checkpoint_generation: int,
    ttl_seconds: int = 7200,
) -> Dict[str, Any]:
    """Host-only. Requires OWNER_AUTHORITY_TOKEN + explicit Owner decision."""
    if not owner_authority_token or len(owner_authority_token) < 32:
        raise OwnerAuthorityError("WRONG_AUTHORITY_TOKEN", "missing_or_short")
    if owner_decision != "GO":
        raise OwnerAuthorityError("OWNER_DECISION_NOT_GO", owner_decision)
    if not owner_decision_source or owner_decision_source.startswith("WORKER"):
        raise OwnerAuthorityError("INVALID_OWNER_DECISION_SOURCE", owner_decision_source)
    if not red_packet_id or not red_raw_sha256 or not red_canonical_sha256:
        raise OwnerAuthorityError("RED_IDENTITY_INCOMPLETE")

    now = time.time()
    nonce = secrets.token_hex(16)
    material = (
        f"{case_id}|{finding_id}|{red_packet_id}|{red_raw_sha256}|"
        f"{red_canonical_sha256}|{nonce}|{expected_execution_route}"
    )
    token_sig = _token_signature(owner_authority_token, material)

    receipt: Dict[str, Any] = {
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "GATE_TYPE": "OWNER_PRODUCTION_GO",
        "GATE_ID": f"GO/{case_id}/{finding_id}/{secrets.token_hex(6)}",
        "CASE_ID": case_id,
        "FINDING_ID": finding_id,
        "RED_PACKET_ID": red_packet_id,
        "RED_RAW_SHA256": red_raw_sha256,
        "RED_CANONICAL_SHA256": red_canonical_sha256,
        "RED_EVIDENCE_SHA256": red_raw_sha256,
        "FROZEN_TEST_HASHES": frozen_test_hashes,
        "EXPECTED_EXECUTION_ROUTE": expected_execution_route,
        "OWNER_DECISION": "GO",
        "OWNER_DECISION_SOURCE": owner_decision_source,
        "OWNER_DECISION_RECEIVED_AT": now,
        "NONCE": nonce,
        "AUTHORITY_TOKEN_SIGNATURE": token_sig,
        "CREATED_AT": now,
        "EXPIRES_AT": now + ttl_seconds,
        "CHECKPOINT_GENERATION": current_checkpoint_generation,
        "STATUS": "ISSUED",
        "CONSUMED": False,
        "RESERVED_BY_WORKER_EXECUTION_ID": None,
        "RESERVED_AT": None,
        "CONSUMED_BY_WORKER_EXECUTION_ID": None,
        "CONSUMED_AT": None,
    }
    receipt["RECEIPT_SHA256"] = _sha_receipt(receipt)
    path = production_go_path(case_root, finding_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt


def register_closure_go(
    case_root: Path,
    *,
    owner_authority_token: str,
    case_id: str,
    finding_id: str,
    fanin_raw_sha256: str,
    closure_readiness: str,
    owner_decision_source: str,
    ttl_seconds: int = 7200,
) -> Dict[str, Any]:
    if not owner_authority_token or len(owner_authority_token) < 32:
        raise OwnerAuthorityError("WRONG_AUTHORITY_TOKEN")
    if not owner_decision_source or owner_decision_source.startswith("WORKER"):
        raise OwnerAuthorityError("INVALID_OWNER_DECISION_SOURCE")
    now = time.time()
    nonce = secrets.token_hex(16)
    material = f"{case_id}|{finding_id}|{fanin_raw_sha256}|{nonce}|CLOSURE"
    token_sig = _token_signature(owner_authority_token, material)
    receipt: Dict[str, Any] = {
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "GATE_TYPE": "OWNER_FINAL_CLOSURE",
        "GATE_ID": f"CLOSE/{case_id}/{finding_id}/{secrets.token_hex(6)}",
        "CASE_ID": case_id,
        "FINDING_ID": finding_id,
        "FANIN_SHA256": fanin_raw_sha256,
        "CLOSURE_READINESS": closure_readiness,
        "OWNER_DECISION": "GO",
        "OWNER_DECISION_SOURCE": owner_decision_source,
        "NONCE": nonce,
        "AUTHORITY_TOKEN_SIGNATURE": token_sig,
        "CREATED_AT": now,
        "EXPIRES_AT": now + ttl_seconds,
        "STATUS": "ISSUED",
        "CONSUMED": False,
        "RESERVED_BY_WORKER_EXECUTION_ID": None,
        "RESERVED_AT": None,
        "CONSUMED_BY_WORKER_EXECUTION_ID": None,
        "CONSUMED_AT": None,
    }
    receipt["RECEIPT_SHA256"] = _sha_receipt(receipt)
    path = closure_go_path(case_root, finding_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt


def verify_token_signature(
    receipt: Dict[str, Any], owner_authority_token: str, *, closure: bool = False
) -> bool:
    if closure:
        material = (
            f"{receipt['CASE_ID']}|{receipt['FINDING_ID']}|{receipt['FANIN_SHA256']}|"
            f"{receipt['NONCE']}|CLOSURE"
        )
    else:
        material = (
            f"{receipt['CASE_ID']}|{receipt['FINDING_ID']}|{receipt['RED_PACKET_ID']}|"
            f"{receipt['RED_RAW_SHA256']}|{receipt['RED_CANONICAL_SHA256']}|"
            f"{receipt['NONCE']}|{receipt['EXPECTED_EXECUTION_ROUTE']}"
        )
    expected = _token_signature(owner_authority_token, material)
    return hmac.compare_digest(expected, receipt.get("AUTHORITY_TOKEN_SIGNATURE", ""))


def validate_and_reserve_production_go(
    case_root: Path,
    *,
    case_id: str,
    finding_id: str,
    red_packet_id: str,
    red_raw_sha256: str,
    red_canonical_sha256: str,
    frozen_test_hashes: Dict[str, str],
    expected_execution_route: str,
    checkpoint_generation: int,
    worker_execution_id: str,
    now: Optional[float] = None,
) -> Tuple[str, Dict[str, Any]]:
    """Prepare-gate: ISSUED → RESERVED. Enforces RED raw+canonical (BF-ICT-001).

    Returns (PASS|OWNER_GO_*_MISMATCH|BLOCKED_*, receipt).
    GO_REQUIRED only when no applicable receipt file exists.
    """
    now = now if now is not None else time.time()
    path = production_go_path(case_root, finding_id)
    if not path.exists():
        return "BLOCKED_OWNER_PRODUCTION_GO_REQUIRED", {}

    receipt = json.loads(path.read_text(encoding="utf-8"))

    if receipt.get("GATE_TYPE") != "OWNER_PRODUCTION_GO":
        return "OWNER_GO_CASE_MISMATCH", receipt
    if receipt.get("CASE_ID") != case_id:
        return "OWNER_GO_CASE_MISMATCH", receipt
    if receipt.get("FINDING_ID") != finding_id:
        return "OWNER_GO_FINDING_MISMATCH", receipt
    if receipt.get("RED_PACKET_ID") != red_packet_id:
        return "OWNER_GO_RED_PACKET_ID_MISMATCH", receipt
    if receipt.get("RED_RAW_SHA256") != red_raw_sha256:
        # legacy alias alone is not enough without canonical
        return "OWNER_GO_RED_RAW_HASH_MISMATCH", receipt
    if receipt.get("RED_CANONICAL_SHA256") != red_canonical_sha256:
        return "OWNER_GO_RED_CANONICAL_HASH_MISMATCH", receipt
    if receipt.get("FROZEN_TEST_HASHES") != frozen_test_hashes:
        return "OWNER_GO_FROZEN_HASH_MISMATCH", receipt
    if receipt.get("EXPECTED_EXECUTION_ROUTE") != expected_execution_route:
        return "OWNER_GO_ROUTE_MISMATCH", receipt
    if receipt.get("CHECKPOINT_GENERATION") != checkpoint_generation:
        return "OWNER_GO_CHECKPOINT_GENERATION_MISMATCH", receipt
    if float(receipt.get("EXPIRES_AT", 0)) < now:
        return "OWNER_GO_EXPIRED", receipt
    if receipt.get("CONSUMED") is True or receipt.get("STATUS") == "CONSUMED":
        return "BLOCKED_OWNER_GO_REPLAY", receipt
    if receipt.get("STATUS") == "RESERVED":
        if receipt.get("RESERVED_BY_WORKER_EXECUTION_ID") != worker_execution_id:
            return "BLOCKED_OWNER_GO_RESERVED_OTHER_WEX", receipt
        return "PASS", receipt
    if receipt.get("RECEIPT_SHA256") != _sha_receipt(receipt):
        return "OWNER_GO_RECEIPT_TAMPER", receipt

    receipt["STATUS"] = "RESERVED"
    receipt["RESERVED_BY_WORKER_EXECUTION_ID"] = worker_execution_id
    receipt["RESERVED_AT"] = now
    receipt["RECEIPT_SHA256"] = _sha_receipt(receipt)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return "PASS", receipt


def consume_reserved_production_go(
    case_root: Path, finding_id: str, worker_execution_id: str
) -> Dict[str, Any]:
    path = production_go_path(case_root, finding_id)
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if receipt.get("STATUS") != "RESERVED":
        raise OwnerAuthorityError("NOT_RESERVED", str(receipt.get("STATUS")))
    if receipt.get("RESERVED_BY_WORKER_EXECUTION_ID") != worker_execution_id:
        raise OwnerAuthorityError("RESERVED_OTHER_WEX")
    receipt["STATUS"] = "CONSUMED"
    receipt["CONSUMED"] = True
    receipt["CONSUMED_BY_WORKER_EXECUTION_ID"] = worker_execution_id
    receipt["CONSUMED_AT"] = time.time()
    receipt["RECEIPT_SHA256"] = _sha_receipt(receipt)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt


def worker_create_production_go_forbidden(*_a: Any, **_k: Any) -> None:
    """Explicit worker-callable stub — always rejects."""
    raise OwnerAuthorityError(
        "WORKER_OWNER_GO_CREATION_FORBIDDEN",
        "use runtime.owner_decision_host.register_production_go from host only",
    )
