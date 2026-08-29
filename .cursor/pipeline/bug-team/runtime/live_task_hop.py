# -*- coding: utf-8 -*-
"""Authoritative reusable prepare → host Task → finalize hop (BF-V2-001).

Python never simulates Cursor Task. Host agent invokes Task using
build_task_prompt() output, then calls finalize_live_hop().

Finalize authority comes from dispatch intent + checkpoint ACTIVE_* fields —
never from caller-supplied expected generation/attempt.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import (
    activation,
    control_model,
    execution_identity,
    fs_boundary,
    owner_decision_host,
    packets,
    retry_auth,
    route_trace,
)
from .worker_contracts import (
    DEFAULT_TIMEOUTS,
    MAX_ATTEMPTS,
    REQUIRES_OWNER_PRODUCTION_GO,
    allowed_pairs,
)

AUTHORITATIVE_PATH = "runtime/live_task_hop.py"
RETRY_ELIGIBLE = frozenset({"TIMEOUT", "FAIL", "CANCELLED", "BLOCKED_RETRYABLE"})
RETRY_INELIGIBLE = frozenset({"RUNNING", "PASS", "PENDING", "WAITING_OWNER", "BLOCKED_NON_RETRYABLE"})


class LiveHopError(Exception):
    """Prepare/finalize hop blocked or rejected."""

    def __init__(self, code: str, detail: str = "", payload: Optional[Dict[str, Any]] = None) -> None:
        self.code = code
        self.detail = detail
        self.payload = payload or {}
        super().__init__(f"{code}: {detail}" if detail else code)


def _wex_slug(wex: str) -> str:
    return wex.replace("/", "_")


def _sha_json(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def worker_contract_hash(worker_id: str) -> str:
    pairs = sorted(list(allowed_pairs(worker_id)))
    return _sha_json({"WORKER_ID": worker_id, "ALLOWED_STATUS_TERMINAL_PAIRS": pairs})


def write_boundary_hash(worker_id: str) -> str:
    allow = list(fs_boundary.WORKER_ALLOWLISTS.get(worker_id, []))
    return _sha_json({"WORKER_ID": worker_id, "ALLOWED_WRITE_PATHS": allow})


def compute_request_fingerprint(
    *,
    orchestration_id: str,
    case_id: str,
    finding_id: Optional[str],
    worker_id: str,
    attempt: int,
    packet_generation: int,
    checkpoint_generation: int,
    payload: Dict[str, Any],
    dependency_ids: List[str],
    dependency_hashes: Dict[str, Any],
    execution_mode: str,
    activation_state_hash: str,
    expected_output_rel: str,
) -> str:
    """Fingerprint of authority-relevant prepare request (before/without WEX)."""
    return _sha_json(
        {
            "ORCHESTRATION_ID": orchestration_id,
            "CASE_ID": case_id,
            "FINDING_ID": finding_id,
            "WORKER_ID": worker_id,
            "ATTEMPT": attempt,
            "PACKET_GENERATION": packet_generation,
            "CHECKPOINT_GENERATION": checkpoint_generation,
            "PAYLOAD": payload,
            "DEPENDENCY_PACKET_IDS": dependency_ids,
            "DEPENDENCY_HASHES": dependency_hashes,
            "EXECUTION_MODE": execution_mode,
            "ACTIVATION_STATE_HASH": activation_state_hash,
            "WORKER_CONTRACT_HASH": worker_contract_hash(worker_id),
            "ALLOWED_WRITE_BOUNDARY_HASH": write_boundary_hash(worker_id),
            "EXPECTED_OUTPUT_PATH": expected_output_rel,
        }
    )


def compute_prepare_fingerprint(
    *,
    request_fingerprint: str,
    worker_execution_id: str,
    input_raw: str,
    input_canonical: str,
) -> str:
    return _sha_json(
        {
            "REQUEST_FINGERPRINT_SHA256": request_fingerprint,
            "WORKER_EXECUTION_ID": worker_execution_id,
            "INPUT_PACKET_RAW_SHA256": input_raw,
            "INPUT_PACKET_CANONICAL_SHA256": input_canonical,
        }
    )


def load_checkpoint(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_checkpoint(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def persist_snapshot(path: Path, snap: fs_boundary.FsSnapshot) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"root": str(snap.root), "digests": snap.digests, "taken_at": time.time()},
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def load_snapshot(path: Path) -> fs_boundary.FsSnapshot:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return fs_boundary.FsSnapshot(root=Path(obj["root"]), digests=dict(obj["digests"]))


def build_task_prompt(
    *,
    worker_id: str,
    worker_execution_id: str,
    orchestration_id: str,
    case_id: str,
    finding_id: Optional[str],
    input_packet_path: Path,
    output_packet_path: Path,
    allowed_write_paths: List[str],
    execution_mode: str,
    attempt: int,
    timeout_seconds: int,
    checkpoint_path: Path,
) -> Dict[str, Any]:
    """Reusable Task prompt generator — no ad-hoc per-worker proof prompts."""
    prompt = "\n".join(
        [
            f"WORKER_ID: {worker_id}",
            f"WORKER_EXECUTION_ID: {worker_execution_id}",
            f"PARENT_ORCHESTRATION_ID: {orchestration_id}",
            f"CASE_ID: {case_id}",
            f"FINDING_ID: {finding_id}",
            f"EXECUTION_MODE: {execution_mode}",
            f"INPUT_PACKET_PATH: {input_packet_path}",
            f"OUTPUT_PACKET_PATH: {output_packet_path}",
            f"CHECKPOINT_PATH: {checkpoint_path}",
            f"ATTEMPT: {attempt}",
            f"TIMEOUT_SECONDS: {timeout_seconds}",
            "PACKET_FORMAT: JSON envelope SCHEMA_VERSION=1 WORKER_OUTPUT",
            "Write ONLY OUTPUT_PACKET_PATH as JSON with required top-level fields.",
            f"ALLOWED_WRITE_PATHS: {json.dumps(allowed_write_paths)}",
            "PRODUCT_WRITES: FORBIDDEN when EXECUTION_MODE=REVIEW_PROOF_ONLY.",
            "Do not create Owner GO receipts. Do not call owner registration APIs.",
            "Do not perform other workers' duties.",
            "MODEL_SELECTION_POLICY: inherit",
        ]
    )
    return {
        "description": f"opsx-bug-team/{worker_id}",
        "subagent_type": "generalPurpose",
        "model": "inherit",
        "prompt": prompt,
    }


def prepare_live_hop(
    *,
    case_root: Path,
    orchestration_id: str,
    worker_id: str,
    case_id: str,
    finding_id: Optional[str],
    execution_mode: str,
    checkpoint_generation: int,
    packet_generation: int,
    dependency_packets: Optional[Dict[str, Path]] = None,
    payload: Optional[Dict[str, Any]] = None,
    attempt: int = 1,
    parent_packet_id: Optional[str] = None,
    proof_root: Optional[Path] = None,
    owner_gate_context: Optional[Dict[str, Any]] = None,
    expected_output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Phase 1 — prepare. Returns hop prep dict or raises LiveHopError."""
    case_root = Path(case_root)
    proof_root = Path(proof_root) if proof_root else case_root
    team = case_root / "team"
    packets_dir = team / "packets"
    snaps_dir = team / "snapshots"
    intents_dir = team / "intents"
    for d in (packets_dir, snaps_dir, intents_dir, case_root / "results", case_root / "gates"):
        d.mkdir(parents=True, exist_ok=True)

    status, details = activation.check_invocation_gate(
        execution_mode=execution_mode, proof_root=proof_root
    )
    if status.startswith("BLOCKED_"):
        raise LiveHopError(status, json.dumps(details, ensure_ascii=False))

    checkpoint_path = team / "CHECKPOINT.json"
    checkpoint = load_checkpoint(checkpoint_path)

    # BF-ICT-003 / BF-ICT-RERUN-001: ACTIVE RUNNING lock + exact idempotency
    active_status = checkpoint.get("ACTIVE_STATUS")
    if active_status == "RUNNING":
        replay = _try_idempotent_replay(
            case_root=case_root,
            checkpoint=checkpoint,
            intents_dir=intents_dir,
            worker_id=worker_id,
            case_id=case_id,
            finding_id=finding_id,
            orchestration_id=orchestration_id,
            checkpoint_generation=checkpoint_generation,
            packet_generation=packet_generation,
            attempt=attempt,
            payload=payload or {"PROOF": True, "WORKER_ID": worker_id},
            dependency_packets=dependency_packets,
            execution_mode=execution_mode,
            expected_output_path=expected_output_path,
        )
        if replay is not None:
            return replay
        raise LiveHopError(
            "BLOCKED_ACTIVE_EXECUTION_RUNNING",
            f"active={checkpoint.get('ACTIVE_WORKER_EXECUTION_ID')} requested={worker_id}",
            {
                "STATUS": "BLOCKED_ACTIVE_EXECUTION_RUNNING",
                "ACTIVE_WORKER_EXECUTION_ID": checkpoint.get("ACTIVE_WORKER_EXECUTION_ID"),
                "ACTIVE_WORKER_ID": checkpoint.get("ACTIVE_WORKER_ID"),
                "REQUESTED_WORKER_ID": worker_id,
                "NEW_WORKER_EXECUTION_CREATED": False,
                "CHECKPOINT_ADVANCED": False,
                "DISPATCH_INTENT_CREATED": False,
                "TASK_DISPATCH_ALLOWED": False,
            },
        )
    if active_status in RETRY_ELIGIBLE:
        if not checkpoint.get("RETRY_AUTHORIZED"):
            raise LiveHopError(
                "BLOCKED_RETRY_AUTHORIZATION_REQUIRED",
                f"active_status={active_status}",
                {
                    "STATUS": "BLOCKED_RETRY_AUTHORIZATION_REQUIRED",
                    "ACTIVE_STATUS": active_status,
                    "ACTIVE_WORKER_EXECUTION_ID": checkpoint.get("ACTIVE_WORKER_EXECUTION_ID"),
                    "DISPATCH_INTENT_CREATED": False,
                    "NEW_WORKER_EXECUTION_CREATED": False,
                },
            )
    # Reserve one-time retry authorization (registry authority; receipt immutable)
    auth_obj: Optional[Dict[str, Any]] = None
    reserved_auth_id: Optional[str] = None
    if checkpoint.get("RETRY_AUTHORIZED") or active_status == "READY_FOR_RETRY":
        if checkpoint.get("ACTIVE_STATUS") == "RUNNING":
            raise LiveHopError(
                "BLOCKED_ACTIVE_EXECUTION_RUNNING",
                "retry_auth_while_running",
                {"STATUS": "BLOCKED_ACTIVE_EXECUTION_RUNNING", "DISPATCH_INTENT_CREATED": False},
            )
        auth_id = checkpoint.get("RETRY_AUTHORIZATION_ID")
        if not auth_id:
            raise LiveHopError("BLOCKED_RETRY_AUTHORIZATION_REQUIRED", "missing_auth_id")
        # Allocate WEX before RESERVED bind (BF-ICT-SR-001)
        wex = f"WEX/{worker_id}/{uuid.uuid4().hex[:10]}"
        try:
            auth_obj = retry_auth.reserve_authorization(
                case_root,
                auth_id=str(auth_id),
                new_worker_execution_id=wex,
                orchestration_id=orchestration_id,
                case_id=case_id,
                finding_id=finding_id,
                worker_id=worker_id,
            )
        except retry_auth.RetryAuthError as exc:
            raise LiveHopError(exc.code, exc.detail, exc.payload) from exc
        reserved_auth_id = str(auth_id)
        if int(auth_obj.get("NEXT_ATTEMPT") or 0) != attempt:
            raise LiveHopError("BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "attempt")
        if int(auth_obj.get("NEXT_PACKET_GENERATION") or 0) != packet_generation:
            raise LiveHopError("BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "packet_gen")
        if int(auth_obj.get("NEXT_CHECKPOINT_GENERATION") or 0) != checkpoint_generation:
            raise LiveHopError("BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "checkpoint_gen")
        _assert_previous_execution_authoritative(
            case_root=case_root,
            previous_wex=str(auth_obj["PREVIOUS_WORKER_EXECUTION_ID"]),
            orchestration_id=orchestration_id,
            case_id=case_id,
            finding_id=finding_id,
            expected_worker_id=str(auth_obj["WORKER_ID"]),
            expected_attempt=int(auth_obj["PREVIOUS_ATTEMPT"]),
            expected_packet_generation=int(auth_obj["PREVIOUS_PACKET_GENERATION"]),
            expected_checkpoint_generation=int(auth_obj["PREVIOUS_CHECKPOINT_GENERATION"]),
            expected_input_raw=auth_obj.get("PREVIOUS_INPUT_RAW_SHA256"),
            expected_input_canonical=auth_obj.get("PREVIOUS_INPUT_CANONICAL_SHA256"),
            require_terminal_eligible=False,
            allow_superseded_marker=True,
        )
    else:
        wex = f"WEX/{worker_id}/{uuid.uuid4().hex[:10]}"

    dep_ids, dep_hashes, dep_manifest_packets = _collect_dependency_state(dependency_packets)

    # Owner GO / local uncommitted authority BEFORE dispatch intent
    owner_receipt: Optional[Dict[str, Any]] = None
    local_authority: Optional[Dict[str, Any]] = None
    if worker_id in REQUIRES_OWNER_PRODUCTION_GO:
        if control_model.uses_local_uncommitted_authority(execution_mode):
            ctx = owner_gate_context or {}
            try:
                local_authority = control_model.validate_local_implementation_authority(
                    execution_mode=execution_mode,
                    red_status=str(ctx.get("red_status") or "RED_CONFIRMED"),
                    red_packet_valid=bool(ctx.get("red_packet_valid", True)),
                    frozen_test_hashes_valid=bool(ctx.get("frozen_test_hashes_valid", True)),
                    expected_execution_route_valid=bool(
                        ctx.get("expected_execution_route_valid", True)
                    ),
                    worker_write_boundary_valid=bool(ctx.get("worker_write_boundary_valid", True)),
                    external_mutation_required=bool(ctx.get("external_mutation_required", False)),
                    deploy_requested=bool(ctx.get("deploy_requested", False)),
                    git_commit_requested=bool(ctx.get("git_commit_requested", False)),
                    git_push_requested=bool(ctx.get("git_push_requested", False)),
                    irreversible_outside_repo=bool(ctx.get("irreversible_outside_repo", False)),
                )
            except control_model.ControlModelError as exc:
                raise LiveHopError(exc.code, exc.detail, exc.payload) from exc
        elif control_model.uses_owner_production_gate(execution_mode) or execution_mode in {
            "REVIEW_PROOF_ONLY",
            "NORMAL",
            "OWNER_GATED",
        }:
            # Legacy / proof / OWNER_GATED: Owner production GO required
            ctx = owner_gate_context or {}
            required = (
                "red_packet_id",
                "red_raw_sha256",
                "red_canonical_sha256",
                "frozen_test_hashes",
                "expected_execution_route",
            )
            if not all(k in ctx for k in required):
                raise LiveHopError(
                    "BLOCKED_OWNER_PRODUCTION_GO_REQUIRED",
                    "owner_gate_context incomplete",
                    {
                        "STATUS": "BLOCKED_OWNER_PRODUCTION_GO_REQUIRED",
                        "DISPATCH_INTENT_CREATED": False,
                        "TASK_DISPATCH_ALLOWED": False,
                        "TASK_DISPATCH_COUNT": 0,
                        "WAITING_OWNER": True,
                    },
                )
            go_status, owner_receipt = owner_decision_host.validate_and_reserve_production_go(
                case_root,
                case_id=case_id,
                finding_id=finding_id or "",
                red_packet_id=ctx["red_packet_id"],
                red_raw_sha256=ctx["red_raw_sha256"],
                red_canonical_sha256=ctx["red_canonical_sha256"],
                frozen_test_hashes=ctx["frozen_test_hashes"],
                expected_execution_route=ctx["expected_execution_route"],
                checkpoint_generation=checkpoint_generation,
                worker_execution_id=wex,
            )
            if go_status != "PASS":
                raise LiveHopError(
                    go_status
                    if go_status.startswith("BLOCKED_") or go_status.startswith("OWNER_GO_")
                    else "BLOCKED_OWNER_PRODUCTION_GO_REQUIRED",
                    go_status,
                    {
                        "STATUS": go_status,
                        "DISPATCH_INTENT_CREATED": False,
                        "TASK_DISPATCH_ALLOWED": False,
                        "TASK_DISPATCH_COUNT": 0,
                        "RECEIPT_RESERVED": False,
                        "GATE_STATUS": go_status,
                        "WAITING_OWNER": True,
                    },
                )
        else:
            raise LiveHopError(
                "BLOCKED_OWNER_PRODUCTION_GO_REQUIRED",
                f"unsupported_mode={execution_mode}",
            )

    pkt = packets.new_input_packet(
        worker_id=worker_id,
        orchestration_id=orchestration_id,
        worker_execution_id=wex,
        case_id=case_id,
        finding_id=finding_id,
        checkpoint_generation=checkpoint_generation,
        packet_generation=packet_generation,
        activation_state_hash=activation.activation_state_hash(),
        execution_mode=execution_mode,
        payload=payload or {"PROOF": True, "WORKER_ID": worker_id},
        parent_packet_id=parent_packet_id,
        dependency_packet_ids=dep_ids,
        dependency_hashes=dep_hashes,
        attempt=attempt,
    )
    in_path = packets_dir / f"{_wex_slug(wex)}.in.json"
    hash_info = packets.write_packet(in_path, pkt)

    dep_manifest = {"packets": dep_manifest_packets} if dep_manifest_packets else None
    if dep_ids and dep_manifest is None:
        raise LiveHopError("DEPENDENCY_MANIFEST_NOT_SUPPLIED")

    contract = {
        "WORKER_ID": worker_id,
        "ALLOWED_STATUS_TERMINAL_PAIRS": list(allowed_pairs(worker_id)),
    }
    # INPUT may have TERMINAL_STATUS null — gate for input uses schema only
    val = packets.validate_packet_for_transition(
        in_path,
        expected_context={
            "PACKET_TYPE": "WORKER_INPUT",
            "WORKER_ID": worker_id,
            "WORKER_EXECUTION_ID": wex,
            "ORCHESTRATION_ID": orchestration_id,
            "CASE_ID": case_id,
            "FINDING_ID": finding_id,
            "PACKET_GENERATION": packet_generation,
            "CHECKPOINT_GENERATION": checkpoint_generation,
            "ATTEMPT": attempt,
            "ACTIVATION_STATE_HASH": activation.activation_state_hash(),
            "EXECUTION_MODE": execution_mode,
        },
        worker_contract=contract,
        dependency_manifest=dep_manifest,
        active_checkpoint=checkpoint or None,
    )
    if val.get("RESULT") != "PASS":
        raise LiveHopError(val.get("FAILURE_CODE") or val.get("CODE") or "PACKET_VALIDATION_FAIL")

    # For WORKER_INPUT, terminal pairs are skipped — good.
    # Re-validate unknown-fields etc already done.

    allowed = list(fs_boundary.WORKER_ALLOWLISTS.get(worker_id, []))
    out_path = (
        Path(expected_output_path)
        if expected_output_path is not None
        else packets_dir / f"{_wex_slug(wex)}.out.json"
    )
    try:
        expected_output_rel = str(out_path.resolve().relative_to(case_root.resolve()))
    except ValueError:
        expected_output_rel = str(out_path)

    activation_hash = activation.activation_state_hash()
    effective_payload = payload or {"PROOF": True, "WORKER_ID": worker_id}
    request_fp = compute_request_fingerprint(
        orchestration_id=orchestration_id,
        case_id=case_id,
        finding_id=finding_id,
        worker_id=worker_id,
        attempt=attempt,
        packet_generation=packet_generation,
        checkpoint_generation=checkpoint_generation,
        payload=effective_payload,
        dependency_ids=dep_ids,
        dependency_hashes=dep_hashes,
        execution_mode=execution_mode,
        activation_state_hash=activation_hash,
        expected_output_rel=expected_output_rel,
    )

    before = fs_boundary.FsSnapshot.take(case_root)
    before_path = snaps_dir / f"{_wex_slug(wex)}.before.json"
    persist_snapshot(before_path, before)

    prepared_at = time.time()
    timeout_seconds = DEFAULT_TIMEOUTS.get(worker_id, 600)
    prepare_fp = compute_prepare_fingerprint(
        request_fingerprint=request_fp,
        worker_execution_id=wex,
        input_raw=hash_info["RAW_SHA256"],
        input_canonical=hash_info["CANONICAL_SHA256"],
    )
    intent = {
        "SCHEMA_VERSION": "1",
        "INTENT_TYPE": "LIVE_TASK_DISPATCH",
        "STATUS": "PREPARED",
        "ORCHESTRATION_ID": orchestration_id,
        "WORKER_ID": worker_id,
        "WORKER_EXECUTION_ID": wex,
        "CASE_ID": case_id,
        "FINDING_ID": finding_id,
        "ATTEMPT": attempt,
        "MAX_ATTEMPTS": MAX_ATTEMPTS.get(worker_id, 2),
        "PACKET_GENERATION": packet_generation,
        "CHECKPOINT_GENERATION": checkpoint_generation,
        "INPUT_PACKET_PATH": str(in_path),
        "INPUT_PACKET_RAW_SHA256": hash_info["RAW_SHA256"],
        "INPUT_PACKET_CANONICAL_SHA256": hash_info["CANONICAL_SHA256"],
        "EXPECTED_OUTPUT_PATH": str(out_path),
        "EXPECTED_OUTPUT_REL": expected_output_rel,
        "BEFORE_SNAPSHOT_PATH": str(before_path),
        "ALLOWED_WRITE_PATHS": allowed,
        "ALLOWED_WRITE_BOUNDARY_HASH": write_boundary_hash(worker_id),
        "WORKER_CONTRACT_HASH": worker_contract_hash(worker_id),
        "ACTIVATION_STATE_HASH": activation_hash,
        "EXECUTION_MODE": execution_mode,
        "REQUEST_FINGERPRINT_SHA256": request_fp,
        "PREPARE_FINGERPRINT_SHA256": prepare_fp,
        "PREPARED_AT": prepared_at,
        "TASK_STARTED_AT": None,
        "TASK_FINISHED_AT": None,
        "FINALIZED_AT": None,
        "DURATION_MS": None,
        "OWNER_RECEIPT_GATE_ID": (owner_receipt or {}).get("GATE_ID"),
        "LOCAL_IMPLEMENTATION_AUTHORIZED": bool(
            (local_authority or {}).get("LOCAL_IMPLEMENTATION_AUTHORIZED")
        ),
        "LIVE_RUNTIME_AUTHORITY": AUTHORITATIVE_PATH,
        "DEPENDENCY_PACKET_IDS": dep_ids,
        "DEPENDENCY_PACKETS": dep_manifest_packets,
        "DEPENDENCY_MANIFEST": {"packets": dep_manifest_packets},
        "DEPENDENCY_RAW_HASHES": {k: v["RAW_SHA256"] for k, v in dep_hashes.items()},
        "DEPENDENCY_CANONICAL_HASHES": {k: v["CANONICAL_SHA256"] for k, v in dep_hashes.items()},
        "RETRY_AUTHORIZATION_ID": (auth_obj or {}).get("RETRY_AUTHORIZATION_ID"),
    }
    intent_path = intents_dir / f"{_wex_slug(wex)}.intent.json"
    intent_path.write_text(json.dumps(intent, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Active execution record (BF-V2-004 / BF-ICT-RERUN-001)
    checkpoint.update(
        {
            "CASE_ID": case_id,
            "FINDING_ID": finding_id,
            "ORCHESTRATION_ID": orchestration_id,
            "CHECKPOINT_GENERATION": checkpoint_generation,
            "PACKET_GENERATION": packet_generation,
            "ACTIVE_WORKER_EXECUTION_ID": wex,
            "ACTIVE_WORKER_ID": worker_id,
            "ACTIVE_ATTEMPT": attempt,
            "ACTIVE_PACKET_GENERATION": packet_generation,
            "ACTIVE_CHECKPOINT_GENERATION": checkpoint_generation,
            "ACTIVE_INPUT_PACKET_SHA256": hash_info["RAW_SHA256"],
            "ACTIVE_INPUT_PACKET_CANONICAL_SHA256": hash_info["CANONICAL_SHA256"],
            "ACTIVE_PREPARE_FINGERPRINT_SHA256": prepare_fp,
            "ACTIVE_REQUEST_FINGERPRINT_SHA256": request_fp,
            "ACTIVE_STARTED_AT": prepared_at,
            "ACTIVE_STATUS": "RUNNING",
            "RETRY_AUTHORIZED": False,
            "RETRY_AUTHORIZATION_ID": None,
            "EXECUTION_MODE": execution_mode,
            "UPDATED_AT": prepared_at,
        }
    )
    save_checkpoint(checkpoint_path, checkpoint)

    if reserved_auth_id is not None and auth_obj is not None:
        prev_wex = str(auth_obj["PREVIOUS_WORKER_EXECUTION_ID"])
        prev_intent_path = intents_dir / f"{_wex_slug(prev_wex)}.intent.json"
        if prev_intent_path.exists():
            prev_intent = json.loads(prev_intent_path.read_text(encoding="utf-8"))
            prev_intent["SUPERSEDED_BY_WORKER_EXECUTION_ID"] = wex
            prev_intent["SUPERSEDED_AT"] = prepared_at
            prev_intent_path.write_text(
                json.dumps(prev_intent, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        _append_retry_dispatch_event(
            case_root=case_root,
            case_id=case_id,
            finding_id=finding_id,
            orchestration_id=orchestration_id,
            worker_id=worker_id,
            previous_wex=prev_wex,
            new_wex=wex,
            attempt=attempt,
            auth_id=reserved_auth_id,
            at=prepared_at,
        )

    _append_prepare_dispatch_record(
        case_root=case_root,
        intent=intent,
        event_type="PREPARE_DISPATCH_INTENT",
    )

    task_args = build_task_prompt(
        worker_id=worker_id,
        worker_execution_id=wex,
        orchestration_id=orchestration_id,
        case_id=case_id,
        finding_id=finding_id,
        input_packet_path=in_path,
        output_packet_path=out_path,
        allowed_write_paths=allowed,
        execution_mode=execution_mode,
        attempt=attempt,
        timeout_seconds=timeout_seconds,
        checkpoint_path=checkpoint_path,
    )

    return {
        "STATUS": "PREPARED",
        "WORKER_EXECUTION_ID": wex,
        "ATTEMPT": attempt,
        "INPUT_PACKET_PATH": str(in_path),
        "INPUT_PACKET_RAW_SHA256": hash_info["RAW_SHA256"],
        "INPUT_PACKET_CANONICAL_SHA256": hash_info["CANONICAL_SHA256"],
        "BEFORE_SNAPSHOT_PATH": str(before_path),
        "DISPATCH_INTENT_PATH": str(intent_path),
        "EXPECTED_OUTPUT_PATH": str(out_path),
        "ALLOWED_WRITE_PATHS": allowed,
        "TASK_ARGS": task_args,
        "DISPATCH_INTENT_CREATED": True,
        "TASK_DISPATCH_ALLOWED": True,
        "CHECKPOINT_PATH": str(checkpoint_path),
        "TIMEOUT_SECONDS": timeout_seconds,
        "REQUEST_FINGERPRINT_SHA256": request_fp,
        "PREPARE_FINGERPRINT_SHA256": prepare_fp,
        "NEW_WORKER_EXECUTION_CREATED": True,
        "CHECKPOINT_CHANGED": True,
        "LOCAL_IMPLEMENTATION_AUTHORIZED": bool(
            (local_authority or {}).get("LOCAL_IMPLEMENTATION_AUTHORIZED")
        ),
        "WAITING_OWNER": False
        if (local_authority or {}).get("LOCAL_IMPLEMENTATION_AUTHORIZED")
        else None,
    }


def _collect_dependency_state(
    dependency_packets: Optional[Dict[str, Path]],
) -> Tuple[List[str], Dict[str, Any], Dict[str, Any]]:
    dep_ids: List[str] = []
    dep_hashes: Dict[str, Any] = {}
    dep_manifest_packets: Dict[str, Any] = {}
    for dep_id, dep_path in (dependency_packets or {}).items():
        dep_path = Path(dep_path)
        if not dep_path.exists():
            raise LiveHopError("DEPENDENCY_PACKET_MISSING", str(dep_path))
        hashes = packets.packet_hashes(dep_path)
        dep_ids.append(dep_id)
        dep_hashes[dep_id] = {
            "RAW_SHA256": hashes["RAW_SHA256"],
            "CANONICAL_SHA256": hashes["CANONICAL_SHA256"],
        }
        dep_manifest_packets[dep_id] = {
            "path": str(dep_path),
            "RAW_SHA256": hashes["RAW_SHA256"],
            "CANONICAL_SHA256": hashes["CANONICAL_SHA256"],
        }
    return dep_ids, dep_hashes, dep_manifest_packets


def _append_prepare_dispatch_record(*, case_root: Path, intent: Dict[str, Any], event_type: str) -> None:
    dispatch_path = Path(case_root) / "team" / "DISPATCH.jsonl"
    dispatch_path.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "EVENT_TYPE": event_type,
        "TIMESTAMP": time.time(),
        "WORKER_EXECUTION_ID": intent.get("WORKER_EXECUTION_ID"),
        "WORKER_ID": intent.get("WORKER_ID"),
        "CASE_ID": intent.get("CASE_ID"),
        "FINDING_ID": intent.get("FINDING_ID"),
        "ORCHESTRATION_ID": intent.get("ORCHESTRATION_ID"),
        "ATTEMPT": intent.get("ATTEMPT"),
        "PACKET_GENERATION": intent.get("PACKET_GENERATION"),
        "CHECKPOINT_GENERATION": intent.get("CHECKPOINT_GENERATION"),
        "INPUT_PACKET_RAW_SHA256": intent.get("INPUT_PACKET_RAW_SHA256"),
        "INPUT_PACKET_CANONICAL_SHA256": intent.get("INPUT_PACKET_CANONICAL_SHA256"),
        "PREPARE_FINGERPRINT_SHA256": intent.get("PREPARE_FINGERPRINT_SHA256"),
        "REQUEST_FINGERPRINT_SHA256": intent.get("REQUEST_FINGERPRINT_SHA256"),
        "STATUS": intent.get("STATUS"),
    }
    with dispatch_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _append_retry_dispatch_event(
    *,
    case_root: Path,
    case_id: str,
    finding_id: Optional[str],
    orchestration_id: str,
    worker_id: str,
    previous_wex: str,
    new_wex: str,
    attempt: int,
    auth_id: str,
    at: float,
) -> None:
    dispatch_path = Path(case_root) / "team" / "DISPATCH.jsonl"
    with dispatch_path.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "EVENT_TYPE": "RETRY_DISPATCH",
                    "TIMESTAMP": at,
                    "CASE_ID": case_id,
                    "FINDING_ID": finding_id,
                    "ORCHESTRATION_ID": orchestration_id,
                    "WORKER_ID": worker_id,
                    "PREVIOUS_WORKER_EXECUTION_ID": previous_wex,
                    "NEW_WORKER_EXECUTION_ID": new_wex,
                    "ATTEMPT": attempt,
                    "RETRY_AUTHORIZATION_ID": auth_id,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    trace_path = Path(case_root) / "results" / "ROUTE-TRACE.jsonl"
    seq = route_trace.last_sequence(trace_path) + 1
    route_trace.append_event(
        trace_path,
        {
            "SCHEMA_VERSION": "2",
            "EVENT_ID": f"RTE/{case_id}/{seq}",
            "SEQUENCE": seq,
            "CASE_ID": case_id,
            "FINDING_ID": finding_id,
            "ORCHESTRATION_ID": orchestration_id,
            "ACTOR_ROLE": "ORCHESTRATOR",
            "WORKER_ID": worker_id,
            "WORKER_EXECUTION_ID": new_wex,
            "CURSOR_AGENT_ID": None,
            "EVENT_TYPE": "RETRY_DISPATCH",
            "FROM_STATE": "READY_FOR_RETRY",
            "TO_STATE": "RUNNING",
            "CHOSEN_ROUTE": None,
            "EXPECTED_NEXT_COMMAND": None,
            "ACTUAL_NEXT_COMMAND": None,
            "NEXT_COMMAND_RECONCILIATION": "NOT_APPLICABLE",
            "EXPECTED_EXECUTION_ROUTE": None,
            "ACTUAL_EXECUTION_ROUTE": None,
            "ROUTE_RECONCILIATION": "NOT_APPLICABLE",
            "STARTED_AT": at,
            "FINISHED_AT": at,
            "DURATION_MS": 0,
            "ATTEMPT": attempt,
            "OWNER_GATE_STATUS": None,
            "BLOCKED_REASON": None,
            "TIMEOUT_REASON": None,
            "INPUT_PACKET_PATH": None,
            "INPUT_PACKET_SHA256": None,
            "OUTPUT_PACKET_PATH": None,
            "OUTPUT_PACKET_SHA256": None,
            "ARTIFACT_PATHS": [f"team/retries/{auth_id}.json"],
            "TERMINAL_STATUS": "RETRY_DISPATCH",
            "PREVIOUS_WORKER_EXECUTION_ID": previous_wex,
            "RETRY_AUTHORIZATION_ID": auth_id,
        },
    )


def _raise_idempotency_mismatch(code: str, detail: str = "") -> None:
    raise LiveHopError(
        "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH",
        detail or code,
        {
            "STATUS": "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH",
            "FAILURE_CODE": code,
            "NEW_WORKER_EXECUTION_CREATED": False,
            "CHECKPOINT_CHANGED": False,
            "DISPATCH_INTENT_CREATED": False,
            "OWNER_RECEIPT_RESERVED": False,
            "TASK_DISPATCH_ALLOWED": False,
        },
    )


def _try_idempotent_replay(
    *,
    case_root: Path,
    checkpoint: Dict[str, Any],
    intents_dir: Path,
    worker_id: str,
    case_id: str,
    finding_id: Optional[str],
    orchestration_id: str,
    checkpoint_generation: int,
    packet_generation: int,
    attempt: int,
    payload: Dict[str, Any],
    dependency_packets: Optional[Dict[str, Path]],
    execution_mode: str,
    expected_output_path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Return existing prep only when authority-relevant prepare fields match exactly."""
    active_wex = checkpoint.get("ACTIVE_WORKER_EXECUTION_ID")
    if not active_wex:
        return None
    intent_path = intents_dir / f"{_wex_slug(active_wex)}.intent.json"
    if not intent_path.exists():
        return None
    intent = json.loads(intent_path.read_text(encoding="utf-8"))
    identity_ok = (
        intent.get("WORKER_ID") == worker_id
        and intent.get("CASE_ID") == case_id
        and intent.get("FINDING_ID") == finding_id
        and intent.get("ORCHESTRATION_ID") == orchestration_id
        and intent.get("WORKER_EXECUTION_ID") == active_wex
        and checkpoint.get("ACTIVE_WORKER_ID") == worker_id
        and int(intent.get("ATTEMPT") or -1) == attempt
    )
    if not identity_ok:
        return None

    # Same idempotency identity — generations and fingerprints must match exactly
    if int(intent.get("PACKET_GENERATION") or -1) != packet_generation:
        _raise_idempotency_mismatch("IDEMPOTENCY_PACKET_GENERATION_MISMATCH")
    if int(intent.get("CHECKPOINT_GENERATION") or -1) != checkpoint_generation:
        _raise_idempotency_mismatch("IDEMPOTENCY_CHECKPOINT_GENERATION_MISMATCH")

    # Identity matches — must also match exact input/deps/contract fingerprint
    try:
        dep_ids, dep_hashes, _ = _collect_dependency_state(dependency_packets)
    except LiveHopError as exc:
        if exc.code == "DEPENDENCY_PACKET_MISSING":
            _raise_idempotency_mismatch("IDEMPOTENCY_DEPENDENCY_HASH_MISMATCH", "dependency_missing")
        raise

    out_path = (
        Path(expected_output_path)
        if expected_output_path is not None
        else Path(intent["EXPECTED_OUTPUT_PATH"])
    )
    try:
        expected_output_rel = str(out_path.resolve().relative_to(Path(case_root).resolve()))
    except ValueError:
        expected_output_rel = str(out_path)

    activation_hash = activation.activation_state_hash()
    request_fp = compute_request_fingerprint(
        orchestration_id=orchestration_id,
        case_id=case_id,
        finding_id=finding_id,
        worker_id=worker_id,
        attempt=attempt,
        packet_generation=packet_generation,
        checkpoint_generation=checkpoint_generation,
        payload=payload,
        dependency_ids=dep_ids,
        dependency_hashes=dep_hashes,
        execution_mode=execution_mode,
        activation_state_hash=activation_hash,
        expected_output_rel=expected_output_rel,
    )

    if intent.get("WORKER_CONTRACT_HASH") != worker_contract_hash(worker_id):
        _raise_idempotency_mismatch("IDEMPOTENCY_CONTRACT_HASH_MISMATCH")
    if intent.get("ALLOWED_WRITE_BOUNDARY_HASH") != write_boundary_hash(worker_id):
        _raise_idempotency_mismatch("IDEMPOTENCY_WRITE_BOUNDARY_HASH_MISMATCH")
    if intent.get("EXPECTED_OUTPUT_REL") != expected_output_rel and str(
        intent.get("EXPECTED_OUTPUT_PATH")
    ) != str(out_path):
        _raise_idempotency_mismatch("IDEMPOTENCY_OUTPUT_PATH_MISMATCH")

    stored_dep_raw = intent.get("DEPENDENCY_RAW_HASHES") or {}
    stored_dep_can = intent.get("DEPENDENCY_CANONICAL_HASHES") or {}
    for dep_id, hashes in dep_hashes.items():
        if stored_dep_raw.get(dep_id) != hashes["RAW_SHA256"]:
            _raise_idempotency_mismatch("IDEMPOTENCY_DEPENDENCY_HASH_MISMATCH", f"raw:{dep_id}")
        if stored_dep_can.get(dep_id) != hashes["CANONICAL_SHA256"]:
            _raise_idempotency_mismatch("IDEMPOTENCY_DEPENDENCY_HASH_MISMATCH", f"canonical:{dep_id}")
    if set(stored_dep_raw.keys()) != set(dep_hashes.keys()):
        _raise_idempotency_mismatch("IDEMPOTENCY_DEPENDENCY_HASH_MISMATCH", "dep_ids")

    in_path = Path(intent["INPUT_PACKET_PATH"])
    if not in_path.exists():
        _raise_idempotency_mismatch("IDEMPOTENCY_INPUT_RAW_HASH_MISMATCH", "input_deleted")
    live_hashes = packets.packet_hashes(in_path)
    if live_hashes["RAW_SHA256"] != intent.get("INPUT_PACKET_RAW_SHA256"):
        _raise_idempotency_mismatch("IDEMPOTENCY_INPUT_RAW_HASH_MISMATCH")
    if live_hashes["CANONICAL_SHA256"] != intent.get("INPUT_PACKET_CANONICAL_SHA256"):
        _raise_idempotency_mismatch("IDEMPOTENCY_INPUT_CANONICAL_HASH_MISMATCH")

    if request_fp != intent.get("REQUEST_FINGERPRINT_SHA256"):
        # Payload / activation / mode divergence not caught above
        _raise_idempotency_mismatch("IDEMPOTENCY_PREPARE_FINGERPRINT_MISMATCH")

    prepare_fp = compute_prepare_fingerprint(
        request_fingerprint=request_fp,
        worker_execution_id=str(active_wex),
        input_raw=live_hashes["RAW_SHA256"],
        input_canonical=live_hashes["CANONICAL_SHA256"],
    )
    if prepare_fp != intent.get("PREPARE_FINGERPRINT_SHA256"):
        _raise_idempotency_mismatch("IDEMPOTENCY_PREPARE_FINGERPRINT_MISMATCH")

    return {
        "STATUS": "EXISTING_DISPATCH_INTENT_RETURNED",
        "WORKER_EXECUTION_ID": active_wex,
        "ATTEMPT": attempt,
        "INPUT_PACKET_PATH": intent.get("INPUT_PACKET_PATH"),
        "INPUT_PACKET_RAW_SHA256": intent.get("INPUT_PACKET_RAW_SHA256"),
        "INPUT_PACKET_CANONICAL_SHA256": intent.get("INPUT_PACKET_CANONICAL_SHA256"),
        "BEFORE_SNAPSHOT_PATH": intent.get("BEFORE_SNAPSHOT_PATH"),
        "DISPATCH_INTENT_PATH": str(intent_path),
        "EXPECTED_OUTPUT_PATH": intent.get("EXPECTED_OUTPUT_PATH"),
        "ALLOWED_WRITE_PATHS": intent.get("ALLOWED_WRITE_PATHS") or [],
        "DISPATCH_INTENT_CREATED": False,
        "NEW_WORKER_EXECUTION_CREATED": False,
        "CHECKPOINT_CHANGED": False,
        "OWNER_RECEIPT_CHANGED": False,
        "TASK_DISPATCH_ALLOWED": True,
        "REQUEST_FINGERPRINT_SHA256": request_fp,
        "PREPARE_FINGERPRINT_SHA256": prepare_fp,
        "TASK_ARGS": build_task_prompt(
            worker_id=worker_id,
            worker_execution_id=str(active_wex),
            orchestration_id=orchestration_id,
            case_id=case_id,
            finding_id=finding_id,
            input_packet_path=Path(intent["INPUT_PACKET_PATH"]),
            output_packet_path=Path(intent["EXPECTED_OUTPUT_PATH"]),
            allowed_write_paths=intent.get("ALLOWED_WRITE_PATHS") or [],
            execution_mode=intent.get("EXECUTION_MODE") or "REVIEW_PROOF_ONLY",
            attempt=attempt,
            timeout_seconds=DEFAULT_TIMEOUTS.get(worker_id, 600),
            checkpoint_path=Path(case_root) / "team" / "CHECKPOINT.json",
        ),
    }


def validate_dispatch_intent_before_task(
    *,
    case_root: Path,
    dispatch_intent_path: Path,
) -> Dict[str, Any]:
    """TOCTOU check after prepare_live_hop and before Cursor Task dispatch."""
    case_root = Path(case_root)
    intent_path = Path(dispatch_intent_path)
    intent = json.loads(intent_path.read_text(encoding="utf-8"))
    checkpoint = load_checkpoint(case_root / "team" / "CHECKPOINT.json")
    active_wex = checkpoint.get("ACTIVE_WORKER_EXECUTION_ID")
    if active_wex != intent.get("WORKER_EXECUTION_ID"):
        raise LiveHopError(
            "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED",
            "active_wex_mismatch",
            {"STATUS": "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED", "TASK_DISPATCH_ALLOWED": False},
        )
    if int(checkpoint.get("CHECKPOINT_GENERATION") or -1) != int(
        intent.get("CHECKPOINT_GENERATION") or -2
    ):
        raise LiveHopError(
            "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED",
            "checkpoint_generation",
            {"STATUS": "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED", "TASK_DISPATCH_ALLOWED": False},
        )
    if checkpoint.get("ACTIVE_PREPARE_FINGERPRINT_SHA256") != intent.get("PREPARE_FINGERPRINT_SHA256"):
        raise LiveHopError(
            "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED",
            "prepare_fingerprint",
            {"STATUS": "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED", "TASK_DISPATCH_ALLOWED": False},
        )
    in_path = Path(intent["INPUT_PACKET_PATH"])
    if not in_path.exists():
        raise LiveHopError(
            "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED",
            "input_missing",
            {"STATUS": "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED", "TASK_DISPATCH_ALLOWED": False},
        )
    live = packets.packet_hashes(in_path)
    if live["RAW_SHA256"] != intent.get("INPUT_PACKET_RAW_SHA256"):
        raise LiveHopError(
            "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED",
            "input_raw",
            {"STATUS": "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED", "TASK_DISPATCH_ALLOWED": False},
        )
    if live["CANONICAL_SHA256"] != intent.get("INPUT_PACKET_CANONICAL_SHA256"):
        raise LiveHopError(
            "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED",
            "input_canonical",
            {"STATUS": "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED", "TASK_DISPATCH_ALLOWED": False},
        )
    for dep_id, meta in (intent.get("DEPENDENCY_PACKETS") or {}).items():
        dep_path = Path(meta["path"])
        if not dep_path.exists():
            raise LiveHopError(
                "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED",
                f"dep_missing:{dep_id}",
                {"STATUS": "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED", "TASK_DISPATCH_ALLOWED": False},
            )
        dh = packets.packet_hashes(dep_path)
        if dh["RAW_SHA256"] != meta.get("RAW_SHA256") or dh["CANONICAL_SHA256"] != meta.get(
            "CANONICAL_SHA256"
        ):
            raise LiveHopError(
                "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED",
                f"dep_hash:{dep_id}",
                {"STATUS": "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED", "TASK_DISPATCH_ALLOWED": False},
            )
    return {"STATUS": "PASS", "TASK_DISPATCH_ALLOWED": True, "PREPARE_FINGERPRINT_SHA256": intent.get("PREPARE_FINGERPRINT_SHA256")}


def _intent_path_for(case_root: Path, wex: str) -> Path:
    return Path(case_root) / "team" / "intents" / f"{_wex_slug(wex)}.intent.json"


def _dispatch_mentions_wex(case_root: Path, wex: str) -> bool:
    path = Path(case_root) / "team" / "DISPATCH.jsonl"
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("WORKER_EXECUTION_ID") == wex or rec.get("NEW_WORKER_EXECUTION_ID") == wex:
            return True
        if rec.get("PREVIOUS_WORKER_EXECUTION_ID") == wex:
            return True
    return False


def _trace_mentions_wex(case_root: Path, wex: str) -> bool:
    path = Path(case_root) / "results" / "ROUTE-TRACE.jsonl"
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("WORKER_EXECUTION_ID") == wex or rec.get("PREVIOUS_WORKER_EXECUTION_ID") == wex:
            return True
    return False


def _assert_previous_execution_authoritative(
    *,
    case_root: Path,
    previous_wex: str,
    orchestration_id: str,
    case_id: str,
    finding_id: Optional[str],
    expected_worker_id: Optional[str] = None,
    expected_attempt: Optional[int] = None,
    expected_packet_generation: Optional[int] = None,
    expected_checkpoint_generation: Optional[int] = None,
    expected_input_raw: Optional[str] = None,
    expected_input_canonical: Optional[str] = None,
    require_terminal_eligible: bool = True,
    allow_superseded_marker: bool = False,
    checkpoint: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Verify previous WEX against intent + DISPATCH + (optional) checkpoint binding."""
    intent_path = _intent_path_for(case_root, previous_wex)
    if not intent_path.exists():
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_FOUND",
            previous_wex,
            {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_FOUND", "RETRY_AUTHORIZATION_CREATED": False},
        )
    intent = json.loads(intent_path.read_text(encoding="utf-8"))
    if not _dispatch_mentions_wex(case_root, previous_wex):
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_FOUND",
            "missing_dispatch_history",
            {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_FOUND", "RETRY_AUTHORIZATION_CREATED": False},
        )

    if intent.get("ORCHESTRATION_ID") != orchestration_id:
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "orchestration",
            {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "RETRY_AUTHORIZATION_CREATED": False},
        )
    if intent.get("CASE_ID") != case_id or intent.get("FINDING_ID") != finding_id:
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "case_finding",
            {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "RETRY_AUTHORIZATION_CREATED": False},
        )
    if expected_worker_id is not None and intent.get("WORKER_ID") != expected_worker_id:
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "worker_id",
            {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "RETRY_AUTHORIZATION_CREATED": False},
        )
    if expected_attempt is not None and int(intent.get("ATTEMPT") or -1) != expected_attempt:
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "attempt",
            {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "RETRY_AUTHORIZATION_CREATED": False},
        )
    if expected_packet_generation is not None and int(intent.get("PACKET_GENERATION") or -1) != expected_packet_generation:
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "packet_generation",
            {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "RETRY_AUTHORIZATION_CREATED": False},
        )
    if expected_checkpoint_generation is not None and int(
        intent.get("CHECKPOINT_GENERATION") or -1
    ) != expected_checkpoint_generation:
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "checkpoint_generation",
            {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "RETRY_AUTHORIZATION_CREATED": False},
        )
    if expected_input_raw is not None and intent.get("INPUT_PACKET_RAW_SHA256") != expected_input_raw:
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "input_raw",
            {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "RETRY_AUTHORIZATION_CREATED": False},
        )
    if expected_input_canonical is not None and intent.get(
        "INPUT_PACKET_CANONICAL_SHA256"
    ) != expected_input_canonical:
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "input_canonical",
            {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "RETRY_AUTHORIZATION_CREATED": False},
        )

    status = intent.get("STATUS")
    if status == "RUNNING" or status == "PREPARED" or status == "DISPATCHED" or status == "PENDING":
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_TERMINAL",
            str(status),
            {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_TERMINAL", "RETRY_AUTHORIZATION_CREATED": False},
        )
    if status == "PASS":
        raise LiveHopError(
            "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE",
            "PASS",
            {"STATUS": "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE", "RETRY_AUTHORIZATION_CREATED": False},
        )
    if status == "WAITING_OWNER" or status == "BLOCKED_NON_RETRYABLE":
        raise LiveHopError(
            "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE",
            str(status),
            {"STATUS": "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE", "RETRY_AUTHORIZATION_CREATED": False},
        )
    if require_terminal_eligible and status not in RETRY_ELIGIBLE:
        # SUPERSEDED alone is not retry-eligible without underlying terminal
        if status == "SUPERSEDED" and not allow_superseded_marker:
            raise LiveHopError(
                "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
                "already_superseded",
                {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "RETRY_AUTHORIZATION_CREATED": False},
            )
        if status not in RETRY_ELIGIBLE and status != "SUPERSEDED":
            raise LiveHopError(
                "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE",
                str(status),
                {"STATUS": "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE", "RETRY_AUTHORIZATION_CREATED": False},
            )

    if intent.get("SUPERSEDED_BY_WORKER_EXECUTION_ID") and not allow_superseded_marker:
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "already_superseded",
            {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH", "RETRY_AUTHORIZATION_CREATED": False},
        )

    if checkpoint is not None:
        cp_active = checkpoint.get("ACTIVE_WORKER_EXECUTION_ID")
        if cp_active != previous_wex:
            raise LiveHopError(
                "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
                "checkpoint_active_wex",
                {
                    "STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
                    "RETRY_AUTHORIZATION_CREATED": False,
                    "CHECKPOINT_ACTIVE": cp_active,
                    "CLAIMED_PREVIOUS": previous_wex,
                },
            )
        cp_status = checkpoint.get("ACTIVE_STATUS")
        if require_terminal_eligible and cp_status not in RETRY_ELIGIBLE:
            if cp_status == "RUNNING":
                raise LiveHopError(
                    "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_TERMINAL",
                    "RUNNING",
                    {"STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_TERMINAL", "RETRY_AUTHORIZATION_CREATED": False},
                )
            if cp_status == "PASS":
                raise LiveHopError(
                    "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE",
                    "PASS",
                    {"STATUS": "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE", "RETRY_AUTHORIZATION_CREATED": False},
                )
            raise LiveHopError(
                "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE",
                str(cp_status),
                {"STATUS": "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE", "RETRY_AUTHORIZATION_CREATED": False},
            )

    return intent


