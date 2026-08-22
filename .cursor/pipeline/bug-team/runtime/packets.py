# -*- coding: utf-8 -*-
"""Machine-enforced packet envelope + validator (BF-002).

UNKNOWN_FIELDS: REJECT (no silent accept). Extensions only under payload.extensions
if schema allows — top-level unknown keys are rejected.
"""

from __future__ import annotations

import hashlib
import json
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "1"
PACKET_TYPES = {"WORKER_INPUT", "WORKER_OUTPUT", "OWNER_GO_RECEIPT", "VALIDATION_RECEIPT"}

REQUIRED_TOP = (
    "SCHEMA_VERSION",
    "PACKET_TYPE",
    "PACKET_ID",
    "PACKET_GENERATION",
    "ORCHESTRATION_ID",
    "WORKER_EXECUTION_ID",
    "WORKER_ID",
    "CASE_ID",
    "FINDING_ID",
    "PARENT_PACKET_ID",
    "DEPENDENCY_PACKET_IDS",
    "DEPENDENCY_HASHES",
    "CHECKPOINT_GENERATION",
    "CREATED_AT",
    "EXPIRES_AT",
    "STATUS",
    "TERMINAL_STATUS",
    "PAYLOAD",
    "ARTIFACTS_WRITTEN",
    "EXECUTION_MODE",
    "ACTIVATION_STATE_HASH",
    "ATTEMPT",
)

WORKER_IDS = {
    "MATERIALIZER",
    "CLAIM_WORKER",
    "CLASSIFIER",
    "SPEC_UPDATE_WORKER",
    "RED_TEST_WORKER",
    "IMPLEMENTATION_EXECUTOR",
    "GREEN_VERIFIER",
    "TASK_COMPLETION_WORKER",
    "BOUNDED_HUNTER",
    "FAN_IN_ASSEMBLER",
    "FAMILY_LEARNING_WORKER",
    "CLOSURE_OPERATOR",
}


