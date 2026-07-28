# -*- coding: utf-8 -*-
"""Corrective V4 tests — ICT blockers BF-ICT-001..003.

Minimum: V4-GATE-01..08, V4-AUTH-01..08, V4-LOCK-01..10,
plus ICT-REG-001..003 probes.
Does NOT issue Independent Tester PASS. Does NOT activate runtime.
"""

from __future__ import annotations

import json
import re
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
from runtime.orchestrator import OrchestratorRuntime  # noqa: E402

Result = Tuple[bool, str, str]
HARNESS = Path(".tmp/opsx-bug-team-harness/corrective-v4-unit")


def _case(name: str) -> Path:
    p = HARNESS / name
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    (p / "team" / "packets").mkdir(parents=True, exist_ok=True)
    (p / "results").mkdir(parents=True, exist_ok=True)
    (p / "gates").mkdir(parents=True, exist_ok=True)
    return p


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


def _register(
    case: Path,
    *,
    raw: str = "redraw",
    can: str = "redcan",
    pid: str = "PKT/red",
    frozen: Optional[Dict[str, str]] = None,
    case_id: str = "C-GO",
    finding_id: str = "F-GO",
) -> None:
    token = owner_decision_host.mint_owner_authority_token()
    owner_decision_host.register_production_go(
        case,
        owner_authority_token=token,
        case_id=case_id,
        finding_id=finding_id,
        owner_decision="GO",
        owner_decision_source="OWNER_CHAT_MESSAGE",
        red_packet_id=pid,
        red_raw_sha256=raw,
        red_canonical_sha256=can,
        frozen_test_hashes=frozen or {"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        current_checkpoint_generation=1,
    )


def _reserve(
    case: Path,
    *,
    raw: str = "redraw",
    can: str = "redcan",
    pid: str = "PKT/red",
    frozen: Optional[Dict[str, str]] = None,
    wex: str = "WEX/IMPLEMENTATION_EXECUTOR/a",
    case_id: str = "C-GO",
    finding_id: str = "F-GO",
) -> Tuple[str, Dict[str, Any]]:
    return owner_decision_host.validate_and_reserve_production_go(
        case,
        case_id=case_id,
        finding_id=finding_id,
        red_packet_id=pid,
        red_raw_sha256=raw,
        red_canonical_sha256=can,
        frozen_test_hashes=frozen or {"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        checkpoint_generation=1,
        worker_execution_id=wex,
    )


# --- V4-GATE ---


def gate01() -> Result:
    case = _case("v4gate01")
    _register(case)
    st, rec = _reserve(case)
    ok = st == "PASS" and rec.get("STATUS") == "RESERVED"
    return ok, "valid raw+canonical → RESERVED", "RUNTIME_UNIT"


def gate02() -> Result:
    case = _case("v4gate02")
    _register(case)
    st, _ = _reserve(case, can="WRONG_CANONICAL")
    ok = st == "OWNER_GO_RED_CANONICAL_HASH_MISMATCH"
    return ok, "correct raw / wrong canonical rejected", "RUNTIME_UNIT"


def gate03() -> Result:
    case = _case("v4gate03")
    _register(case)
    st, _ = _reserve(case, raw="WRONG_RAW")
    ok = st == "OWNER_GO_RED_RAW_HASH_MISMATCH"
    return ok, "wrong raw / correct canonical rejected", "RUNTIME_UNIT"


def gate04() -> Result:
    case = _case("v4gate04")
    _register(case)
    st, _ = _reserve(case, frozen={"t1": "WRONG"})
    ok = st == "OWNER_GO_FROZEN_HASH_MISMATCH"
    return ok, "wrong frozen test hash rejected", "RUNTIME_UNIT"


def gate05() -> Result:
    case = _case("v4gate05")
    _register(case)
    st, _ = _reserve(case, pid="PKT/wrong")
    ok = st == "OWNER_GO_RED_PACKET_ID_MISMATCH"
    return ok, "wrong RED_PACKET_ID rejected", "RUNTIME_UNIT"


def gate06() -> Result:
    case = _case("v4gate06")
    _register(case)
    st, _ = _reserve(case, can="bad")
    ok = st.startswith("OWNER_GO_") and st != "BLOCKED_OWNER_PRODUCTION_GO_REQUIRED"
    return ok, "mismatched receipt → MISMATCH not GO_REQUIRED", "RUNTIME_UNIT"


def gate07() -> Result:
    case = _case("v4gate07")
    _register(case)
    st, _ = _reserve(case, can="bad")
    receipt = json.loads(
        owner_decision_host.production_go_path(case, "F-GO").read_text(encoding="utf-8")
    )
    ok = st != "PASS" and receipt.get("STATUS") == "ISSUED" and receipt.get("RESERVED_AT") is None
    return ok, "rejected receipt remains unreserved", "RUNTIME_UNIT"


def gate08() -> Result:
    case = _case("v4gate08")
    _register(case, case_id="C-G8", finding_id="F-G8")
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/g8",
            worker_id="IMPLEMENTATION_EXECUTOR",
            case_id="C-G8",
            finding_id="F-G8",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=1,
            proof_root=case,
            owner_gate_context={
                "red_packet_id": "PKT/red",
                "red_raw_sha256": "redraw",
                "red_canonical_sha256": "WRONG",
                "frozen_test_hashes": {"t1": "h1"},
                "expected_execution_route": "/opsx-fix-bug",
            },
        )
        return False, "should not create intent", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        intents = list((case / "team" / "intents").glob("*.json")) if (case / "team" / "intents").exists() else []
        ok = (
            exc.code == "OWNER_GO_RED_CANONICAL_HASH_MISMATCH"
            and len(intents) == 0
            and exc.payload.get("DISPATCH_INTENT_CREATED") is False
        )
        return ok, "mismatch creates no dispatch intent", "RUNTIME_UNIT"


# --- V4-AUTH ---


def auth01() -> Result:
    case = _case("v4auth01")
    orch = OrchestratorRuntime(
        case_root=case, execution_mode="REVIEW_PROOF_ONLY", proof_root=case
    )
    cp_before = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    res = orch.finalize_after_task()
    cp_after = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    ok = (
        res.get("STATUS") == "BLOCKED_LEGACY_FINALIZE_DISABLED"
        and cp_before == cp_after
        and res.get("CHECKPOINT_ADVANCED") is False
    )
    return ok, "legacy finalize disabled; checkpoint unchanged", "RUNTIME_UNIT"


def auth02() -> Result:
    case = _case("v4auth02")
    orch = OrchestratorRuntime(
        case_root=case, execution_mode="REVIEW_PROOF_ONLY", proof_root=case
    )
    before = route_trace.last_sequence(case / "results" / "ROUTE-TRACE.jsonl")
    orch.finalize_after_task()
    after = route_trace.last_sequence(case / "results" / "ROUTE-TRACE.jsonl")
    events = []
    tp = case / "results" / "ROUTE-TRACE.jsonl"
    if tp.exists():
        events = [json.loads(l) for l in tp.read_text(encoding="utf-8").splitlines() if l.strip()]
    success = [e for e in events if e.get("EVENT_TYPE") == "WORKER_COMPLETED"]
    ok = before == after and len(success) == 0
    return ok, "legacy cannot append success route event", "RUNTIME_UNIT"


def auth03() -> Result:
    case = _case("v4auth03")
    _register(case)
    orch = OrchestratorRuntime(
        case_root=case, execution_mode="REVIEW_PROOF_ONLY", proof_root=case
    )
    before = json.loads(
        owner_decision_host.production_go_path(case, "F-GO").read_text(encoding="utf-8")
    )
    orch.finalize_after_task()
    after = json.loads(
        owner_decision_host.production_go_path(case, "F-GO").read_text(encoding="utf-8")
    )
    ok = before.get("STATUS") == after.get("STATUS") == "ISSUED" and after.get("CONSUMED") is not True
    return ok, "legacy cannot consume Owner receipt", "RUNTIME_UNIT"


def auth04() -> Result:
    case = _case("v4auth04")
    orch = OrchestratorRuntime(
        case_root=case, execution_mode="REVIEW_PROOF_ONLY", proof_root=case
    )
    res = orch.finalize_after_task()
    ok = res.get("DEPENDENT_WORKERS_DISPATCHED") is False
    return ok, "legacy cannot enable dependent worker", "RUNTIME_UNIT"


def auth05() -> Result:
    case = _case("v4auth05")
    pkt = _out_packet(
        worker_id="CLASSIFIER",
        wex="WEX/CLASSIFIER/x",
        orch="ORCH/x",
        case_id="C",
        finding_id="F",
    )
    path = case / "out.json"
    packets.write_packet(path, pkt)
    # weak validate may PASS
    try:
        packets.validate_packet(
            pkt,
            expect_type="WORKER_OUTPUT",
            require_active_for_normal=False,
        )
        weak_pass = True
    except packets.PacketValidationError:
        weak_pass = False
    cp = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    ok = weak_pass and not cp.get("CHECKPOINT_GENERATION") and not cp.get("ACTIVE_STATUS")
    # empty checkpoint unchanged — write one first
    live_task_hop.save_checkpoint(
        case / "team" / "CHECKPOINT.json",
        {"CHECKPOINT_GENERATION": 1, "ACTIVE_STATUS": "IDLE"},
    )
    before = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    packets.validate_packet(pkt, expect_type="WORKER_OUTPUT", require_active_for_normal=False)
    after = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    ok = weak_pass and before == after
    return ok, "weak validate_packet PASS does not advance state", "RUNTIME_UNIT"


def auth06() -> Result:
    case = _case("v4auth06")
    prep = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/a6",
        worker_id="CLASSIFIER",
        case_id="C-A6",
        finding_id="F-A6",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    live_task_hop.mark_task_started(Path(prep["DISPATCH_INTENT_PATH"]))
    out = Path(prep["EXPECTED_OUTPUT_PATH"])
    packets.write_packet(
        out,
        _out_packet(
            worker_id="CLASSIFIER",
            wex=prep["WORKER_EXECUTION_ID"],
            orch="ORCH/a6",
            case_id="C-A6",
            finding_id="F-A6",
        ),
    )
    time.sleep(0.02)
    res = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-a6",
        output_packet_path=out,
    )
    ok = res.get("CHECKPOINT_ADVANCED") is True and res.get("STATUS") == "PASS"
    return ok, "finalize_live_hop advances exactly once", "RUNTIME_UNIT"