def authorize_retry_or_resume(
    *,
    case_root: Path,
    reason: str,
    orchestration_id: str,
    case_id: str,
    finding_id: Optional[str] = None,
    previous_worker_execution_id: Optional[str] = None,
    expected_worker_id: Optional[str] = None,
    expected_attempt: Optional[int] = None,
    expected_packet_generation: Optional[int] = None,
    expected_checkpoint_generation: Optional[int] = None,
    expected_input_raw_sha256: Optional[str] = None,
    expected_input_canonical_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """Explicit one-time retry authority after eligible terminal previous execution.

    Ordinary prepare_live_hop must NOT create retry authority.
    Previous WEX must exist in DISPATCH_INTENT + DISPATCH.jsonl and match checkpoint.
    """
    case_root = Path(case_root)
    checkpoint_path = case_root / "team" / "CHECKPOINT.json"
    checkpoint = load_checkpoint(checkpoint_path)
    status = checkpoint.get("ACTIVE_STATUS")
    if status not in RETRY_ELIGIBLE:
        if status == "RUNNING":
            raise LiveHopError(
                "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_TERMINAL",
                "RUNNING",
                {
                    "STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_TERMINAL",
                    "RETRY_AUTHORIZATION_CREATED": False,
                },
            )
        if status == "PASS":
            raise LiveHopError(
                "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE",
                "PASS",
                {"STATUS": "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE", "RETRY_AUTHORIZATION_CREATED": False},
            )
        if status == "READY_FOR_RETRY" and checkpoint.get("RETRY_AUTHORIZED"):
            raise LiveHopError(
                "BLOCKED_RETRY_AUTHORIZATION_DUPLICATE",
                "already_authorized",
                {
                    "STATUS": "BLOCKED_RETRY_AUTHORIZATION_DUPLICATE",
                    "RETRY_AUTHORIZATION_CREATED": False,
                },
            )
        raise LiveHopError(
            "BLOCKED_RETRY_NOT_APPLICABLE",
            f"active_status={status}",
            {"STATUS": "BLOCKED_RETRY_NOT_APPLICABLE", "RETRY_AUTHORIZATION_CREATED": False},
        )

    claimed_prev = previous_worker_execution_id or checkpoint.get("ACTIVE_WORKER_EXECUTION_ID")
    if not claimed_prev:
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_FOUND",
            "empty",
            {
                "STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_FOUND",
                "RETRY_AUTHORIZATION_CREATED": False,
                "CHECKPOINT_CHANGED": False,
            },
        )

    if (
        previous_worker_execution_id is not None
        and checkpoint.get("ACTIVE_WORKER_EXECUTION_ID")
        and previous_worker_execution_id != checkpoint.get("ACTIVE_WORKER_EXECUTION_ID")
    ):
        raise LiveHopError(
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "not_current_active",
            {
                "STATUS": "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
                "RETRY_AUTHORIZATION_CREATED": False,
                "CHECKPOINT_CHANGED": False,
            },
        )

    worker_guess = (
        expected_worker_id
        or checkpoint.get("ACTIVE_WORKER_ID")
        or intent_worker_fallback(str(claimed_prev), case_root)
    )
    attempt_guess = (
        expected_attempt
        if expected_attempt is not None
        else int(checkpoint.get("ACTIVE_ATTEMPT") or 1)
    )
    pkg_guess = (
        expected_packet_generation
        if expected_packet_generation is not None
        else int(
            checkpoint.get("ACTIVE_PACKET_GENERATION")
            or checkpoint.get("PACKET_GENERATION")
            or 1
        )
    )
    cpg_guess = (
        expected_checkpoint_generation
        if expected_checkpoint_generation is not None
        else int(
            checkpoint.get("ACTIVE_CHECKPOINT_GENERATION")
            or checkpoint.get("CHECKPOINT_GENERATION")
            or 1
        )
    )

    intent = _assert_previous_execution_authoritative(
        case_root=case_root,
        previous_wex=str(claimed_prev),
        orchestration_id=orchestration_id,
        case_id=case_id,
        finding_id=finding_id,
        expected_worker_id=worker_guess,
        expected_attempt=attempt_guess,
        expected_packet_generation=pkg_guess,
        expected_checkpoint_generation=cpg_guess,
        expected_input_raw=expected_input_raw_sha256,
        expected_input_canonical=expected_input_canonical_sha256,
        require_terminal_eligible=True,
        allow_superseded_marker=False,
        checkpoint=checkpoint,
    )

    worker_id = str(intent.get("WORKER_ID"))
    prev_attempt = int(intent.get("ATTEMPT") or 1)
    prev_pkg = int(intent.get("PACKET_GENERATION") or 1)
    prev_cpg = int(intent.get("CHECKPOINT_GENERATION") or 1)
    prev_raw = intent.get("INPUT_PACKET_RAW_SHA256")
    prev_can = intent.get("INPUT_PACKET_CANONICAL_SHA256")
    terminal_status = intent.get("STATUS")

    retries_dir = case_root / "team" / "retries"
    retries_dir.mkdir(parents=True, exist_ok=True)
    by_prev_path = retries_dir / f"by_prev_{_wex_slug(str(claimed_prev))}.json"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(by_prev_path), flags)
    except FileExistsError:
        raise LiveHopError(
            "BLOCKED_RETRY_AUTHORIZATION_DUPLICATE",
            str(claimed_prev),
            {
                "STATUS": "BLOCKED_RETRY_AUTHORIZATION_DUPLICATE",
                "RETRY_AUTHORIZATION_CREATED": False,
                "CHECKPOINT_CHANGED": False,
            },
        ) from None
    try:
        os.write(fd, b"pending\n")
    finally:
        os.close(fd)

    new_attempt = prev_attempt + 1
    new_pkg = prev_pkg + 1
    new_cpg = int(checkpoint.get("CHECKPOINT_GENERATION") or prev_cpg) + 1
    now = time.time()
    try:
        auth_obj = retry_auth.issue_retry_authorization(
            case_root,
            orchestration_id=orchestration_id,
            case_id=case_id,
            finding_id=finding_id,
            worker_id=worker_id,
            previous_wex=str(claimed_prev),
            previous_terminal_status=str(terminal_status),
            previous_attempt=prev_attempt,
            previous_packet_generation=prev_pkg,
            previous_checkpoint_generation=prev_cpg,
            previous_input_raw=str(prev_raw or ""),
            previous_input_canonical=str(prev_can or ""),
            next_attempt=new_attempt,
            next_packet_generation=new_pkg,
            next_checkpoint_generation=new_cpg,
        )
    except retry_auth.RetryAuthError as exc:
        # release exclusive by_prev lock on issue failure
        try:
            by_prev_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise LiveHopError(exc.code, exc.detail, exc.payload) from exc

    auth_id = str(auth_obj["RETRY_AUTHORIZATION_ID"])
    auth_path = retry_auth.canonical_receipt_path(case_root, auth_id)
    by_prev_path.write_text(
        json.dumps({"RETRY_AUTHORIZATION_ID": auth_id, "PATH": str(auth_path)}, indent=2) + "\n",
        encoding="utf-8",
    )

    trace_path = case_root / "results" / "ROUTE-TRACE.jsonl"
    seq = route_trace.last_sequence(trace_path) + 1
    route_trace.append_event(
        trace_path,
        {
            "SCHEMA_VERSION": "2",
            "EVENT_ID": f"RTE/{case_id}/{seq}",
            "SEQUENCE": seq,
            "CASE_ID": case_id,
            "FINDING_ID": finding_id,
            "ORCHESTRATION_ID": orchestration_id,
            "ACTOR_ROLE": "ORCHESTRATOR",
            "WORKER_ID": worker_id,
            "WORKER_EXECUTION_ID": claimed_prev,
            "CURSOR_AGENT_ID": None,
            "EVENT_TYPE": "RETRY_AUTHORIZED",
            "FROM_STATE": status,
            "TO_STATE": "READY_FOR_RETRY",
            "CHOSEN_ROUTE": None,
            "EXPECTED_NEXT_COMMAND": None,
            "ACTUAL_NEXT_COMMAND": None,
            "NEXT_COMMAND_RECONCILIATION": "NOT_APPLICABLE",
            "EXPECTED_EXECUTION_ROUTE": None,
            "ACTUAL_EXECUTION_ROUTE": None,
            "ROUTE_RECONCILIATION": "NOT_APPLICABLE",
            "STARTED_AT": now,
            "FINISHED_AT": now,
            "DURATION_MS": 0,
            "ATTEMPT": new_attempt,
            "OWNER_GATE_STATUS": None,
            "BLOCKED_REASON": reason,
            "TIMEOUT_REASON": None,
            "INPUT_PACKET_PATH": None,
            "INPUT_PACKET_SHA256": None,
            "OUTPUT_PACKET_PATH": None,
            "OUTPUT_PACKET_SHA256": None,
            "ARTIFACT_PATHS": [auth_obj["CANONICAL_RECEIPT_PATH"]],
            "TERMINAL_STATUS": "RETRY_AUTHORIZED",
            "RETRY_AUTHORIZATION_ID": auth_id,
        },
    )

    intent["STATUS"] = "SUPERSEDED"
    intent["PRIOR_TERMINAL_STATUS"] = terminal_status
    intent["SUPERSEDED_AT"] = now
    intent["SUPERSEDE_REASON"] = reason
    intent["RETRY_AUTHORIZATION_ID"] = auth_id
    intent_path = _intent_path_for(case_root, str(claimed_prev))
    intent_path.write_text(json.dumps(intent, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    checkpoint.update(
        {
            "ACTIVE_STATUS": "READY_FOR_RETRY",
            "RETRY_AUTHORIZED": True,
            "RETRY_AUTHORIZATION_ID": auth_id,
            "PREVIOUS_WORKER_EXECUTION_ID": claimed_prev,
            "ACTIVE_WORKER_EXECUTION_ID": None,
            "ACTIVE_ATTEMPT": new_attempt,
            "ACTIVE_PACKET_GENERATION": new_pkg,
            "PACKET_GENERATION": new_pkg,
            "CHECKPOINT_GENERATION": new_cpg,
            "UPDATED_AT": now,
            "RETRY_REASON": reason,
        }
    )
    save_checkpoint(checkpoint_path, checkpoint)
    return {
        "STATUS": "RETRY_AUTHORIZED",
        "RETRY_AUTHORIZATION_ID": auth_id,
        "RETRY_AUTHORIZATION_PATH": str(auth_path),
        "PREVIOUS_WORKER_EXECUTION_ID": claimed_prev,
        "PREVIOUS_TERMINAL_STATUS": terminal_status,
        "NEXT_ATTEMPT": new_attempt,
        "PACKET_GENERATION": new_pkg,
        "CHECKPOINT_GENERATION": new_cpg,
        "ACTIVE_STATUS": "READY_FOR_RETRY",
        "RETRY_AUTHORIZATION_CREATED": True,
        "CHECKPOINT_CHANGED": True,
        "NONCE": auth_obj.get("NONCE"),
        "REGISTRY_STATUS": retry_auth.STATUS_ISSUED,
    }


def intent_worker_fallback(wex: str, case_root: Path) -> Optional[str]:
    """Best-effort WORKER_ID from intent when checkpoint lacks ACTIVE_WORKER_ID."""
    path = _intent_path_for(case_root, wex)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get("WORKER_ID")


def mark_fail(case_root: Path, worker_execution_id: str, reason: str = "FAIL") -> None:
    """Mark active execution FAIL (requires authorize_retry_or_resume for next prepare)."""
    checkpoint_path = Path(case_root) / "team" / "CHECKPOINT.json"
    checkpoint = load_checkpoint(checkpoint_path)
    if checkpoint.get("ACTIVE_WORKER_EXECUTION_ID") == worker_execution_id:
        checkpoint["ACTIVE_STATUS"] = "FAIL"
        checkpoint["RETRY_AUTHORIZED"] = False
        checkpoint["FAIL_REASON"] = reason
        checkpoint["UPDATED_AT"] = time.time()
        save_checkpoint(checkpoint_path, checkpoint)
    intent_path = (
        Path(case_root) / "team" / "intents" / f"{_wex_slug(worker_execution_id)}.intent.json"
    )
    if intent_path.exists():
        intent = json.loads(intent_path.read_text(encoding="utf-8"))
        intent["STATUS"] = "FAIL"
        intent["TASK_FINISHED_AT"] = time.time()
        intent_path.write_text(json.dumps(intent, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def mark_task_started(dispatch_intent_path: Path) -> Dict[str, Any]:
    intent = json.loads(Path(dispatch_intent_path).read_text(encoding="utf-8"))
    intent["STATUS"] = "DISPATCHED"
    intent["TASK_STARTED_AT"] = time.time()
    Path(dispatch_intent_path).write_text(
        json.dumps(intent, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return intent


def mark_timeout(case_root: Path, worker_execution_id: str) -> None:
    """Logical timeout — isolates active execution; does not kill OS process tree."""
    checkpoint_path = Path(case_root) / "team" / "CHECKPOINT.json"
    checkpoint = load_checkpoint(checkpoint_path)
    if checkpoint.get("ACTIVE_WORKER_EXECUTION_ID") == worker_execution_id:
        checkpoint["ACTIVE_STATUS"] = "TIMEOUT"
        checkpoint["RETRY_AUTHORIZED"] = False
        checkpoint["UPDATED_AT"] = time.time()
        save_checkpoint(checkpoint_path, checkpoint)
    intent_path = Path(case_root) / "team" / "intents" / f"{_wex_slug(worker_execution_id)}.intent.json"
    if intent_path.exists():
        intent = json.loads(intent_path.read_text(encoding="utf-8"))
        intent["STATUS"] = "TIMEOUT"
        intent["TASK_FINISHED_AT"] = time.time()
        intent_path.write_text(json.dumps(intent, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def finalize_live_hop(
    *,
    case_root: Path,
    dispatch_intent_path: Path,
    actual_cursor_agent_id: Optional[str],
    actual_task_id_if_available: Optional[str] = None,
    output_packet_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Phase 3 — finalize using dispatch intent + checkpoint as authority."""
    case_root = Path(case_root)
    intent_path = Path(dispatch_intent_path)
    intent = json.loads(intent_path.read_text(encoding="utf-8"))
    finalized_at = time.time()
    checkpoint_path = case_root / "team" / "CHECKPOINT.json"
    checkpoint = load_checkpoint(checkpoint_path)

    # Verify input hashes against original file bytes
    in_path = Path(intent["INPUT_PACKET_PATH"])
    current_hashes = packets.packet_hashes(in_path)
    if current_hashes["RAW_SHA256"] != intent["INPUT_PACKET_RAW_SHA256"]:
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            "INPUT_RAW_HASH_MISMATCH",
            checkpoint_advanced=False,
        )
    if current_hashes["CANONICAL_SHA256"] != intent["INPUT_PACKET_CANONICAL_SHA256"]:
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            "INPUT_CANONICAL_HASH_MISMATCH",
            checkpoint_advanced=False,
        )

    out_path = Path(output_packet_path or intent["EXPECTED_OUTPUT_PATH"])
    worker_id = intent["WORKER_ID"]
    wex = intent["WORKER_EXECUTION_ID"]

    # Universal stale / active execution check (BF-V2-004)
    if intent.get("STATUS") not in {"DISPATCHED", "PREPARED", "RUNNING"}:
        # PREPARED without mark_task_started still allowed if host forgot — treat as dispatched
        if intent.get("STATUS") in {"TIMEOUT", "FAILED", "CANCELLED", "FINALIZED", "CONSUMED"}:
            return _reject_finalize(
                case_root,
                intent,
                checkpoint,
                "REJECTED_STALE_OUTPUT",
                detail=f"intent_status={intent.get('STATUS')}",
                checkpoint_advanced=False,
                append_rejection_trace=True,
            )

    if checkpoint.get("ACTIVE_STATUS") != "RUNNING":
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            "REJECTED_STALE_OUTPUT",
            detail=f"active_status={checkpoint.get('ACTIVE_STATUS')}",
            checkpoint_advanced=False,
            append_rejection_trace=True,
        )
    if checkpoint.get("ACTIVE_WORKER_EXECUTION_ID") != wex:
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            "REJECTED_STALE_OUTPUT",
            detail="wex_mismatch",
            checkpoint_advanced=False,
            append_rejection_trace=True,
        )
    if checkpoint.get("ACTIVE_WORKER_ID") != worker_id:
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            "REJECTED_STALE_OUTPUT",
            detail="worker_id_mismatch",
            checkpoint_advanced=False,
            append_rejection_trace=True,
        )
    if checkpoint.get("ACTIVE_ATTEMPT") != intent["ATTEMPT"]:
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            "REJECTED_STALE_OUTPUT",
            detail="attempt_mismatch",
            checkpoint_advanced=False,
            append_rejection_trace=True,
        )
    if checkpoint.get("ACTIVE_PACKET_GENERATION") != intent["PACKET_GENERATION"]:
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            "REJECTED_STALE_OUTPUT",
            detail="packet_generation_mismatch",
            checkpoint_advanced=False,
            append_rejection_trace=True,
        )
    if checkpoint.get("ACTIVE_CHECKPOINT_GENERATION") != intent["CHECKPOINT_GENERATION"]:
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            "REJECTED_STALE_OUTPUT",
            detail="checkpoint_generation_mismatch",
            checkpoint_advanced=False,
            append_rejection_trace=True,
        )

    if not out_path.exists():
        return _reject_finalize(
            case_root, intent, checkpoint, "MISSING_OUTPUT_PACKET", checkpoint_advanced=False
        )

    # Single gate validation
    contract = {
        "WORKER_ID": worker_id,
        "ALLOWED_STATUS_TERMINAL_PAIRS": list(allowed_pairs(worker_id)),
    }
    # Rebuild dependency manifest from input packet
    in_pkt = packets.read_packet(in_path)
    dep_manifest: Optional[Dict[str, Any]] = None
    if in_pkt.get("DEPENDENCY_PACKET_IDS"):
        packets_meta: Dict[str, Any] = {}
        for dep_id, meta in (in_pkt.get("DEPENDENCY_HASHES") or {}).items():
            # paths not in packet — look under team/packets by id if stored
            # For finalize, use hashes only from packet + require file discovery via intent siblings
            if isinstance(meta, dict):
                packets_meta[dep_id] = {
                    "path": str(case_root / "team" / "packets" / f"{dep_id.replace('/', '_')}.json")
                    if not Path(str(meta.get("path", ""))).exists()
                    else meta.get("path"),
                    "RAW_SHA256": meta.get("RAW_SHA256"),
                    "CANONICAL_SHA256": meta.get("CANONICAL_SHA256"),
                }
        # Prefer storing absolute paths in DEPENDENCY_HASHES during prepare — already done
        # Fix paths: during prepare we only store hashes. Re-read from intent if present.
        if intent.get("DEPENDENCY_MANIFEST"):
            dep_manifest = intent["DEPENDENCY_MANIFEST"]
        else:
            # Soft: empty paths with hash-only check via packet DEPENDENCY_HASHES strings
            dep_manifest = {"packets": {}}
            for dep_id in in_pkt.get("DEPENDENCY_PACKET_IDS") or []:
                # Skip file path check if we only have hashes in packet — validate via gate
                # by supplying synthetic path that won't exist → would fail MISSING.
                # Store dep files during prepare into intent instead.
                pass
            if intent.get("DEPENDENCY_PACKETS"):
                dep_manifest = {"packets": intent["DEPENDENCY_PACKETS"]}

    # Always attach dependency packets from intent when prepare stored them
    if intent.get("DEPENDENCY_PACKETS"):
        dep_manifest = {"packets": intent["DEPENDENCY_PACKETS"]}

    val = packets.validate_packet_for_transition(
        out_path,
        expected_context={
            "PACKET_TYPE": "WORKER_OUTPUT",
            "WORKER_ID": worker_id,
            "WORKER_EXECUTION_ID": wex,
            "ORCHESTRATION_ID": intent["ORCHESTRATION_ID"],
            "CASE_ID": intent["CASE_ID"],
            "FINDING_ID": intent["FINDING_ID"],
            "PACKET_GENERATION": intent["PACKET_GENERATION"],
            "CHECKPOINT_GENERATION": intent["CHECKPOINT_GENERATION"],
            "ATTEMPT": intent["ATTEMPT"],
            "ACTIVATION_STATE_HASH": activation.activation_state_hash(),
            "EXECUTION_MODE": intent["EXECUTION_MODE"],
            "ENFORCE_ACTIVE_WEX": True,
            "REQUIRE_DEPENDENCY_MANIFEST": bool(in_pkt.get("DEPENDENCY_PACKET_IDS")),
        },
        worker_contract=contract,
        dependency_manifest=dep_manifest if (in_pkt.get("DEPENDENCY_PACKET_IDS") or None) else (
            {"packets": {}} if not in_pkt.get("DEPENDENCY_PACKET_IDS") else dep_manifest
        ),
        active_checkpoint=checkpoint,
    )
    if val.get("RESULT") != "PASS":
        code = val.get("FAILURE_CODE") or val.get("CODE") or "BLOCKED_INVALID_PACKET"
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            code,
            detail=val.get("DETAIL", ""),
            checkpoint_advanced=False,
            validation=val,
        )

    out_pkt = val["PACKET"]
    # Cross-check output identity vs active (already partly in gate)
    if out_pkt["WORKER_EXECUTION_ID"] != checkpoint["ACTIVE_WORKER_EXECUTION_ID"]:
        return _reject_finalize(
            case_root, intent, checkpoint, "REJECTED_STALE_OUTPUT", detail="output_wex"
        )
    if out_pkt["ATTEMPT"] != checkpoint["ACTIVE_ATTEMPT"]:
        return _reject_finalize(
            case_root, intent, checkpoint, "REJECTED_STALE_OUTPUT", detail="output_attempt"
        )
    if out_pkt["PACKET_GENERATION"] != checkpoint["ACTIVE_PACKET_GENERATION"]:
        return _reject_finalize(
            case_root, intent, checkpoint, "REJECTED_STALE_OUTPUT", detail="output_pkg"
        )
    if out_pkt["CHECKPOINT_GENERATION"] != checkpoint["ACTIVE_CHECKPOINT_GENERATION"]:
        return _reject_finalize(
            case_root, intent, checkpoint, "REJECTED_STALE_OUTPUT", detail="output_cpg"
        )

    # Real filesystem after snapshot + diff (never synthetic FsDiff)
    before = load_snapshot(Path(intent["BEFORE_SNAPSHOT_PATH"]))
    after = fs_boundary.FsSnapshot.take(case_root)
    after_path = case_root / "team" / "snapshots" / f"{_wex_slug(wex)}.after.json"
    persist_snapshot(after_path, after)
    diff = fs_boundary.diff_snapshots(before, after)
    wb_result, violations = fs_boundary.evaluate_write_boundary(worker_id, diff)
    fs_boundary.write_boundary_report(
        case_root / "team" / "packets" / f"{_wex_slug(wex)}.wb.json",
        worker_id=worker_id,
        result=wb_result,
        violations=violations,
        fs_diff=diff,
    )
    if wb_result == "VIOLATION":
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            "FAIL_WRITE_BOUNDARY",
            detail=",".join(violations),
            checkpoint_advanced=False,
        )

    out_hashes = packets.packet_hashes(out_path)
    started = intent.get("TASK_STARTED_AT") or intent.get("PREPARED_AT")
    finished = finalized_at
    duration_ms = int((finished - float(started)) * 1000)

    # Trace success event
    trace_path = case_root / "results" / "ROUTE-TRACE.jsonl"
    seq = route_trace.last_sequence(trace_path) + 1
    event = {
        "SCHEMA_VERSION": "2",
        "EVENT_ID": f"RTE/{intent['CASE_ID']}/{seq}",
        "SEQUENCE": seq,
        "CASE_ID": intent["CASE_ID"],
        "FINDING_ID": intent["FINDING_ID"],
        "ORCHESTRATION_ID": intent["ORCHESTRATION_ID"],
        "ACTOR_ROLE": "WORKER",
        "WORKER_ID": worker_id,
        "WORKER_EXECUTION_ID": wex,
        "CURSOR_AGENT_ID": actual_cursor_agent_id,
        "EVENT_TYPE": "WORKER_COMPLETED",
        "FROM_STATE": f"DISPATCHED/{worker_id}",
        "TO_STATE": f"COMPLETED/{worker_id}",
        "CHOSEN_ROUTE": None,
        "EXPECTED_NEXT_COMMAND": None,
        "ACTUAL_NEXT_COMMAND": None,
        "NEXT_COMMAND_RECONCILIATION": "NOT_APPLICABLE",
        "EXPECTED_EXECUTION_ROUTE": None,
        "ACTUAL_EXECUTION_ROUTE": None,
        "ROUTE_RECONCILIATION": "NOT_APPLICABLE",
        "STARTED_AT": started,
        "FINISHED_AT": finished,
        "DURATION_MS": duration_ms,
        "ATTEMPT": intent["ATTEMPT"],
        "OWNER_GATE_STATUS": intent.get("OWNER_RECEIPT_GATE_ID"),
        "BLOCKED_REASON": None,
        "TIMEOUT_REASON": None,
        "INPUT_PACKET_PATH": str(in_path),
        "INPUT_PACKET_RAW_SHA256": intent["INPUT_PACKET_RAW_SHA256"],
        "INPUT_PACKET_CANONICAL_SHA256": intent["INPUT_PACKET_CANONICAL_SHA256"],
        "OUTPUT_PACKET_PATH": str(out_path),
        "OUTPUT_PACKET_RAW_SHA256": out_hashes["RAW_SHA256"],
        "OUTPUT_PACKET_CANONICAL_SHA256": out_hashes["CANONICAL_SHA256"],
        "ARTIFACT_PATHS": diff.all_touched,
        "TERMINAL_STATUS": out_pkt.get("TERMINAL_STATUS"),
        "BEFORE_SNAPSHOT_PATH": intent["BEFORE_SNAPSHOT_PATH"],
        "AFTER_SNAPSHOT_PATH": str(after_path),
    }
    try:
        route_trace.append_event(trace_path, event)
        trace_ok = "PASS"
    except route_trace.TraceIntegrityError as exc:
        return _reject_finalize(
            case_root, intent, checkpoint, exc.code, checkpoint_advanced=False
        )

    # Consume Owner receipt only after accepted executor output (OWNER_GATED / legacy)
    if worker_id in REQUIRES_OWNER_PRODUCTION_GO and intent.get("OWNER_RECEIPT_GATE_ID"):
        try:
            owner_decision_host.consume_reserved_production_go(
                case_root, intent["FINDING_ID"], wex
            )
        except owner_decision_host.OwnerAuthorityError as exc:
            return _reject_finalize(
                case_root,
                intent,
                checkpoint,
                exc.code,
                detail=exc.detail,
                checkpoint_advanced=False,
            )

    # Consume retry authorization (RESERVED → CONSUMED) — registry only
    retry_auth_id = intent.get("RETRY_AUTHORIZATION_ID")
    if retry_auth_id:
        try:
            retry_auth.consume_authorization(
                case_root,
                auth_id=str(retry_auth_id),
                new_worker_execution_id=wex,
                output_packet_raw_sha256=out_hashes["RAW_SHA256"],
                checkpoint_generation=int(intent.get("CHECKPOINT_GENERATION") or 0),
            )
        except retry_auth.RetryAuthError as exc:
            return _reject_finalize(
                case_root,
                intent,
                checkpoint,
                exc.code,
                detail=exc.detail,
                checkpoint_advanced=False,
            )

    # V10: real Cursor agent id required before terminal accept
    if execution_identity.is_placeholder_agent(
        str(actual_cursor_agent_id) if actual_cursor_agent_id is not None else None
    ):
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            "BLOCKED_EXECUTION_IDENTITY_NOT_FINALIZED",
            detail="CURSOR_AGENT_ID pending/placeholder/missing",
            checkpoint_advanced=False,
        )

    # DISPATCH.jsonl — never include OWNER_AUTHORITY_TOKEN
    dispatch_path = case_root / "team" / "DISPATCH.jsonl"
    dispatch_path.parent.mkdir(parents=True, exist_ok=True)
    disp_record_id = execution_identity.dispatch_record_id_for(wex, int(intent["ATTEMPT"]))
    dispatch_record = {
        "DISPATCH_RECORD_ID": disp_record_id,
        "ORCHESTRATION_ID": intent["ORCHESTRATION_ID"],
        "WORKER_EXECUTION_ID": wex,
        "WORKER_ID": worker_id,
        "ATTEMPT": intent["ATTEMPT"],
        "TASK_TOOL": "Cursor Task",
        "SUBAGENT_TYPE": "generalPurpose",
        "CURSOR_AGENT_ID": actual_cursor_agent_id,
        "CURSOR_TASK_ID_OR_EQUIVALENT": actual_task_id_if_available
        or actual_cursor_agent_id,
        "INPUT_PACKET_PATH": str(in_path),
        "INPUT_PACKET_RAW_SHA256": intent["INPUT_PACKET_RAW_SHA256"],
        "INPUT_PACKET_CANONICAL_SHA256": intent["INPUT_PACKET_CANONICAL_SHA256"],
        "OUTPUT_PACKET_PATH": str(out_path),
        "OUTPUT_PACKET_RAW_SHA256": out_hashes["RAW_SHA256"],
        "OUTPUT_PACKET_CANONICAL_SHA256": out_hashes["CANONICAL_SHA256"],
        "PREPARED_AT": intent.get("PREPARED_AT"),
        "TASK_STARTED_AT": intent.get("TASK_STARTED_AT") or started,
        "TASK_FINISHED_AT": finished,
        "FINALIZED_AT": finalized_at,
        "DURATION_MS": duration_ms,
        "STATUS": out_pkt.get("STATUS"),
        "TERMINAL_STATUS": out_pkt.get("TERMINAL_STATUS"),
        "WRITE_BOUNDARY_RESULT": wb_result,
        "TRACE_EVENT_RESULT": trace_ok,
        "LIVE_RUNTIME_AUTHORITY": AUTHORITATIVE_PATH,
    }
    with dispatch_path.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(dispatch_record, ensure_ascii=False, sort_keys=True) + "\n"
        )

    # V10: seal identity + authoritative reconcile before checkpoint advance
    try:
        execution_identity.build_identity_from_finalize(
            case_root=case_root,
            intent=intent,
            actual_cursor_agent_id=str(actual_cursor_agent_id),
            in_path=in_path,
            out_path=out_path,
            in_pkt=in_pkt,
            out_pkt=out_pkt,
            dispatch_record=dispatch_record,
            checkpoint_path=checkpoint_path,
            branch_id=intent.get("BRANCH_ID"),
        )
        id_gate = execution_identity.validate_execution_identity(
            identity_path=execution_identity.identity_path(case_root, wex),
            dispatch_log_path=dispatch_path,
            input_packet_path=in_path,
            output_packet_path=out_path,
            checkpoint_path=checkpoint_path,
            expected_orchestration_id=intent["ORCHESTRATION_ID"],
            expected_case_id=intent["CASE_ID"],
            expected_finding_id=intent["FINDING_ID"],
            expected_worker_execution_id=wex,
            expected_branch_id=intent.get("BRANCH_ID"),
            case_root=case_root,
        )
    except execution_identity.ExecutionIdentityError as exc:
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            "BLOCKED_EXECUTION_IDENTITY_NOT_FINALIZED",
            detail=f"{exc.code}:{exc.detail}",
            checkpoint_advanced=False,
        )

    if not id_gate.VALID:
        try:
            execution_identity.mark_identity_rejected(case_root, wex, id_gate.REASON_CODE)
        except Exception:
            pass
        return _reject_finalize(
            case_root,
            intent,
            checkpoint,
            "BLOCKED_EXECUTION_IDENTITY_NOT_FINALIZED",
            detail=id_gate.REASON_CODE,
            checkpoint_advanced=False,
        )

    execution_identity.mark_identity_validated(case_root, wex)

    # Advance checkpoint; clear active
    completed = list(checkpoint.get("COMPLETED_HOPS") or [])
    completed.append(worker_id)
    new_cpg = int(checkpoint.get("CHECKPOINT_GENERATION") or intent["CHECKPOINT_GENERATION"]) + 1
    checkpoint.update(
        {
            "CHECKPOINT_GENERATION": new_cpg,
            "COMPLETED_HOPS": completed,
            "ACTIVE_STATUS": "IDLE",
            "ACTIVE_WORKER_EXECUTION_ID": None,
            "LAST_ACCEPTED_WEX": wex,
            "UPDATED_AT": finalized_at,
            "LAST_IDENTITY_VALIDATION": "PASS",
            "LAST_IDENTITY_WEX": wex,
        }
    )
    save_checkpoint(checkpoint_path, checkpoint)

    intent["STATUS"] = "FINALIZED"
    intent["TASK_FINISHED_AT"] = finished
    intent["FINALIZED_AT"] = finalized_at
    intent["DURATION_MS"] = duration_ms
    intent["CURSOR_AGENT_ID"] = actual_cursor_agent_id
    intent["EXECUTION_IDENTITY_VALIDATION"] = "PASS"
    intent_path.write_text(json.dumps(intent, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "STATUS": out_pkt.get("STATUS", "PASS"),
        "TERMINAL_STATUS": out_pkt.get("TERMINAL_STATUS", "PASS"),
        "CHECKPOINT_ADVANCED": True,
        "ROUTE_TRACE_SUCCESS_EVENT_APPENDED": True,
        "DEPENDENT_WORKERS_DISPATCHED": False,
        "WORKER_EXECUTION_ID": wex,
        "CURSOR_AGENT_ID": actual_cursor_agent_id,
        "EXECUTION_IDENTITY_VALIDATION": "PASS",
        "INPUT_PACKET_RAW_SHA256": intent["INPUT_PACKET_RAW_SHA256"],
        "INPUT_PACKET_CANONICAL_SHA256": intent["INPUT_PACKET_CANONICAL_SHA256"],
        "OUTPUT_PACKET_RAW_SHA256": out_hashes["RAW_SHA256"],
        "OUTPUT_PACKET_CANONICAL_SHA256": out_hashes["CANONICAL_SHA256"],
        "BEFORE_SNAPSHOT_PATH": intent["BEFORE_SNAPSHOT_PATH"],
        "AFTER_SNAPSHOT_PATH": str(after_path),
        "FILESYSTEM_DIFF": {
            "CREATED": diff.created,
            "MODIFIED": diff.modified,
            "DELETED": diff.deleted,
        },
        "WRITE_BOUNDARY_RESULT": wb_result,
        "DURATION_MS": duration_ms,
        "TRACE_EVENT_ID": event["EVENT_ID"],
        "CHECKPOINT_GENERATION": new_cpg,
    }


def _reject_finalize(
    case_root: Path,
    intent: Dict[str, Any],
    checkpoint: Dict[str, Any],
    code: str,
    *,
    detail: str = "",
    checkpoint_advanced: bool = False,
    append_rejection_trace: bool = False,
    validation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Stale/invalid finalize — never advances checkpoint or success trace."""
    result = {
        "STATUS": code if code.startswith("REJECTED_") else "FAIL",
        "TERMINAL_STATUS": code,
        "DETAIL": detail,
        "CHECKPOINT_ADVANCED": False,
        "ROUTE_TRACE_SUCCESS_EVENT_APPENDED": False,
        "DEPENDENT_WORKERS_DISPATCHED": False,
        "WORKER_EXECUTION_ID": intent.get("WORKER_EXECUTION_ID"),
        "VALIDATION": validation,
    }
    if code == "REJECTED_STALE_OUTPUT":
        result["STATUS"] = "REJECTED_STALE_OUTPUT"
    # Owner receipt must NOT be consumed on stale
    if append_rejection_trace:
        trace_path = Path(case_root) / "results" / "ROUTE-TRACE.jsonl"
        try:
            seq = route_trace.last_sequence(trace_path) + 1
            route_trace.append_event(
                trace_path,
                {
                    "SCHEMA_VERSION": "2",
                    "EVENT_ID": f"RTE/{intent.get('CASE_ID')}/{seq}",
                    "SEQUENCE": seq,
                    "CASE_ID": intent.get("CASE_ID"),
                    "FINDING_ID": intent.get("FINDING_ID"),
                    "ORCHESTRATION_ID": intent.get("ORCHESTRATION_ID"),
                    "ACTOR_ROLE": "ORCHESTRATOR",
                    "WORKER_ID": intent.get("WORKER_ID"),
                    "WORKER_EXECUTION_ID": intent.get("WORKER_EXECUTION_ID"),
                    "CURSOR_AGENT_ID": None,
                    "EVENT_TYPE": "OUTPUT_REJECTED",
                    "FROM_STATE": "ACTIVE",
                    "TO_STATE": "REJECTED_STALE_OUTPUT",
                    "CHOSEN_ROUTE": None,
                    "EXPECTED_NEXT_COMMAND": None,
                    "ACTUAL_NEXT_COMMAND": None,
                    "NEXT_COMMAND_RECONCILIATION": "NOT_APPLICABLE",
                    "EXPECTED_EXECUTION_ROUTE": None,
                    "ACTUAL_EXECUTION_ROUTE": None,
                    "ROUTE_RECONCILIATION": "NOT_APPLICABLE",
                    "STARTED_AT": time.time(),
                    "FINISHED_AT": time.time(),
                    "DURATION_MS": 0,
                    "ATTEMPT": intent.get("ATTEMPT"),
                    "OWNER_GATE_STATUS": None,
                    "BLOCKED_REASON": code,
                    "TIMEOUT_REASON": None,
                    "INPUT_PACKET_PATH": intent.get("INPUT_PACKET_PATH"),
                    "INPUT_PACKET_SHA256": intent.get("INPUT_PACKET_RAW_SHA256"),
                    "OUTPUT_PACKET_PATH": intent.get("EXPECTED_OUTPUT_PATH"),
                    "OUTPUT_PACKET_SHA256": None,
                    "ARTIFACT_PATHS": [],
                    "TERMINAL_STATUS": code,
                },
            )
        except route_trace.TraceIntegrityError:
            pass
    reject_path = (
        Path(case_root)
        / "team"
        / "packets"
        / f"{_wex_slug(intent.get('WORKER_EXECUTION_ID', 'unknown'))}.finalize_reject.json"
    )
    reject_path.parent.mkdir(parents=True, exist_ok=True)
    reject_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result