class PacketValidationError(Exception):
    """Packet rejected by machine validator."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return sha256_bytes(raw)


def write_packet(path: Path, packet: Dict[str, Any]) -> Dict[str, str]:
    """Write packet; return raw and canonical hashes (explicitly labeled)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(packet, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    raw_bytes = text.encode("utf-8")
    path.write_bytes(raw_bytes)
    return {
        "INPUT_PACKET_RAW_SHA256": sha256_bytes(raw_bytes),
        "INPUT_PACKET_CANONICAL_SHA256": sha256_json(packet),
        "RAW_SHA256": sha256_bytes(raw_bytes),
        "CANONICAL_SHA256": sha256_json(packet),
    }


def packet_hashes(path: Path) -> Dict[str, str]:
    raw = path.read_bytes()
    obj = json.loads(raw.decode("utf-8"))
    return {
        "RAW_SHA256": sha256_bytes(raw),
        "CANONICAL_SHA256": sha256_json(obj),
    }

def read_packet(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise PacketValidationError("EMPTY_PACKET")
    if not (text.startswith("{") or text.startswith("[")):
        raise PacketValidationError("PLAIN_TEXT_RESPONSE_REJECTED")
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PacketValidationError("PLAIN_TEXT_RESPONSE_REJECTED", str(exc)) from exc
    if not isinstance(obj, dict):
        raise PacketValidationError("PACKET_NOT_OBJECT")
    return obj


def new_input_packet(
    *,
    worker_id: str,
    orchestration_id: str,
    worker_execution_id: str,
    case_id: str,
    finding_id: Optional[str],
    checkpoint_generation: int,
    packet_generation: int,
    activation_state_hash: str,
    execution_mode: str,
    payload: Dict[str, Any],
    parent_packet_id: Optional[str] = None,
    dependency_packet_ids: Optional[List[str]] = None,
    dependency_hashes: Optional[Dict[str, str]] = None,
    ttl_seconds: int = 3600,
    attempt: int = 1,
) -> Dict[str, Any]:
    now = time.time()
    return {
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "PACKET_TYPE": "WORKER_INPUT",
        "PACKET_ID": f"PKT/{worker_execution_id}/IN",
        "PACKET_GENERATION": packet_generation,
        "ORCHESTRATION_ID": orchestration_id,
        "WORKER_EXECUTION_ID": worker_execution_id,
        "WORKER_ID": worker_id,
        "CASE_ID": case_id,
        "FINDING_ID": finding_id,
        "PARENT_PACKET_ID": parent_packet_id,
        "DEPENDENCY_PACKET_IDS": dependency_packet_ids or [],
        "DEPENDENCY_HASHES": dependency_hashes or {},
        "CHECKPOINT_GENERATION": checkpoint_generation,
        "CREATED_AT": now,
        "EXPIRES_AT": now + ttl_seconds,
        "STATUS": "PENDING",
        "TERMINAL_STATUS": None,
        "PAYLOAD": payload,
        "ARTIFACTS_WRITTEN": [],
        "EXECUTION_MODE": execution_mode,
        "ACTIVATION_STATE_HASH": activation_state_hash,
        "ATTEMPT": attempt,
    }


def validate_packet(
    packet: Dict[str, Any],
    *,
    expect_type: Optional[str] = None,
    expect_worker_id: Optional[str] = None,
    expect_wex: Optional[str] = None,
    expect_orch: Optional[str] = None,
    expect_case: Optional[str] = None,
    expect_finding: Optional[str] = None,
    expect_checkpoint_generation: Optional[int] = None,
    expect_packet_generation: Optional[int] = None,
    expect_activation_hash: Optional[str] = None,
    require_active_for_normal: bool = True,
    activation_is_active: bool = False,
    now: Optional[float] = None,
    allowed_artifact_prefixes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Non-authoritative packet helper (parser / static checks).

    ```text
    LIVE_TRANSITION_AUTHORITY: NONE
    ```

    Must NOT be used to advance checkpoint, consume Owner GO, or append
    success route events. Authoritative live gate:
    ``validate_packet_for_transition`` via ``live_task_hop.finalize_live_hop``.
    """
    now = now if now is not None else time.time()

    # Unknown top-level fields: REJECT
    unknown = sorted(set(packet.keys()) - set(REQUIRED_TOP))
    if unknown:
        raise PacketValidationError("UNKNOWN_FIELDS", ",".join(unknown))

    for key in REQUIRED_TOP:
        if key not in packet:
            raise PacketValidationError("MISSING_REQUIRED_FIELD", key)

    if packet["SCHEMA_VERSION"] != SCHEMA_VERSION:
        raise PacketValidationError("WRONG_SCHEMA_VERSION", str(packet["SCHEMA_VERSION"]))

    if packet["PACKET_TYPE"] not in PACKET_TYPES:
        raise PacketValidationError("WRONG_PACKET_TYPE", str(packet["PACKET_TYPE"]))
    if expect_type and packet["PACKET_TYPE"] != expect_type:
        raise PacketValidationError("WRONG_PACKET_TYPE", packet["PACKET_TYPE"])

    if packet["WORKER_ID"] not in WORKER_IDS:
        raise PacketValidationError("WRONG_WORKER_ID", str(packet["WORKER_ID"]))
    if expect_worker_id and packet["WORKER_ID"] != expect_worker_id:
        raise PacketValidationError("WRONG_WORKER_ID", packet["WORKER_ID"])
    if expect_wex and packet["WORKER_EXECUTION_ID"] != expect_wex:
        raise PacketValidationError("WRONG_WORKER_EXECUTION_ID")
    if expect_orch and packet["ORCHESTRATION_ID"] != expect_orch:
        raise PacketValidationError("WRONG_ORCHESTRATION_ID")
    if expect_case and packet["CASE_ID"] != expect_case:
        raise PacketValidationError("WRONG_CASE_ID")
    if expect_finding is not None and packet["FINDING_ID"] != expect_finding:
        raise PacketValidationError("WRONG_FINDING_ID")

    if expect_checkpoint_generation is not None:
        if packet["CHECKPOINT_GENERATION"] != expect_checkpoint_generation:
            raise PacketValidationError("STALE_CHECKPOINT_GENERATION")
    if expect_packet_generation is not None:
        if packet["PACKET_GENERATION"] != expect_packet_generation:
            raise PacketValidationError("STALE_PACKET_GENERATION")

    if packet["EXPIRES_AT"] is not None and float(packet["EXPIRES_AT"]) < now:
        raise PacketValidationError("EXPIRED_PACKET")

    if expect_activation_hash and packet["ACTIVATION_STATE_HASH"] != expect_activation_hash:
        raise PacketValidationError("ACTIVATION_HASH_MISMATCH")

    # Direct worker packet without orchestration identity
    if not packet.get("ORCHESTRATION_ID") or not str(packet["ORCHESTRATION_ID"]).startswith(
        "ORCH/"
    ):
        raise PacketValidationError("DIRECT_PACKET_WITHOUT_ORCHESTRATION")

    if require_active_for_normal and packet.get("EXECUTION_MODE") != "REVIEW_PROOF_ONLY":
        if not activation_is_active:
            raise PacketValidationError("NORMAL_RUNTIME_NOT_ACTIVE")

    # Dependency hash presence
    dep_ids = packet.get("DEPENDENCY_PACKET_IDS") or []
    dep_hashes = packet.get("DEPENDENCY_HASHES") or {}
    if not isinstance(dep_ids, list) or not isinstance(dep_hashes, dict):
        raise PacketValidationError("DEPENDENCY_STRUCTURE_INVALID")
    for dep in dep_ids:
        if dep not in dep_hashes:
            raise PacketValidationError("MISSING_DEPENDENCY", dep)

    # Self-reported artifacts vs allowlist prefixes (optional pre-check)
    arts = packet.get("ARTIFACTS_WRITTEN") or []
    if not isinstance(arts, list):
        raise PacketValidationError("ARTIFACTS_WRITTEN_NOT_LIST")
    if allowed_artifact_prefixes is not None:
        for a in arts:
            ap = str(a).replace("\\", "/")
            if not any(ap.startswith(p.replace("\\", "/")) or p in ap for p in allowed_artifact_prefixes):
                raise PacketValidationError("SELF_REPORTED_ARTIFACT_OUTSIDE_BOUNDARY", ap)

    # Output from incorrect worker already covered by expect_worker_id

    return {
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "PACKET_TYPE": "VALIDATION_RECEIPT",
        "RESULT": "PASS",
        "PACKET_ID": packet["PACKET_ID"],
        "UNKNOWN_FIELD_POLICY": "REJECT",
        "VALIDATED_AT": now,
    }


def validate_packet_for_transition(
    packet_path: Path,
    *,
    expected_context: Dict[str, Any],
    worker_contract: Dict[str, Any],
    dependency_manifest: Optional[Dict[str, Any]],
    active_checkpoint: Optional[Dict[str, Any]],
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Single authoritative validation gate (BF-V2-002).

    dependency_manifest keys:
      required: bool
      packets: { packet_id: { path, RAW_SHA256, CANONICAL_SHA256 } }
    """
    from .worker_contracts import allowed_pairs  # local import avoid cycle

    now = now if now is not None else time.time()
    try:
        packet = read_packet(packet_path)
    except PacketValidationError as exc:
        return reject_receipt(exc.code, exc.detail)

    try:
        # unknown fields + required
        unknown = sorted(set(packet.keys()) - set(REQUIRED_TOP))
        if unknown:
            raise PacketValidationError("UNKNOWN_FIELDS", ",".join(unknown))
        for key in REQUIRED_TOP:
            if key not in packet:
                raise PacketValidationError("MISSING_REQUIRED_FIELD", key)
        if packet["SCHEMA_VERSION"] != SCHEMA_VERSION:
            raise PacketValidationError("WRONG_SCHEMA_VERSION")
        if packet["PACKET_TYPE"] not in PACKET_TYPES:
            raise PacketValidationError("WRONG_PACKET_TYPE")
        if packet["PACKET_TYPE"] != expected_context.get("PACKET_TYPE", packet["PACKET_TYPE"]):
            if "PACKET_TYPE" in expected_context:
                raise PacketValidationError("WRONG_PACKET_TYPE")

        wid = packet["WORKER_ID"]
        if wid != expected_context.get("WORKER_ID", wid):
            raise PacketValidationError("WRONG_WORKER_ID")
        if packet["WORKER_EXECUTION_ID"] != expected_context.get(
            "WORKER_EXECUTION_ID", packet["WORKER_EXECUTION_ID"]
        ):
            if "WORKER_EXECUTION_ID" in expected_context:
                raise PacketValidationError("WRONG_WORKER_EXECUTION_ID")
        if packet["ORCHESTRATION_ID"] != expected_context.get(
            "ORCHESTRATION_ID", packet["ORCHESTRATION_ID"]
        ):
            if "ORCHESTRATION_ID" in expected_context:
                raise PacketValidationError("WRONG_ORCHESTRATION_ID")
        if "CASE_ID" in expected_context and packet["CASE_ID"] != expected_context["CASE_ID"]:
            raise PacketValidationError("WRONG_CASE_ID")
        if "FINDING_ID" in expected_context and packet["FINDING_ID"] != expected_context["FINDING_ID"]:
            raise PacketValidationError("WRONG_FINDING_ID")
        if "PACKET_GENERATION" in expected_context and packet[
            "PACKET_GENERATION"
        ] != expected_context["PACKET_GENERATION"]:
            raise PacketValidationError("STALE_PACKET_GENERATION")
        if "CHECKPOINT_GENERATION" in expected_context and packet[
            "CHECKPOINT_GENERATION"
        ] != expected_context["CHECKPOINT_GENERATION"]:
            raise PacketValidationError("STALE_CHECKPOINT_GENERATION")
        if "ATTEMPT" in expected_context and packet["ATTEMPT"] != expected_context["ATTEMPT"]:
            raise PacketValidationError("WRONG_ATTEMPT")
        if float(packet["EXPIRES_AT"]) < now:
            raise PacketValidationError("EXPIRED_PACKET")
        if "ACTIVATION_STATE_HASH" in expected_context and packet[
            "ACTIVATION_STATE_HASH"
        ] != expected_context["ACTIVATION_STATE_HASH"]:
            raise PacketValidationError("ACTIVATION_HASH_MISMATCH")
        if "EXECUTION_MODE" in expected_context and packet["EXECUTION_MODE"] != expected_context[
            "EXECUTION_MODE"
        ]:
            raise PacketValidationError("WRONG_EXECUTION_MODE")

        if not str(packet.get("ORCHESTRATION_ID", "")).startswith("ORCH/"):
            raise PacketValidationError("DIRECT_PACKET_WITHOUT_ORCHESTRATION")

        # Terminal status pairs (for OUTPUT; INPUT may have TERMINAL_STATUS null)
        if packet["PACKET_TYPE"] == "WORKER_OUTPUT":
            status = packet.get("STATUS")
            terminal = packet.get("TERMINAL_STATUS")
            if status is None or terminal is None:
                raise PacketValidationError("BLOCKED_INVALID_TERMINAL_STATUS", "missing")
            pairs = worker_contract.get("ALLOWED_STATUS_TERMINAL_PAIRS") or allowed_pairs(wid)
            if (status, terminal) not in pairs:
                raise PacketValidationError(
                    "BLOCKED_INVALID_TERMINAL_STATUS", f"{status}/{terminal}"
                )

        # Dependency manifest mandatory when packet lists deps OR context requires
        dep_ids = packet.get("DEPENDENCY_PACKET_IDS") or []
        dep_hashes = packet.get("DEPENDENCY_HASHES") or {}
        needs_manifest = bool(dep_ids) or expected_context.get("REQUIRE_DEPENDENCY_MANIFEST")
        if needs_manifest and dependency_manifest is None:
            raise PacketValidationError("DEPENDENCY_MANIFEST_NOT_SUPPLIED")
        if dependency_manifest is not None:
            packets_meta = dependency_manifest.get("packets") or {}
            for dep in dep_ids:
                if dep not in packets_meta:
                    raise PacketValidationError("MISSING_DEPENDENCY", dep)
                meta = packets_meta[dep]
                path = Path(meta["path"])
                if not path.exists():
                    raise PacketValidationError("MISSING_DEPENDENCY", dep)
                hashes = packet_hashes(path)
                dep_entry = dep_hashes.get(dep)
                if isinstance(dep_entry, dict):
                    expected_raw = dep_entry.get("RAW_SHA256") or meta.get("RAW_SHA256")
                    expected_can = dep_entry.get("CANONICAL_SHA256") or meta.get(
                        "CANONICAL_SHA256"
                    )
                else:
                    expected_raw = dep_entry or meta.get("RAW_SHA256")
                    expected_can = meta.get("CANONICAL_SHA256")
                if expected_raw and hashes["RAW_SHA256"] != expected_raw:
                    raise PacketValidationError("DEPENDENCY_HASH_MISMATCH", f"raw:{dep}")
                if expected_can and hashes["CANONICAL_SHA256"] != expected_can:
                    raise PacketValidationError("DEPENDENCY_HASH_MISMATCH", f"canonical:{dep}")

        if active_checkpoint is not None and packet["PACKET_TYPE"] == "WORKER_OUTPUT":
            # optional early active check (finalize does authoritative)
            if active_checkpoint.get("ACTIVE_WORKER_EXECUTION_ID") and packet[
                "WORKER_EXECUTION_ID"
            ] != active_checkpoint["ACTIVE_WORKER_EXECUTION_ID"]:
                if expected_context.get("ENFORCE_ACTIVE_WEX"):
                    raise PacketValidationError("REJECTED_STALE_OUTPUT", "wex")

    except PacketValidationError as exc:
        return reject_receipt(exc.code, exc.detail, packet)

    return {
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "PACKET_TYPE": "VALIDATION_RECEIPT",
        "RESULT": "PASS",
        "PACKET_ID": packet.get("PACKET_ID"),
        "UNKNOWN_FIELD_POLICY": "REJECT",
        "VALIDATED_AT": now,
        "CHECKPOINT_ADVANCED": False,  # caller advances after full hop
        "DEPENDENT_WORKERS_DISPATCHED": False,
        "PACKET": packet,
    }


def validate_dependency_hashes(
    dependency_hashes: Dict[str, str], path_by_id: Dict[str, Path]
) -> None:
    """Legacy helper — prefer validate_packet_for_transition."""
    for dep_id, expected in dependency_hashes.items():
        path = path_by_id.get(dep_id)
        if path is None or not path.exists():
            raise PacketValidationError("MISSING_DEPENDENCY", dep_id)
        actual = sha256_file(path)
        if actual != expected:
            raise PacketValidationError("DEPENDENCY_HASH_MISMATCH", dep_id)


def reject_receipt(code: str, detail: str = "", packet: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "PACKET_TYPE": "VALIDATION_RECEIPT",
        "RESULT": "REJECT",
        "CODE": code,
        "DETAIL": detail,
        "PACKET_ID": (packet or {}).get("PACKET_ID"),
        "UNKNOWN_FIELD_POLICY": "REJECT",
        "VALIDATED_AT": time.time(),
        "CHECKPOINT_ADVANCED": False,
        "DEPENDENT_WORKERS_DISPATCHED": False,
        "CURRENT_STATE": "BLOCKED_INVALID_PACKET",
        "VALIDATION_STATUS": "FAIL",
        "FAILURE_CODE": code,
    }