def auth07() -> Result:
    case = _case("v4auth07")
    prep = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/a7",
        worker_id="CLASSIFIER",
        case_id="C-A7",
        finding_id="F-A7",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    live_task_hop.mark_task_started(Path(prep["DISPATCH_INTENT_PATH"]))
    out = Path(prep["EXPECTED_OUTPUT_PATH"])
    packets.write_packet(
        out,
        _out_packet(
            worker_id="CLASSIFIER",
            wex=prep["WORKER_EXECUTION_ID"],
            orch="ORCH/a7",
            case_id="C-A7",
            finding_id="F-A7",
        ),
    )
    r1 = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-a7",
        output_packet_path=out,
    )
    r2 = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-a7b",
        output_packet_path=out,
    )
    ok = r1.get("CHECKPOINT_ADVANCED") is True and r2.get("STATUS") == "REJECTED_STALE_OUTPUT"
    return ok, "duplicate live finalize rejected", "RUNTIME_UNIT"


def auth08() -> Result:
    rt = Path(".cursor/pipeline/bug-team/runtime")
    live_txt = (rt / "live_task_hop.py").read_text(encoding="utf-8")
    orch = (rt / "orchestrator.py").read_text(encoding="utf-8")
    has_finalize = "def finalize_live_hop(" in live_txt
    legacy_disabled = "BLOCKED_LEGACY_FINALIZE_DISABLED" in orch
    # Thin wrapper OK if it delegates; no second implementation body
    orch_delegates = (
        "def finalize_live_hop(self" in orch
        and "live_task_hop.finalize_live_hop(" in orch
    )
    others = []
    for p in rt.glob("*.py"):
        if p.name in {"live_task_hop.py", "orchestrator.py"}:
            continue
        if re.search(r"def finalize_live_hop\s*\(", p.read_text(encoding="utf-8")):
            others.append(p.name)
    fat_idx = orch.find("def finalize_after_task")
    fat = orch[fat_idx : fat_idx + 1500] if fat_idx >= 0 else ""
    ok = (
        has_finalize
        and legacy_disabled
        and orch_delegates
        and len(others) == 0
        and "validate_packet(" not in fat
        and 'CHECKPOINT_ADVANCED": True' not in fat
    )
    return ok, "exactly one live success authority (static)", "CONTRACT_STATIC"


