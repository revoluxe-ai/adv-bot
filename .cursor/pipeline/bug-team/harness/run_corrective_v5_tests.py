# -*- coding: utf-8 -*-
"""Corrective V5 tests — ICT rerun blockers BF-ICT-RERUN-001/002.

Minimum: V5-IDEM-01..13, V5-RETRY-01..18, ICT-RERUN-REG-AP04/AP05,
adversarial A1..A6 (≥33 tests).

Does NOT issue Independent Tester PASS. Does NOT activate runtime.
Does NOT create real .tmp/opsx-bug-cases cases.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import (  # noqa: E402
    activation,
    live_task_hop,
    owner_decision_host,
    packets,
    route_trace,
)

Result = Tuple[bool, str, str]
HARNESS = Path(".tmp/opsx-bug-team-harness/corrective-v5-unit")


def _case(name: str) -> Path:
    p = HARNESS / name
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    (p / "team" / "packets").mkdir(parents=True, exist_ok=True)
    (p / "results").mkdir(parents=True, exist_ok=True)
    (p / "gates").mkdir(parents=True, exist_ok=True)
    return p


def _prep(
    case: Path,
    *,
    orch: str = "ORCH/v5",
    worker: str = "CLASSIFIER",
    case_id: str = "C-V5",
    finding: str = "F-V5",
    payload: Optional[Dict[str, Any]] = None,
    cpg: int = 1,
    pkg: int = 1,
    attempt: int = 1,
    deps: Optional[Dict[str, Path]] = None,
    expected_output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    return live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id=orch,
        worker_id=worker,
        case_id=case_id,
        finding_id=finding,
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=cpg,
        packet_generation=pkg,
        attempt=attempt,
        proof_root=case,
        payload=payload or {"PROOF": True},
        dependency_packets=deps,
        expected_output_path=expected_output_path,
    )


def _dep_packet(case: Path, name: str, payload: Dict[str, Any]) -> Path:
    path = case / "team" / "packets" / f"dep_{name}.json"
    pkt = {
        "SCHEMA_VERSION": "1",
        "PACKET_TYPE": "WORKER_OUTPUT",
        "PACKET_ID": f"PKT/DEP/{name}",
        "PACKET_GENERATION": 1,
        "ORCHESTRATION_ID": "ORCH/v5",
        "WORKER_EXECUTION_ID": f"WEX/DEP/{name}",
        "WORKER_ID": "CLASSIFIER",
        "CASE_ID": "C-V5",
        "FINDING_ID": "F-V5",
        "PARENT_PACKET_ID": None,
        "DEPENDENCY_PACKET_IDS": [],
        "DEPENDENCY_HASHES": {},
        "CHECKPOINT_GENERATION": 1,
        "CREATED_AT": time.time(),
        "EXPIRES_AT": time.time() + 3600,
        "STATUS": "PASS",
        "TERMINAL_STATUS": "PASS",
        "PAYLOAD": payload,
        "ARTIFACTS_WRITTEN": [],
        "EXECUTION_MODE": "REVIEW_PROOF_ONLY",
        "ACTIVATION_STATE_HASH": activation.activation_state_hash(),
        "ATTEMPT": 1,
    }
    packets.write_packet(path, pkt)
    return path


def _out_packet(
    *,
    worker_id: str,
    wex: str,
    orch: str,
    case_id: str,
    finding_id: Optional[str],
    status: str = "PASS",
    terminal: str = "PASS",
    packet_generation: int = 1,
    checkpoint_generation: int = 1,
    attempt: int = 1,
) -> Dict[str, Any]:
    now = time.time()
    return {
        "SCHEMA_VERSION": "1",
        "PACKET_TYPE": "WORKER_OUTPUT",
        "PACKET_ID": f"PKT/{wex}/OUT",
        "PACKET_GENERATION": packet_generation,
        "ORCHESTRATION_ID": orch,
        "WORKER_EXECUTION_ID": wex,
        "WORKER_ID": worker_id,
        "CASE_ID": case_id,
        "FINDING_ID": finding_id,
        "PARENT_PACKET_ID": f"PKT/{wex}/IN",
        "DEPENDENCY_PACKET_IDS": [],
        "DEPENDENCY_HASHES": {},
        "CHECKPOINT_GENERATION": checkpoint_generation,
        "CREATED_AT": now,
        "EXPIRES_AT": now + 3600,
        "STATUS": status,
        "TERMINAL_STATUS": terminal,
        "PAYLOAD": {"PROOF": True},
        "ARTIFACTS_WRITTEN": [],
        "EXECUTION_MODE": "REVIEW_PROOF_ONLY",
        "ACTIVATION_STATE_HASH": activation.activation_state_hash(),
        "ATTEMPT": attempt,
    }


# --- V5-IDEM ---


def idem01() -> Result:
    case = _case("idem01")
    p1 = _prep(case, payload={"PROOF": True, "VARIANT": "A"})
    p2 = _prep(case, payload={"PROOF": True, "VARIANT": "A"})
    ok = (
        p2.get("STATUS") == "EXISTING_DISPATCH_INTENT_RETURNED"
        and p2["WORKER_EXECUTION_ID"] == p1["WORKER_EXECUTION_ID"]
        and p2.get("NEW_WORKER_EXECUTION_CREATED") is False
        and p2.get("CHECKPOINT_CHANGED") is False
    )
    return ok, "exact replay returns existing intent", "RUNTIME_UNIT"


def idem02() -> Result:
    case = _case("idem02")
    _prep(case, payload={"PROOF": True, "VARIANT": "A"})
    try:
        _prep(case, payload={"PROOF": True, "VARIANT": "B_CHANGED_BYTES"})
        return False, "should reject changed raw/payload", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = exc.code == "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH"
        return ok, "same keys + changed bytes rejected", "RUNTIME_UNIT"


def idem03() -> Result:
    case = _case("idem03")
    _prep(case, payload={"PROOF": True, "SEM": 1})
    try:
        _prep(case, payload={"PROOF": True, "SEM": 2})
        return False, "should reject semantic change", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH",
            "semantically changed canonical payload rejected",
            "RUNTIME_UNIT",
        )


def idem04() -> Result:
    case = _case("idem04")
    p1 = _prep(case, payload={"PROOF": True, "X": 1})
    in_path = Path(p1["INPUT_PACKET_PATH"])
    raw = in_path.read_text(encoding="utf-8")
    # Change raw bytes without changing JSON semantic value (trailing whitespace)
    in_path.write_text(raw.rstrip() + "\n\n", encoding="utf-8")
    try:
        _prep(case, payload={"PROOF": True, "X": 1})
        return False, "should reject raw-only change", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = (
            exc.code == "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH"
            and exc.payload.get("FAILURE_CODE") == "IDEMPOTENCY_INPUT_RAW_HASH_MISMATCH"
        )
        return ok, "same canonical data but changed raw bytes rejected", "RUNTIME_UNIT"


def idem05() -> Result:
    case = _case("idem05")
    dep = _dep_packet(case, "d5", {"V": 1})
    _prep(case, deps={"DEP1": dep}, payload={"PROOF": True})
    # Replace dependency bytes at same path
    _dep_packet(case, "d5", {"V": 2})
    try:
        _prep(case, deps={"DEP1": dep}, payload={"PROOF": True})
        return False, "should reject dep raw change", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = (
            exc.code == "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH"
            and "DEPENDENCY" in str(exc.payload.get("FAILURE_CODE") or exc.detail)
        )
        return ok, "dependency raw hash change rejected", "RUNTIME_UNIT"


def idem06() -> Result:
    case = _case("idem06")
    dep = _dep_packet(case, "d6", {"K": "a"})
    _prep(case, deps={"DEP1": dep}, payload={"PROOF": True})
    # Force canonical change via different key ordering / value
    _dep_packet(case, "d6", {"K": "b"})
    try:
        _prep(case, deps={"DEP1": dep}, payload={"PROOF": True})
        return False, "should reject dep canonical change", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH",
            "dependency canonical hash change rejected",
            "RUNTIME_UNIT",
        )


def idem07() -> Result:
    case = _case("idem07")
    p1 = _prep(case)
    intent_path = Path(p1["DISPATCH_INTENT_PATH"])
    intent = json.loads(intent_path.read_text(encoding="utf-8"))
    intent["WORKER_CONTRACT_HASH"] = "deadbeef" * 8
    intent_path.write_text(json.dumps(intent, indent=2) + "\n", encoding="utf-8")
    try:
        _prep(case)
        return False, "should reject contract hash change", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = (
            exc.code == "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH"
            and exc.payload.get("FAILURE_CODE") == "IDEMPOTENCY_CONTRACT_HASH_MISMATCH"
        )
        return ok, "contract hash change rejected", "RUNTIME_UNIT"


def idem08() -> Result:
    case = _case("idem08")
    p1 = _prep(case)
    intent_path = Path(p1["DISPATCH_INTENT_PATH"])
    intent = json.loads(intent_path.read_text(encoding="utf-8"))
    intent["ALLOWED_WRITE_BOUNDARY_HASH"] = "cafebabe" * 8
    intent_path.write_text(json.dumps(intent, indent=2) + "\n", encoding="utf-8")
    try:
        _prep(case)
        return False, "should reject write-boundary hash change", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = (
            exc.code == "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH"
            and exc.payload.get("FAILURE_CODE") == "IDEMPOTENCY_WRITE_BOUNDARY_HASH_MISMATCH"
        )
        return ok, "write-boundary hash change rejected", "RUNTIME_UNIT"


def idem09() -> Result:
    case = _case("idem09")
    _prep(case)
    other = case / "team" / "packets" / "other.out.json"
    try:
        _prep(case, expected_output_path=other)
        return False, "should reject output path change", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = (
            exc.code == "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH"
            and exc.payload.get("FAILURE_CODE")
            in {
                "IDEMPOTENCY_OUTPUT_PATH_MISMATCH",
                "IDEMPOTENCY_PREPARE_FINGERPRINT_MISMATCH",
            }
        )
        return ok, "expected output path change rejected", "RUNTIME_UNIT"


def idem10() -> Result:
    case = _case("idem10")
    _prep(case, cpg=1, pkg=1)
    try:
        _prep(case, cpg=1, pkg=2)
        return False, "should reject packet generation change", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = (
            exc.code == "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH"
            and exc.payload.get("FAILURE_CODE") == "IDEMPOTENCY_PACKET_GENERATION_MISMATCH"
        )
        return ok, "changed packet generation rejected", "RUNTIME_UNIT"


def idem11() -> Result:
    case = _case("idem11")
    token = owner_decision_host.mint_owner_authority_token()
    owner_decision_host.register_production_go(
        case,
        owner_authority_token=token,
        case_id="C-V5",
        finding_id="F-GO",
        red_packet_id="PKT/red",
        red_raw_sha256="redraw",
        red_canonical_sha256="redcan",
        frozen_test_hashes={"t": "h"},
        expected_execution_route="ROUTE_A",
        owner_decision="GO",
        owner_decision_source="V5-IDEM-11",
        current_checkpoint_generation=1,
    )
    receipt_before = owner_decision_host.production_go_path(case, "F-GO").read_text(encoding="utf-8")
    _prep(case, finding="F-GO", payload={"PROOF": True, "A": 1})
    try:
        _prep(case, finding="F-GO", payload={"PROOF": True, "A": 2})
    except live_task_hop.LiveHopError:
        pass
    receipt_after = owner_decision_host.production_go_path(case, "F-GO").read_text(encoding="utf-8")
    ok = receipt_before == receipt_after
    return ok, "rejected replay does not reserve/mutate Owner receipt", "RUNTIME_UNIT"


def idem12() -> Result:
    case = _case("idem12")
    p1 = _prep(case, payload={"PROOF": True})
    in_path = Path(p1["INPUT_PACKET_PATH"])
    obj = json.loads(in_path.read_text(encoding="utf-8"))
    obj["PAYLOAD"] = {"PROOF": True, "MUTATED_AFTER_PREPARE": True}
    in_path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    try:
        live_task_hop.validate_dispatch_intent_before_task(
            case_root=case, dispatch_intent_path=Path(p1["DISPATCH_INTENT_PATH"])
        )
        return False, "TOCTOU should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = exc.code == "BLOCKED_DISPATCH_INTENT_INPUT_CHANGED"
        return ok, "input changed after prepare before Task rejected", "RUNTIME_UNIT"


def idem13() -> Result:
    case = _case("idem13")
    p1 = _prep(case, payload={"PROOF": True, "Z": 1})
    before_seq = route_trace.last_sequence(case / "results" / "ROUTE-TRACE.jsonl")
    dispatch_before = (case / "team" / "DISPATCH.jsonl").read_text(encoding="utf-8")
    p2 = _prep(case, payload={"PROOF": True, "Z": 1})
    after_seq = route_trace.last_sequence(case / "results" / "ROUTE-TRACE.jsonl")
    dispatch_after = (case / "team" / "DISPATCH.jsonl").read_text(encoding="utf-8")
    ok = (
        p2.get("STATUS") == "EXISTING_DISPATCH_INTENT_RETURNED"
        and p2["WORKER_EXECUTION_ID"] == p1["WORKER_EXECUTION_ID"]
        and before_seq == after_seq
        and dispatch_before == dispatch_after
    )
    return ok, "exact replay creates no route event or new WEX", "RUNTIME_UNIT"


# --- V5-RETRY ---


def retry01() -> Result:
    case = _case("retry01")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case, reason="timeout", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
    )
    ok = auth.get("STATUS") == "RETRY_AUTHORIZED" and auth.get("RETRY_AUTHORIZATION_CREATED") is True
    return ok, "real TIMEOUT WEX permits retry authorization", "RUNTIME_UNIT"


def retry02() -> Result:
    case = _case("retry02")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    cp = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    cp["ACTIVE_WORKER_EXECUTION_ID"] = "WEX/CLASSIFIER/FORGED_UNKNOWN"
    live_task_hop.save_checkpoint(case / "team" / "CHECKPOINT.json", cp)
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case, reason="forge", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
        )
        return False, "forged WEX should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_FOUND",
            "forged unknown WEX rejected",
            "RUNTIME_UNIT",
        )


def retry03() -> Result:
    case = _case("retry03")
    p1 = _prep(case, case_id="C-A", finding="F-A")
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case,
            reason="cross-case",
            orchestration_id="ORCH/v5",
            case_id="C-OTHER",
            finding_id="F-A",
            previous_worker_execution_id=p1["WORKER_EXECUTION_ID"],
        )
        return False, "cross-case should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "WEX from another case rejected",
            "RUNTIME_UNIT",
        )


def retry04() -> Result:
    case = _case("retry04")
    p1 = _prep(case, finding="F-A")
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case,
            reason="cross-finding",
            orchestration_id="ORCH/v5",
            case_id="C-V5",
            finding_id="F-OTHER",
            previous_worker_execution_id=p1["WORKER_EXECUTION_ID"],
        )
        return False, "cross-finding should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "WEX from another finding rejected",
            "RUNTIME_UNIT",
        )


def retry05() -> Result:
    case = _case("retry05")
    p1 = _prep(case, orch="ORCH/A")
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case,
            reason="cross-orch",
            orchestration_id="ORCH/B",
            case_id="C-V5",
            finding_id="F-V5",
            previous_worker_execution_id=p1["WORKER_EXECUTION_ID"],
        )
        return False, "cross-orch should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "WEX from another orchestration rejected",
            "RUNTIME_UNIT",
        )


def retry06() -> Result:
    case = _case("retry06")
    _prep(case)
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case, reason="running", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
        )
        return False, "RUNNING should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_TERMINAL",
            "RUNNING WEX rejected",
            "RUNTIME_UNIT",
        )


def retry07() -> Result:
    case = _case("retry07")
    p1 = _prep(case)
    # Mark PASS terminal (not retry-eligible)
    cp = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    cp["ACTIVE_STATUS"] = "PASS"
    live_task_hop.save_checkpoint(case / "team" / "CHECKPOINT.json", cp)
    intent = json.loads(Path(p1["DISPATCH_INTENT_PATH"]).read_text(encoding="utf-8"))
    intent["STATUS"] = "PASS"
    Path(p1["DISPATCH_INTENT_PATH"]).write_text(json.dumps(intent, indent=2) + "\n", encoding="utf-8")
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case, reason="pass", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
        )
        return False, "PASS should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_STATUS_NOT_ELIGIBLE",
            "PASS WEX rejected",
            "RUNTIME_UNIT",
        )


def retry08() -> Result:
    case = _case("retry08")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case,
            reason="wrong-worker",
            orchestration_id="ORCH/v5",
            case_id="C-V5",
            finding_id="F-V5",
            expected_worker_id="RED_TEST_WORKER",
        )
        return False, "wrong worker should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "wrong worker ID rejected",
            "RUNTIME_UNIT",
        )


def retry09() -> Result:
    case = _case("retry09")
    p1 = _prep(case, attempt=1)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case,
            reason="wrong-attempt",
            orchestration_id="ORCH/v5",
            case_id="C-V5",
            finding_id="F-V5",
            expected_attempt=99,
        )
        return False, "wrong attempt should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "wrong previous attempt rejected",
            "RUNTIME_UNIT",
        )


def retry10() -> Result:
    case = _case("retry10")
    p1 = _prep(case, pkg=1)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case,
            reason="wrong-pkg",
            orchestration_id="ORCH/v5",
            case_id="C-V5",
            finding_id="F-V5",
            expected_packet_generation=99,
        )
        return False, "wrong pkg should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "wrong packet generation rejected",
            "RUNTIME_UNIT",
        )


def retry11() -> Result:
    case = _case("retry11")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case,
            reason="wrong-hash",
            orchestration_id="ORCH/v5",
            case_id="C-V5",
            finding_id="F-V5",
            expected_input_raw_sha256="0" * 64,
        )
        return False, "wrong input hash should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "wrong input hash rejected",
            "RUNTIME_UNIT",
        )


def retry12() -> Result:
    case = _case("retry12")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case, reason="r1", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
    )
    p2 = _prep(
        case,
        cpg=auth["CHECKPOINT_GENERATION"],
        pkg=auth["PACKET_GENERATION"],
        attempt=auth["NEXT_ATTEMPT"],
    )
    live_task_hop.mark_timeout(case, p2["WORKER_EXECUTION_ID"])
    # Branch: try authorize from superseded WEX-1 while WEX-2 is current
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case,
            reason="branch",
            orchestration_id="ORCH/v5",
            case_id="C-V5",
            finding_id="F-V5",
            previous_worker_execution_id=p1["WORKER_EXECUTION_ID"],
        )
        return False, "superseded WEX-1 should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = exc.code in {
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH",
            "BLOCKED_RETRY_AUTHORIZATION_DUPLICATE",
        }
        return ok, "already superseded WEX rejected", "RUNTIME_UNIT"


def retry13() -> Result:
    case = _case("retry13")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    live_task_hop.authorize_retry_or_resume(
        case_root=case, reason="first", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
    )
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case, reason="dup", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
        )
        return False, "duplicate auth should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_DUPLICATE",
            "duplicate authorization rejected",
            "RUNTIME_UNIT",
        )


def retry14() -> Result:
    case = _case("retry14")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case, reason="once", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
    )
    p2 = _prep(
        case,
        cpg=auth["CHECKPOINT_GENERATION"],
        pkg=auth["PACKET_GENERATION"],
        attempt=auth["NEXT_ATTEMPT"],
    )
    from runtime import retry_auth as _ra

    status = _ra.registry_status(case, auth["RETRY_AUTHORIZATION_ID"])
    last = _ra.latest_status_for(case, auth["RETRY_AUTHORIZATION_ID"])[1]
    ok = (
        status == _ra.STATUS_RESERVED
        and last is not None
        and last.get("NEW_WORKER_EXECUTION_ID") == p2["WORKER_EXECUTION_ID"]
    )
    return ok, "valid authorization reserved once (registry)", "RUNTIME_UNIT"


def retry15() -> Result:
    case = _case("retry15")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case, reason="replay", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
    )
    _prep(
        case,
        cpg=auth["CHECKPOINT_GENERATION"],
        pkg=auth["PACKET_GENERATION"],
        attempt=auth["NEXT_ATTEMPT"],
    )
    # Force checkpoint back to READY_FOR_RETRY with same auth id (replay attempt)
    cp = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    cp["ACTIVE_STATUS"] = "READY_FOR_RETRY"
    cp["RETRY_AUTHORIZED"] = True
    cp["RETRY_AUTHORIZATION_ID"] = auth["RETRY_AUTHORIZATION_ID"]
    cp["ACTIVE_WORKER_EXECUTION_ID"] = None
    live_task_hop.save_checkpoint(case / "team" / "CHECKPOINT.json", cp)
    try:
        _prep(
            case,
            cpg=auth["CHECKPOINT_GENERATION"],
            pkg=auth["PACKET_GENERATION"],
            attempt=auth["NEXT_ATTEMPT"],
        )
        return False, "replay should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REPLAY",
            "replay rejected",
            "RUNTIME_UNIT",
        )


def retry16() -> Result:
    case = _case("retry16")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    auth1 = live_task_hop.authorize_retry_or_resume(
        case_root=case, reason="r1", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
    )
    p2 = _prep(
        case,
        cpg=auth1["CHECKPOINT_GENERATION"],
        pkg=auth1["PACKET_GENERATION"],
        attempt=auth1["NEXT_ATTEMPT"],
    )
    live_task_hop.mark_timeout(case, p2["WORKER_EXECUTION_ID"])
    # Cannot branch WEX-3 from WEX-1
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case,
            reason="branch",
            orchestration_id="ORCH/v5",
            case_id="C-V5",
            finding_id="F-V5",
            previous_worker_execution_id=p1["WORKER_EXECUTION_ID"],
        )
        return False, "branch should reject", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = exc.code == "BLOCKED_RETRY_PREVIOUS_EXECUTION_MISMATCH"
        return ok, "WEX-3 cannot branch directly from WEX-1 after WEX-2", "RUNTIME_UNIT"


def retry17() -> Result:
    case = _case("retry17")
    p1 = _prep(case, attempt=1, pkg=1, cpg=1)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case, reason="inc", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
    )
    p2 = _prep(
        case,
        cpg=auth["CHECKPOINT_GENERATION"],
        pkg=auth["PACKET_GENERATION"],
        attempt=auth["NEXT_ATTEMPT"],
    )
    ok = p2["ATTEMPT"] == 2 and auth["PACKET_GENERATION"] == 2 and auth["CHECKPOINT_GENERATION"] == 2
    return ok, "new WEX correctly increments attempt/generation", "RUNTIME_UNIT"


def retry18() -> Result:
    case = _case("retry18")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case, reason="late", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
    )
    p2 = _prep(
        case,
        cpg=auth["CHECKPOINT_GENERATION"],
        pkg=auth["PACKET_GENERATION"],
        attempt=auth["NEXT_ATTEMPT"],
    )
    live_task_hop.mark_task_started(Path(p2["DISPATCH_INTENT_PATH"]))
    out1 = Path(p1["EXPECTED_OUTPUT_PATH"])
    packets.write_packet(
        out1,
        _out_packet(
            worker_id="CLASSIFIER",
            wex=p1["WORKER_EXECUTION_ID"],
            orch="ORCH/v5",
            case_id="C-V5",
            finding_id="F-V5",
            attempt=1,
        ),
    )
    intent = json.loads(Path(p1["DISPATCH_INTENT_PATH"]).read_text(encoding="utf-8"))
    if intent.get("STATUS") == "SUPERSEDED":
        intent["STATUS"] = "DISPATCHED"
        Path(p1["DISPATCH_INTENT_PATH"]).write_text(json.dumps(intent, indent=2) + "\n", encoding="utf-8")
    res = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(p1["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-r18",
        output_packet_path=out1,
    )
    ok = res.get("STATUS") == "REJECTED_STALE_OUTPUT"
    return ok, "late previous-WEX output remains rejected", "RUNTIME_UNIT"


# --- ICT independent regression probes (literal / readable) ---


def ict_rerun_reg_ap04() -> Result:
    """ICT-RERUN-REG-AP04: same identity keys + changed input bytes → mismatch."""
    case = _case("ict_ap04")
    prep1 = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/ap04",
        worker_id="CLASSIFIER",
        case_id="C-AP04",
        finding_id="F-AP04",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
        payload={"PROOF": True, "VARIANT": "A"},
    )
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/ap04",
            worker_id="CLASSIFIER",
            case_id="C-AP04",
            finding_id="F-AP04",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=1,
            proof_root=case,
            payload={"PROOF": True, "VARIANT": "B_CHANGED_BYTES"},
        )
        return False, "AP04 must not idempotent-pass", "ICT_REGRESSION"
    except live_task_hop.LiveHopError as exc:
        ok = exc.code == "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH"
        return ok, "ICT-RERUN-REG-AP04 blocked divergent input", "ICT_REGRESSION"


def ict_rerun_reg_ap05() -> Result:
    """ICT-RERUN-REG-AP05: forged PREVIOUS_WORKER_EXECUTION_ID → NOT_FOUND."""
    case = _case("ict_ap05")
    prep = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/ap05",
        worker_id="CLASSIFIER",
        case_id="C-AP05",
        finding_id="F-AP05",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    live_task_hop.mark_timeout(case, prep["WORKER_EXECUTION_ID"])
    cp = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    cp["ACTIVE_WORKER_EXECUTION_ID"] = "WEX/CLASSIFIER/WRONG_PREV"
    live_task_hop.save_checkpoint(case / "team" / "CHECKPOINT.json", cp)
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case,
            reason="forged-wrong-prev",
            orchestration_id="ORCH/ap05",
            case_id="C-AP05",
            finding_id="F-AP05",
        )
        return False, "AP05 forge must not be accepted", "ICT_REGRESSION"
    except live_task_hop.LiveHopError as exc:
        ok = exc.code == "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_FOUND"
        return ok, "ICT-RERUN-REG-AP05 forged previous WEX rejected", "ICT_REGRESSION"


# --- Adversarial ---


def adv_a1() -> Result:
    case = _case("adv_a1")
    p1 = _prep(case)
    Path(p1["INPUT_PACKET_PATH"]).unlink()
    try:
        _prep(case)
        return False, "deleted input should reject", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH",
            "exact replay after input deleted rejected",
            "ADVERSARIAL",
        )


def adv_a2() -> Result:
    case = _case("adv_a2")
    dep = _dep_packet(case, "a2", {"V": 1})
    _prep(case, deps={"DEP1": dep})
    _dep_packet(case, "a2", {"V": "replaced"})
    try:
        _prep(case, deps={"DEP1": dep})
        return False, "replaced dep should reject", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_IDEMPOTENCY_INPUT_MISMATCH",
            "exact replay after dependency replaced rejected",
            "ADVERSARIAL",
        )


def adv_a3() -> Result:
    case = _case("adv_a3")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case, reason="a3", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
    )
    # Wipe DISPATCH history so previous WEX is no longer authoritative
    (case / "team" / "DISPATCH.jsonl").write_text("", encoding="utf-8")
    try:
        _prep(
            case,
            cpg=auth["CHECKPOINT_GENERATION"],
            pkg=auth["PACKET_GENERATION"],
            attempt=auth["NEXT_ATTEMPT"],
        )
        return False, "missing history should reject prepare", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        ok = exc.code in {
            "BLOCKED_RETRY_PREVIOUS_EXECUTION_NOT_FOUND",
            "BLOCKED_RETRY_AUTHORIZATION_REQUIRED",
        }
        return ok, "retry auth then missing history - prepare rejected", "ADVERSARIAL"


def adv_a4() -> Result:
    case = _case("adv_a4")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    # Simulate concurrent: pre-create exclusive lock file
    retries = case / "team" / "retries"
    retries.mkdir(parents=True, exist_ok=True)
    lock = retries / f"by_prev_{live_task_hop._wex_slug(p1['WORKER_EXECUTION_ID'])}.json"
    lock.write_text('{"RETRY_AUTHORIZATION_ID":"pre"}\n', encoding="utf-8")
    # Restore TIMEOUT status (still)
    try:
        live_task_hop.authorize_retry_or_resume(
            case_root=case, reason="a4", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
        )
        return False, "second concurrent should fail", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_DUPLICATE",
            "two concurrent retry auth - only one succeeds",
            "ADVERSARIAL",
        )


def adv_a5() -> Result:
    case = _case("adv_a5")
    p1 = _prep(case, worker="CLASSIFIER")
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case, reason="a5", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
    )
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/v5",
            worker_id="RED_TEST_WORKER",
            case_id="C-V5",
            finding_id="F-V5",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=auth["CHECKPOINT_GENERATION"],
            packet_generation=auth["PACKET_GENERATION"],
            attempt=auth["NEXT_ATTEMPT"],
            proof_root=case,
        )
        return False, "worker B should reject", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_WORKER_MISMATCH",
            "retry auth for worker A used to prepare worker B rejected",
            "ADVERSARIAL",
        )


def adv_a6() -> Result:
    case = _case("adv_a6")
    p1 = _prep(case)
    live_task_hop.mark_timeout(case, p1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case, reason="a6", orchestration_id="ORCH/v5", case_id="C-V5", finding_id="F-V5"
    )
    # Forge: keep retry auth while another RUNNING WEX is active
    cp = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    cp["ACTIVE_STATUS"] = "RUNNING"
    cp["ACTIVE_WORKER_EXECUTION_ID"] = "WEX/CLASSIFIER/OTHER_RUNNING"
    cp["RETRY_AUTHORIZED"] = True
    cp["RETRY_AUTHORIZATION_ID"] = auth["RETRY_AUTHORIZATION_ID"]
    live_task_hop.save_checkpoint(case / "team" / "CHECKPOINT.json", cp)
    try:
        _prep(
            case,
            cpg=auth["CHECKPOINT_GENERATION"],
            pkg=auth["PACKET_GENERATION"],
            attempt=auth["NEXT_ATTEMPT"],
        )
        return False, "should not prepare while RUNNING", "ADVERSARIAL"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_ACTIVE_EXECUTION_RUNNING",
            "retry auth while ACTIVE RUNNING - no prepare",
            "ADVERSARIAL",
        )


TESTS: List[Tuple[str, Callable[[], Result]]] = [
    ("V5-IDEM-01", idem01),
    ("V5-IDEM-02", idem02),
    ("V5-IDEM-03", idem03),
    ("V5-IDEM-04", idem04),
    ("V5-IDEM-05", idem05),
    ("V5-IDEM-06", idem06),
    ("V5-IDEM-07", idem07),
    ("V5-IDEM-08", idem08),
    ("V5-IDEM-09", idem09),
    ("V5-IDEM-10", idem10),
    ("V5-IDEM-11", idem11),
    ("V5-IDEM-12", idem12),
    ("V5-IDEM-13", idem13),
    ("V5-RETRY-01", retry01),
    ("V5-RETRY-02", retry02),
    ("V5-RETRY-03", retry03),
    ("V5-RETRY-04", retry04),
    ("V5-RETRY-05", retry05),
    ("V5-RETRY-06", retry06),
    ("V5-RETRY-07", retry07),
    ("V5-RETRY-08", retry08),
    ("V5-RETRY-09", retry09),
    ("V5-RETRY-10", retry10),
    ("V5-RETRY-11", retry11),
    ("V5-RETRY-12", retry12),
    ("V5-RETRY-13", retry13),
    ("V5-RETRY-14", retry14),
    ("V5-RETRY-15", retry15),
    ("V5-RETRY-16", retry16),
    ("V5-RETRY-17", retry17),
    ("V5-RETRY-18", retry18),
    ("ICT-RERUN-REG-AP04", ict_rerun_reg_ap04),
    ("ICT-RERUN-REG-AP05", ict_rerun_reg_ap05),
    ("V5-ADV-A1", adv_a1),
    ("V5-ADV-A2", adv_a2),
    ("V5-ADV-A3", adv_a3),
    ("V5-ADV-A4", adv_a4),
    ("V5-ADV-A5", adv_a5),
    ("V5-ADV-A6", adv_a6),
]


def main() -> int:
    print("=== Corrective V5 tests (ICT rerun blockers) ===")
    print(f"activation: {activation.load_activation().get('RUNTIME_STATUS')}")
    passed = failed = 0
    rows: List[Dict[str, Any]] = []
    for name, fn in TESTS:
        try:
            ok, detail, kind = fn()
        except Exception as exc:  # noqa: BLE001
            ok, detail, kind = False, f"EXC {exc}", "ERROR"
            traceback.print_exc()
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] {name}: {detail} ({kind})".encode("ascii", "replace").decode("ascii"))
        rows.append({"id": name, "status": status, "detail": detail, "kind": kind})
    total = passed + failed
    print(f"\nTOTAL={total} PASSED={passed} FAILED={failed}")
    out = Path(".tmp/opsx-bug-team-harness/corrective-v5-unit/RESULTS.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"total": total, "passed": passed, "failed": failed, "rows": rows}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