# --- V4-LOCK ---


def lock01() -> Result:
    case = _case("v4lock01")
    live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l1",
        worker_id="CLASSIFIER",
        case_id="C-L1",
        finding_id="F-L1",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/l1",
            worker_id="RED_TEST_WORKER",
            case_id="C-L1",
            finding_id="F-L1",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=1,
            proof_root=case,
        )
        return False, "should block", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = exc.code == "BLOCKED_ACTIVE_EXECUTION_RUNNING"
        return ok, "different worker while ACTIVE RUNNING blocked", "RUNTIME_UNIT"


def lock02() -> Result:
    case = _case("v4lock02")
    live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l2",
        worker_id="CLASSIFIER",
        case_id="C-L2",
        finding_id="F-L2",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/l2",
            worker_id="CLASSIFIER",
            case_id="C-L2",
            finding_id="F-L2",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=1,
            attempt=2,
            proof_root=case,
        )
        return False, "should block", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_ACTIVE_EXECUTION_RUNNING",
            "same worker new WEX while RUNNING blocked",
            "RUNTIME_UNIT",
        )


def lock03() -> Result:
    case = _case("v4lock03")
    prep1 = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l3",
        worker_id="CLASSIFIER",
        case_id="C-L3",
        finding_id="F-L3",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        attempt=1,
        proof_root=case,
    )
    cp_before = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    prep2 = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l3",
        worker_id="CLASSIFIER",
        case_id="C-L3",
        finding_id="F-L3",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        attempt=1,
        proof_root=case,
    )
    cp_after = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    ok = (
        prep2.get("STATUS") == "EXISTING_DISPATCH_INTENT_RETURNED"
        and prep2.get("WORKER_EXECUTION_ID") == prep1["WORKER_EXECUTION_ID"]
        and prep2.get("NEW_WORKER_EXECUTION_CREATED") is False
        and cp_before == cp_after
    )
    return ok, "exact idempotent replay returns existing intent", "RUNTIME_UNIT"


def lock04() -> Result:
    case = _case("v4lock04")
    live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l4",
        worker_id="CLASSIFIER",
        case_id="C-L4",
        finding_id="F-L4",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/l4",
            worker_id="GREEN_VERIFIER",
            case_id="C-L4",
            finding_id="F-L4",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,  # same cpg must NOT permit supersede
            packet_generation=2,
            proof_root=case,
        )
        return False, "should block", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_ACTIVE_EXECUTION_RUNNING",
            "matching checkpoint_generation does not permit supersede",
            "RUNTIME_UNIT",
        )


def lock05() -> Result:
    case = _case("v4lock05")
    _register(case, case_id="C-L5", finding_id="F-L5")
    live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l5",
        worker_id="CLASSIFIER",
        case_id="C-L5",
        finding_id="F-L5",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/l5",
            worker_id="IMPLEMENTATION_EXECUTOR",
            case_id="C-L5",
            finding_id="F-L5",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=1,
            proof_root=case,
            owner_gate_context={
                "red_packet_id": "PKT/red",
                "red_raw_sha256": "redraw",
                "red_canonical_sha256": "redcan",
                "frozen_test_hashes": {"t1": "h1"},
                "expected_execution_route": "/opsx-fix-bug",
            },
        )
        return False, "should block before reserve", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        receipt = json.loads(
            owner_decision_host.production_go_path(case, "F-L5").read_text(encoding="utf-8")
        )
        ok = (
            exc.code == "BLOCKED_ACTIVE_EXECUTION_RUNNING"
            and receipt.get("STATUS") == "ISSUED"
            and receipt.get("RESERVED_AT") is None
        )
        return ok, "blocked prepare does not reserve Owner receipt", "RUNTIME_UNIT"


def lock06() -> Result:
    case = _case("v4lock06")
    live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l6",
        worker_id="CLASSIFIER",
        case_id="C-L6",
        finding_id="F-L6",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    before = route_trace.last_sequence(case / "results" / "ROUTE-TRACE.jsonl")
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/l6",
            worker_id="MATERIALIZER",
            case_id="C-L6",
            finding_id="F-L6",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=1,
            proof_root=case,
        )
    except live_task_hop.LiveHopError:
        pass
    after = route_trace.last_sequence(case / "results" / "ROUTE-TRACE.jsonl")
    ok = before == after
    return ok, "blocked prepare does not append dispatch-success event", "RUNTIME_UNIT"


def lock07() -> Result:
    case = _case("v4lock07")
    prep1 = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l7",
        worker_id="CLASSIFIER",
        case_id="C-L7",
        finding_id="F-L7",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    live_task_hop.mark_timeout(case, prep1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case,
        reason="timeout-retry",
        orchestration_id="ORCH/l7",
        case_id="C-L7",
        finding_id="F-L7",
    )
    prep2 = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l7",
        worker_id="CLASSIFIER",
        case_id="C-L7",
        finding_id="F-L7",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=auth["CHECKPOINT_GENERATION"],
        packet_generation=auth["PACKET_GENERATION"],
        attempt=auth["NEXT_ATTEMPT"],
        proof_root=case,
    )
    ok = (
        prep2.get("DISPATCH_INTENT_CREATED") is True
        and prep2["WORKER_EXECUTION_ID"] != prep1["WORKER_EXECUTION_ID"]
        and prep2["ATTEMPT"] == 2
    )
    return ok, "explicit TIMEOUT + authorized retry allows new attempt", "RUNTIME_UNIT"


def lock08() -> Result:
    case = _case("v4lock08")
    prep1 = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l8",
        worker_id="CLASSIFIER",
        case_id="C-L8",
        finding_id="F-L8",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    live_task_hop.mark_fail(case, prep1["WORKER_EXECUTION_ID"])
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/l8",
            worker_id="CLASSIFIER",
            case_id="C-L8",
            finding_id="F-L8",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=2,
            attempt=2,
            proof_root=case,
        )
        return False, "should block without authorize", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_RETRY_AUTHORIZATION_REQUIRED",
            "FAIL + unauthorized prepare blocked until retry auth",
            "RUNTIME_UNIT",
        )


def lock09() -> Result:
    case = _case("v4lock09")
    prep1 = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l9",
        worker_id="CLASSIFIER",
        case_id="C-L9",
        finding_id="F-L9",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    live_task_hop.mark_task_started(Path(prep1["DISPATCH_INTENT_PATH"]))
    live_task_hop.mark_timeout(case, prep1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case,
        reason="supersede",
        orchestration_id="ORCH/l9",
        case_id="C-L9",
        finding_id="F-L9",
    )
    prep2 = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l9",
        worker_id="CLASSIFIER",
        case_id="C-L9",
        finding_id="F-L9",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=auth["CHECKPOINT_GENERATION"],
        packet_generation=auth["PACKET_GENERATION"],
        attempt=auth["NEXT_ATTEMPT"],
        proof_root=case,
    )
    live_task_hop.mark_task_started(Path(prep2["DISPATCH_INTENT_PATH"]))
    out1 = Path(prep1["EXPECTED_OUTPUT_PATH"])
    packets.write_packet(
        out1,
        _out_packet(
            worker_id="CLASSIFIER",
            wex=prep1["WORKER_EXECUTION_ID"],
            orch="ORCH/l9",
            case_id="C-L9",
            finding_id="F-L9",
            attempt=1,
        ),
    )
    intent = json.loads(Path(prep1["DISPATCH_INTENT_PATH"]).read_text(encoding="utf-8"))
    intent["STATUS"] = "DISPATCHED"
    Path(prep1["DISPATCH_INTENT_PATH"]).write_text(json.dumps(intent, indent=2) + "\n", encoding="utf-8")
    res = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep1["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-l9",
        output_packet_path=out1,
    )
    ok = res.get("STATUS") == "REJECTED_STALE_OUTPUT"
    return ok, "superseded WEX late output rejected", "RUNTIME_UNIT"


def lock10() -> Result:
    case = _case("v4lock10")
    live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/l10",
        worker_id="CLASSIFIER",
        case_id="C-L10",
        finding_id="F-L10",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/l10",
            worker_id="GREEN_VERIFIER",
            case_id="C-L10",
            finding_id="F-L10",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=1,
            proof_root=case,
        )
        return False, "dependent should block", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_ACTIVE_EXECUTION_RUNNING",
            "dependent worker cannot begin while parent RUNNING",
            "RUNTIME_UNIT",
        )


# --- ICT regression probes ---


def ict_reg_001() -> Result:
    """ICT-REG-001: receipt raw correct / canonical wrong → rejected."""
    case = _case("ictreg001")
    _register(case)
    st, _ = _reserve(case, can="not-the-canonical")
    ok = st == "OWNER_GO_RED_CANONICAL_HASH_MISMATCH"
    return ok, "ICT-REG-001 raw ok / canonical wrong rejected", "RUNTIME_UNIT"


def ict_reg_002() -> Result:
    """ICT-REG-002: legacy finalize_after_task → no state advancement."""
    case = _case("ictreg002")
    orch = OrchestratorRuntime(
        case_root=case, execution_mode="REVIEW_PROOF_ONLY", proof_root=case
    )
    live_task_hop.save_checkpoint(
        case / "team" / "CHECKPOINT.json",
        {"CHECKPOINT_GENERATION": 1, "ACTIVE_STATUS": "IDLE", "COMPLETED_HOPS": []},
    )
    before = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    res = orch.finalize_after_task(
        worker_id="CLASSIFIER",
        wex="WEX/CLASSIFIER/x",
        case_id="C",
        finding_id="F",
        in_path=case / "x",
        in_hash="00",
        out_path=case / "y",
        before=None,
        cursor_agent_id="x",
        started_at=time.time(),
        attempt=1,
        from_state="A",
        to_state="B",
    )
    after = live_task_hop.load_checkpoint(case / "team" / "CHECKPOINT.json")
    ok = (
        res.get("STATUS") == "BLOCKED_LEGACY_FINALIZE_DISABLED"
        and before == after
        and res.get("CHECKPOINT_ADVANCED") is False
    )
    return ok, "ICT-REG-002 legacy finalize no state advancement", "RUNTIME_UNIT"


def ict_reg_003() -> Result:
    """ICT-REG-003: different worker prepare during ACTIVE RUNNING → blocked."""
    case = _case("ictreg003")
    live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/ict3",
        worker_id="CLASSIFIER",
        case_id="C-ICT3",
        finding_id="F-ICT3",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/ict3",
            worker_id="RED_TEST_WORKER",
            case_id="C-ICT3",
            finding_id="F-ICT3",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=1,
            proof_root=case,
        )
        return False, "should block", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        return (
            exc.code == "BLOCKED_ACTIVE_EXECUTION_RUNNING",
            "ICT-REG-003 different-worker prepare blocked while RUNNING",
            "RUNTIME_UNIT",
        )


TESTS: List[Tuple[str, Callable[[], Result]]] = [
    ("V4-GATE-01", gate01),
    ("V4-GATE-02", gate02),
    ("V4-GATE-03", gate03),
    ("V4-GATE-04", gate04),
    ("V4-GATE-05", gate05),
    ("V4-GATE-06", gate06),
    ("V4-GATE-07", gate07),
    ("V4-GATE-08", gate08),
    ("V4-AUTH-01", auth01),
    ("V4-AUTH-02", auth02),
    ("V4-AUTH-03", auth03),
    ("V4-AUTH-04", auth04),
    ("V4-AUTH-05", auth05),
    ("V4-AUTH-06", auth06),
    ("V4-AUTH-07", auth07),
    ("V4-AUTH-08", auth08),
    ("V4-LOCK-01", lock01),
    ("V4-LOCK-02", lock02),
    ("V4-LOCK-03", lock03),
    ("V4-LOCK-04", lock04),
    ("V4-LOCK-05", lock05),
    ("V4-LOCK-06", lock06),
    ("V4-LOCK-07", lock07),
    ("V4-LOCK-08", lock08),
    ("V4-LOCK-09", lock09),
    ("V4-LOCK-10", lock10),
    ("ICT-REG-001", ict_reg_001),
    ("ICT-REG-002", ict_reg_002),
    ("ICT-REG-003", ict_reg_003),
]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
    HARNESS.mkdir(parents=True, exist_ok=True)
    results: Dict[str, Any] = {}
    failed = 0
    for name, fn in TESTS:
        try:
            ok, msg, label = fn()
            results[name] = {"PASS": ok, "MSG": msg, "LABEL": label}
            print(f"{'PASS' if ok else 'FAIL'} {name} [{label}]: {msg}")
            if not ok:
                failed += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            results[name] = {"PASS": False, "MSG": str(exc), "TRACE": traceback.format_exc()}
            print(f"ERROR {name}: {exc}\n{traceback.format_exc()}")
    out = Path(".cursor/pipeline/bug-team/controlled-tests/CORRECTIVE_V4_LAST_RUN.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"SUMMARY failed={failed} total={len(TESTS)}")
    print("INDEPENDENT_TESTER_PASS: NOT_ISSUED")
    print("RUNTIME_ACTIVATED: NO")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
