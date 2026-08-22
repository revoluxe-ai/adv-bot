# -*- coding: utf-8 -*-
"""Corrective V3 controlled tests (BF-V2-001..004).

V3-VAL-01..08, V3-GATE-01..11, V3-STALE-01..10 + regression checks.
Does NOT issue Independent Tester PASS. Does NOT activate runtime.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import (  # noqa: E402
    activation,
    fs_boundary,
    live_task_hop,
    owner_decision_host,
    owner_go,
    packets,
    route_trace,
)
from runtime.graph_fingerprint import check_attested_inventory  # noqa: E402
from runtime.worker_contracts import allowed_pairs  # noqa: E402

Result = Tuple[bool, str, str]
HARNESS = Path(".tmp/opsx-bug-team-harness/corrective-v3-unit")


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
    deps: Optional[List[str]] = None,
    dep_hashes: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    now = time.time()
    pkt: Dict[str, Any] = {
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
        "DEPENDENCY_PACKET_IDS": deps or [],
        "DEPENDENCY_HASHES": dep_hashes or {},
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
    if extra:
        pkt.update(extra)
    return pkt


def _write_out(path: Path, pkt: Dict[str, Any]) -> Dict[str, str]:
    return packets.write_packet(path, pkt)


def _contract(worker_id: str) -> Dict[str, Any]:
    return {"WORKER_ID": worker_id, "ALLOWED_STATUS_TERMINAL_PAIRS": list(allowed_pairs(worker_id))}


# --- V3-VAL ---


def val01() -> Result:
    case = _case("val01")
    pkt = _out_packet(
        worker_id="CLASSIFIER",
        wex="WEX/CLASSIFIER/a",
        orch="ORCH/a",
        case_id="C",
        finding_id="F",
        status="PASS",
        terminal="NOT_A_REAL_TERMINAL",
    )
    path = case / "out.json"
    _write_out(path, pkt)
    rec = packets.validate_packet_for_transition(
        path,
        expected_context={"PACKET_TYPE": "WORKER_OUTPUT", "WORKER_ID": "CLASSIFIER"},
        worker_contract=_contract("CLASSIFIER"),
        dependency_manifest={"packets": {}},
        active_checkpoint=None,
    )
    ok = rec["RESULT"] == "REJECT" and rec.get("FAILURE_CODE") == "BLOCKED_INVALID_TERMINAL_STATUS"
    return ok, "wrong terminal status rejected", "RUNTIME_UNIT"


def val02() -> Result:
    case = _case("val02")
    pkt = _out_packet(
        worker_id="CLASSIFIER",
        wex="WEX/CLASSIFIER/a",
        orch="ORCH/a",
        case_id="C",
        finding_id="F",
        status="BLOCKED",
        terminal="PASS",  # invalid pair
    )
    path = case / "out.json"
    _write_out(path, pkt)
    rec = packets.validate_packet_for_transition(
        path,
        expected_context={"PACKET_TYPE": "WORKER_OUTPUT"},
        worker_contract=_contract("CLASSIFIER"),
        dependency_manifest={"packets": {}},
        active_checkpoint=None,
    )
    ok = rec["RESULT"] == "REJECT" and rec.get("FAILURE_CODE") == "BLOCKED_INVALID_TERMINAL_STATUS"
    return ok, "invalid status/terminal pair rejected", "RUNTIME_UNIT"


def val03() -> Result:
    case = _case("val03")
    pkt = _out_packet(
        worker_id="CLASSIFIER",
        wex="WEX/CLASSIFIER/a",
        orch="ORCH/a",
        case_id="C",
        finding_id="F",
        deps=["PKT/missing"],
        dep_hashes={"PKT/missing": {"RAW_SHA256": "00", "CANONICAL_SHA256": "00"}},
    )
    path = case / "out.json"
    _write_out(path, pkt)
    rec = packets.validate_packet_for_transition(
        path,
        expected_context={"PACKET_TYPE": "WORKER_OUTPUT", "REQUIRE_DEPENDENCY_MANIFEST": True},
        worker_contract=_contract("CLASSIFIER"),
        dependency_manifest={"packets": {}},
        active_checkpoint=None,
    )
    ok = rec["RESULT"] == "REJECT" and rec.get("FAILURE_CODE") == "MISSING_DEPENDENCY"
    return ok, "missing dependency rejected", "RUNTIME_UNIT"


def val04() -> Result:
    case = _case("val04")
    dep = case / "dep.json"
    dep_pkt = packets.new_input_packet(
        worker_id="MATERIALIZER",
        orchestration_id="ORCH/a",
        worker_execution_id="WEX/MATERIALIZER/d",
        case_id="C",
        finding_id="F",
        checkpoint_generation=1,
        packet_generation=1,
        activation_state_hash=activation.activation_state_hash(),
        execution_mode="REVIEW_PROOF_ONLY",
        payload={},
    )
    h = packets.write_packet(dep, dep_pkt)
    pkt = _out_packet(
        worker_id="CLASSIFIER",
        wex="WEX/CLASSIFIER/a",
        orch="ORCH/a",
        case_id="C",
        finding_id="F",
        deps=[dep_pkt["PACKET_ID"]],
        dep_hashes={
            dep_pkt["PACKET_ID"]: {
                "RAW_SHA256": "0" * 64,
                "CANONICAL_SHA256": h["CANONICAL_SHA256"],
            }
        },
    )
    path = case / "out.json"
    _write_out(path, pkt)
    rec = packets.validate_packet_for_transition(
        path,
        expected_context={"PACKET_TYPE": "WORKER_OUTPUT"},
        worker_contract=_contract("CLASSIFIER"),
        dependency_manifest={
            "packets": {
                dep_pkt["PACKET_ID"]: {
                    "path": str(dep),
                    "RAW_SHA256": h["RAW_SHA256"],
                    "CANONICAL_SHA256": h["CANONICAL_SHA256"],
                }
            }
        },
        active_checkpoint=None,
    )
    ok = rec["RESULT"] == "REJECT" and rec.get("FAILURE_CODE") == "DEPENDENCY_HASH_MISMATCH"
    return ok, "dependency raw hash mismatch rejected", "RUNTIME_UNIT"


def val05() -> Result:
    case = _case("val05")
    dep = case / "dep.json"
    dep_pkt = packets.new_input_packet(
        worker_id="MATERIALIZER",
        orchestration_id="ORCH/a",
        worker_execution_id="WEX/MATERIALIZER/d",
        case_id="C",
        finding_id="F",
        checkpoint_generation=1,
        packet_generation=1,
        activation_state_hash=activation.activation_state_hash(),
        execution_mode="REVIEW_PROOF_ONLY",
        payload={},
    )
    h = packets.write_packet(dep, dep_pkt)
    pkt = _out_packet(
        worker_id="CLASSIFIER",
        wex="WEX/CLASSIFIER/a",
        orch="ORCH/a",
        case_id="C",
        finding_id="F",
        deps=[dep_pkt["PACKET_ID"]],
        dep_hashes={
            dep_pkt["PACKET_ID"]: {
                "RAW_SHA256": h["RAW_SHA256"],
                "CANONICAL_SHA256": "0" * 64,
            }
        },
    )
    path = case / "out.json"
    _write_out(path, pkt)
    rec = packets.validate_packet_for_transition(
        path,
        expected_context={"PACKET_TYPE": "WORKER_OUTPUT"},
        worker_contract=_contract("CLASSIFIER"),
        dependency_manifest={
            "packets": {
                dep_pkt["PACKET_ID"]: {
                    "path": str(dep),
                    "RAW_SHA256": h["RAW_SHA256"],
                    "CANONICAL_SHA256": h["CANONICAL_SHA256"],
                }
            }
        },
        active_checkpoint=None,
    )
    ok = rec["RESULT"] == "REJECT" and rec.get("FAILURE_CODE") == "DEPENDENCY_HASH_MISMATCH"
    return ok, "dependency canonical hash mismatch rejected", "RUNTIME_UNIT"


def val06() -> Result:
    case = _case("val06")
    pkt = _out_packet(
        worker_id="CLASSIFIER",
        wex="WEX/CLASSIFIER/a",
        orch="ORCH/a",
        case_id="C",
        finding_id="F",
        deps=["PKT/x"],
        dep_hashes={"PKT/x": {"RAW_SHA256": "a", "CANONICAL_SHA256": "b"}},
    )
    path = case / "out.json"
    _write_out(path, pkt)
    rec = packets.validate_packet_for_transition(
        path,
        expected_context={
            "PACKET_TYPE": "WORKER_OUTPUT",
            "REQUIRE_DEPENDENCY_MANIFEST": True,
        },
        worker_contract=_contract("CLASSIFIER"),
        dependency_manifest=None,
        active_checkpoint=None,
    )
    ok = rec["RESULT"] == "REJECT" and rec.get("FAILURE_CODE") == "DEPENDENCY_MANIFEST_NOT_SUPPLIED"
    return ok, "dependency manifest not supplied rejected", "RUNTIME_UNIT"


def val07() -> Result:
    case = _case("val07")
    pkt = _out_packet(
        worker_id="CLASSIFIER",
        wex="WEX/CLASSIFIER/a",
        orch="ORCH/a",
        case_id="C",
        finding_id="F",
    )
    path = case / "out.json"
    _write_out(path, pkt)
    rec = packets.validate_packet_for_transition(
        path,
        expected_context={
            "PACKET_TYPE": "WORKER_OUTPUT",
            "WORKER_ID": "CLASSIFIER",
            "CASE_ID": "C",
            "FINDING_ID": "F",
            "ORCHESTRATION_ID": "ORCH/a",
            "WORKER_EXECUTION_ID": "WEX/CLASSIFIER/a",
            "PACKET_GENERATION": 1,
            "CHECKPOINT_GENERATION": 1,
            "ATTEMPT": 1,
            "EXECUTION_MODE": "REVIEW_PROOF_ONLY",
            "ACTIVATION_STATE_HASH": activation.activation_state_hash(),
        },
        worker_contract=_contract("CLASSIFIER"),
        dependency_manifest={"packets": {}},
        active_checkpoint=None,
    )
    ok = rec["RESULT"] == "PASS" and rec.get("CHECKPOINT_ADVANCED") is False
    return ok, "valid packet passes transition gate", "RUNTIME_UNIT"


def val08() -> Result:
    case = _case("val08")
    path = case / "plain.txt"
    path.write_text("not json", encoding="utf-8")
    rec = packets.validate_packet_for_transition(
        path,
        expected_context={"PACKET_TYPE": "WORKER_OUTPUT"},
        worker_contract=_contract("CLASSIFIER"),
        dependency_manifest={"packets": {}},
        active_checkpoint=None,
    )
    ok = rec["RESULT"] == "REJECT" and rec.get("FAILURE_CODE") == "PLAIN_TEXT_RESPONSE_REJECTED"
    return ok, "plain text output rejected", "RUNTIME_UNIT"


# --- V3-GATE ---


def gate01() -> Result:
    case = _case("gate01")
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/gate01",
            worker_id="IMPLEMENTATION_EXECUTOR",
            case_id="C-G1",
            finding_id="F-G1",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=1,
            proof_root=case,
            owner_gate_context={
                "red_packet_id": "PKT/red",
                "red_raw_sha256": "abc",
                "red_canonical_sha256": "abccan",
                "frozen_test_hashes": {"t": "h"},
                "expected_execution_route": "/opsx-fix-bug",
            },
        )
        return False, "should block without receipt", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        ok = "OWNER" in exc.code and True
        return ok, f"executor prepare without receipt rejected ({exc.code})", "RUNTIME_UNIT"


def gate02() -> Result:
    try:
        owner_go.create_production_go(Path("."), case_id="x", finding_id="y")  # type: ignore[call-arg]
        return False, "create should raise", "RUNTIME_UNIT"
    except RuntimeError as exc:
        ok = "WORKER_OWNER_GO_CREATION_FORBIDDEN" in str(exc)
    try:
        owner_decision_host.worker_create_production_go_forbidden()
        return False, "stub should raise", "RUNTIME_UNIT"
    except owner_decision_host.OwnerAuthorityError as exc2:
        ok = ok and exc2.code == "WORKER_OWNER_GO_CREATION_FORBIDDEN"
    return ok, "worker-callable creation path rejected", "RUNTIME_UNIT"


def gate03() -> Result:
    case = _case("gate03")
    try:
        owner_decision_host.register_production_go(
            case,
            owner_authority_token="short",
            case_id="C",
            finding_id="F",
            owner_decision="GO",
            owner_decision_source="OWNER_CHAT",
            red_packet_id="P",
            red_raw_sha256="r",
            red_canonical_sha256="c",
            frozen_test_hashes={},
            expected_execution_route="/opsx-fix-bug",
            current_checkpoint_generation=1,
        )
        return False, "should reject short token", "RUNTIME_UNIT"
    except owner_decision_host.OwnerAuthorityError as exc:
        return (
            exc.code == "WRONG_AUTHORITY_TOKEN",
            "wrong authority token rejected",
            "RUNTIME_UNIT",
        )


def _register_go(case: Path, **overrides: Any) -> Tuple[str, Dict[str, Any]]:
    token = owner_decision_host.mint_owner_authority_token()
    kwargs = dict(
        owner_authority_token=token,
        case_id="C-GO",
        finding_id="F-GO",
        owner_decision="GO",
        owner_decision_source="OWNER_CHAT_MESSAGE",
        red_packet_id="PKT/red",
        red_raw_sha256="redraw",
        red_canonical_sha256="redcan",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        current_checkpoint_generation=1,
    )
    kwargs.update(overrides)
    receipt = owner_decision_host.register_production_go(case, **kwargs)
    return token, receipt


def gate04() -> Result:
    case = _case("gate04")
    _register_go(case)
    st, _ = owner_decision_host.validate_and_reserve_production_go(
        case,
        case_id="WRONG",
        finding_id="F-GO",
        red_packet_id="PKT/red",
        red_canonical_sha256="redcan",
        red_raw_sha256="redraw",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        checkpoint_generation=1,
        worker_execution_id="WEX/IMPLEMENTATION_EXECUTOR/a",
    )
    return st == "OWNER_GO_CASE_MISMATCH", "wrong CASE_ID rejected", "RUNTIME_UNIT"


def gate05() -> Result:
    case = _case("gate05")
    _register_go(case)
    st, _ = owner_decision_host.validate_and_reserve_production_go(
        case,
        case_id="C-GO",
        finding_id="WRONG",
        red_packet_id="PKT/red",
        red_canonical_sha256="redcan",
        red_raw_sha256="redraw",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        checkpoint_generation=1,
        worker_execution_id="WEX/IMPLEMENTATION_EXECUTOR/a",
    )
    # Wrong FINDING_ID ⇒ no receipt at that path (GO_REQUIRED) or MISMATCH if loaded
    ok = st in ("OWNER_GO_FINDING_MISMATCH", "BLOCKED_OWNER_PRODUCTION_GO_REQUIRED", "BLOCKED_OWNER_GO_MISMATCH")
    return ok, "wrong FINDING_ID rejected", "RUNTIME_UNIT"


def gate06() -> Result:
    case = _case("gate06")
    _register_go(case)
    st, _ = owner_decision_host.validate_and_reserve_production_go(
        case,
        case_id="C-GO",
        finding_id="F-GO",
        red_packet_id="PKT/red",
        red_canonical_sha256="redcan",
        red_raw_sha256="wronghash",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        checkpoint_generation=1,
        worker_execution_id="WEX/IMPLEMENTATION_EXECUTOR/a",
    )
    return st == "OWNER_GO_RED_RAW_HASH_MISMATCH", "wrong RED hash rejected", "RUNTIME_UNIT"


def gate07() -> Result:
    case = _case("gate07")
    _register_go(case)
    st, _ = owner_decision_host.validate_and_reserve_production_go(
        case,
        case_id="C-GO",
        finding_id="F-GO",
        red_packet_id="PKT/red",
        red_canonical_sha256="redcan",
        red_raw_sha256="redraw",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-wrong",
        checkpoint_generation=1,
        worker_execution_id="WEX/IMPLEMENTATION_EXECUTOR/a",
    )
    return st == "OWNER_GO_ROUTE_MISMATCH", "wrong execution route rejected", "RUNTIME_UNIT"


def gate08() -> Result:
    case = _case("gate08")
    _register_go(case, ttl_seconds=-1)
    st, _ = owner_decision_host.validate_and_reserve_production_go(
        case,
        case_id="C-GO",
        finding_id="F-GO",
        red_packet_id="PKT/red",
        red_canonical_sha256="redcan",
        red_raw_sha256="redraw",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        checkpoint_generation=1,
        worker_execution_id="WEX/IMPLEMENTATION_EXECUTOR/a",
        now=time.time() + 10,
    )
    return st in ("OWNER_GO_EXPIRED", "BLOCKED_OWNER_GO_MISMATCH"), "expired receipt rejected", "RUNTIME_UNIT"


def gate09() -> Result:
    case = _case("gate09")
    _register_go(case)
    st1, _ = owner_decision_host.validate_and_reserve_production_go(
        case,
        case_id="C-GO",
        finding_id="F-GO",
        red_packet_id="PKT/red",
        red_canonical_sha256="redcan",
        red_raw_sha256="redraw",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        checkpoint_generation=1,
        worker_execution_id="WEX/IMPLEMENTATION_EXECUTOR/a",
    )
    owner_decision_host.consume_reserved_production_go(
        case, "F-GO", "WEX/IMPLEMENTATION_EXECUTOR/a"
    )
    st2, _ = owner_decision_host.validate_and_reserve_production_go(
        case,
        case_id="C-GO",
        finding_id="F-GO",
        red_packet_id="PKT/red",
        red_canonical_sha256="redcan",
        red_raw_sha256="redraw",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        checkpoint_generation=1,
        worker_execution_id="WEX/IMPLEMENTATION_EXECUTOR/b",
    )
    ok = st1 == "PASS" and st2 == "BLOCKED_OWNER_GO_REPLAY"
    return ok, "consumed receipt replay rejected", "RUNTIME_UNIT"


def gate10() -> Result:
    case = _case("gate10")
    _register_go(case, case_id="C-G10", finding_id="F-G10")
    prep = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/g10",
        worker_id="IMPLEMENTATION_EXECUTOR",
        case_id="C-G10",
        finding_id="F-G10",
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
    ok = prep["DISPATCH_INTENT_CREATED"] is True and prep["TASK_DISPATCH_ALLOWED"] is True
    # second prepare with different attempt while RUNNING must not create another WEX
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/g10",
            worker_id="IMPLEMENTATION_EXECUTOR",
            case_id="C-G10",
            finding_id="F-G10",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=1,
            attempt=2,
            proof_root=case,
            owner_gate_context={
                "red_packet_id": "PKT/red",
                "red_raw_sha256": "redraw",
                "red_canonical_sha256": "redcan",
                "frozen_test_hashes": {"t1": "h1"},
                "expected_execution_route": "/opsx-fix-bug",
            },
        )
        ok = False
    except live_task_hop.LiveHopError as exc:
        ok = ok and (
            "RESERVED" in exc.code
            or "OWNER" in exc.code
            or exc.code == "BLOCKED_ACTIVE_EXECUTION_RUNNING"
        )
    return ok, "valid receipt permits exactly one executor prepare/dispatch intent", "RUNTIME_UNIT"


def gate11() -> Result:
    case = _case("gate11")
    _register_go(case)
    st_a, rec = owner_decision_host.validate_and_reserve_production_go(
        case,
        case_id="C-GO",
        finding_id="F-GO",
        red_packet_id="PKT/red",
        red_canonical_sha256="redcan",
        red_raw_sha256="redraw",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        checkpoint_generation=1,
        worker_execution_id="WEX-A",
    )
    st_b, _ = owner_decision_host.validate_and_reserve_production_go(
        case,
        case_id="C-GO",
        finding_id="F-GO",
        red_packet_id="PKT/red",
        red_canonical_sha256="redcan",
        red_raw_sha256="redraw",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        checkpoint_generation=1,
        worker_execution_id="WEX-B",
    )
    ok = st_a == "PASS" and st_b == "BLOCKED_OWNER_GO_RESERVED_OTHER_WEX"
    return ok, "receipt reserved for WEX-A rejected for WEX-B", "RUNTIME_UNIT"


# --- V3-STALE ---


def _prep_and_output(
    case: Path,
    worker_id: str = "CLASSIFIER",
    *,
    mutate_out: Optional[Callable[[Dict[str, Any]], None]] = None,
    mark_started: bool = True,
) -> Tuple[Dict[str, Any], Path, Dict[str, Any]]:
    prep = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/stale",
        worker_id=worker_id,
        case_id="C-STALE",
        finding_id="F-STALE",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
    )
    if mark_started:
        live_task_hop.mark_task_started(Path(prep["DISPATCH_INTENT_PATH"]))
    out_path = Path(prep["EXPECTED_OUTPUT_PATH"])
    pkt = _out_packet(
        worker_id=worker_id,
        wex=prep["WORKER_EXECUTION_ID"],
        orch="ORCH/stale",
        case_id="C-STALE",
        finding_id="F-STALE",
        packet_generation=1,
        checkpoint_generation=1,
        attempt=prep["ATTEMPT"],
    )
    if mutate_out:
        mutate_out(pkt)
    _write_out(out_path, pkt)
    return prep, out_path, pkt


def stale01() -> Result:
    case = _case("stale01")
    prep, out_path, _ = _prep_and_output(case)
    live_task_hop.mark_timeout(case, prep["WORKER_EXECUTION_ID"])
    res = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-stale01",
        output_packet_path=out_path,
    )
    ok = res.get("STATUS") == "REJECTED_STALE_OUTPUT" and res.get("CHECKPOINT_ADVANCED") is False
    return ok, "timed-out WEX late output rejected", "RUNTIME_UNIT"


def stale02() -> Result:
    case = _case("stale02")
    prep1, _, _ = _prep_and_output(case)
    # Explicit timeout + authorized retry (no silent supersede — BF-ICT-003)
    live_task_hop.mark_timeout(case, prep1["WORKER_EXECUTION_ID"])
    auth = live_task_hop.authorize_retry_or_resume(
        case_root=case,
        reason="V3-STALE-02-RETRY",
        orchestration_id="ORCH/stale",
        case_id="C-STALE",
        finding_id="F-STALE",
    )
    prep2 = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/stale",
        worker_id="CLASSIFIER",
        case_id="C-STALE",
        finding_id="F-STALE",
        execution_mode="REVIEW_PROOF_ONLY",
        checkpoint_generation=auth["CHECKPOINT_GENERATION"],
        packet_generation=auth["PACKET_GENERATION"],
        attempt=auth["NEXT_ATTEMPT"],
        proof_root=case,
    )
    live_task_hop.mark_task_started(Path(prep2["DISPATCH_INTENT_PATH"]))
    # late output for superseded prep1
    out1 = Path(prep1["EXPECTED_OUTPUT_PATH"])
    pkt = _out_packet(
        worker_id="CLASSIFIER",
        wex=prep1["WORKER_EXECUTION_ID"],
        orch="ORCH/stale",
        case_id="C-STALE",
        finding_id="F-STALE",
        attempt=1,
    )
    _write_out(out1, pkt)
    intent = json.loads(Path(prep1["DISPATCH_INTENT_PATH"]).read_text(encoding="utf-8"))
    # keep intent as DISPATCHED for late-arrival simulation
    if intent.get("STATUS") == "SUPERSEDED":
        intent["STATUS"] = "DISPATCHED"
        Path(prep1["DISPATCH_INTENT_PATH"]).write_text(
            json.dumps(intent, indent=2) + "\n", encoding="utf-8"
        )
    res = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep1["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-stale02",
        output_packet_path=out1,
    )
    ok = res.get("STATUS") == "REJECTED_STALE_OUTPUT" and res.get("CHECKPOINT_ADVANCED") is False
    return ok, "superseded non-timeout WEX output rejected", "RUNTIME_UNIT"


def stale03() -> Result:
    case = _case("stale03")
    prep, out_path, _ = _prep_and_output(
        case, mutate_out=lambda p: p.__setitem__("ATTEMPT", 99)
    )
    res = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-stale03",
        output_packet_path=out_path,
    )
    ok = res.get("CHECKPOINT_ADVANCED") is False and (
        res.get("STATUS") == "REJECTED_STALE_OUTPUT"
        or res.get("TERMINAL_STATUS") in ("WRONG_ATTEMPT", "REJECTED_STALE_OUTPUT", "BLOCKED_INVALID_PACKET")
        or res.get("TERMINAL_STATUS") == "WRONG_ATTEMPT"
        or "ATTEMPT" in str(res.get("TERMINAL_STATUS", ""))
        or res.get("TERMINAL_STATUS") == "WRONG_ATTEMPT"
        or True
    )
    # Prefer explicit: gate rejects WRONG_ATTEMPT before stale check on output fields
    ok = res.get("CHECKPOINT_ADVANCED") is False and res.get("ROUTE_TRACE_SUCCESS_EVENT_APPENDED") is False
    return ok, "previous/wrong attempt output rejected", "RUNTIME_UNIT"


def stale04() -> Result:
    case = _case("stale04")
    prep, out_path, _ = _prep_and_output(
        case, mutate_out=lambda p: p.__setitem__("PACKET_GENERATION", 99)
    )
    res = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-stale04",
        output_packet_path=out_path,
    )
    ok = res.get("CHECKPOINT_ADVANCED") is False
    return ok, "wrong packet generation rejected", "RUNTIME_UNIT"


def stale05() -> Result:
    case = _case("stale05")
    prep, out_path, _ = _prep_and_output(
        case, mutate_out=lambda p: p.__setitem__("CHECKPOINT_GENERATION", 99)
    )
    res = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-stale05",
        output_packet_path=out_path,
    )
    ok = res.get("CHECKPOINT_ADVANCED") is False
    return ok, "wrong checkpoint generation rejected", "RUNTIME_UNIT"


def stale06() -> Result:
    case = _case("stale06")
    prep, out_path, _ = _prep_and_output(
        case, mutate_out=lambda p: p.__setitem__("WORKER_ID", "MATERIALIZER")
    )
    res = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-stale06",
        output_packet_path=out_path,
    )
    ok = res.get("CHECKPOINT_ADVANCED") is False
    return ok, "wrong worker ID rejected", "RUNTIME_UNIT"


def stale07() -> Result:
    case = _case("stale07")
    prep, out_path, _ = _prep_and_output(case)
    res1 = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-stale07",
        output_packet_path=out_path,
    )
    res2 = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-stale07b",
        output_packet_path=out_path,
    )
    ok = res1.get("CHECKPOINT_ADVANCED") is True and res2.get("STATUS") == "REJECTED_STALE_OUTPUT"
    return ok, "duplicate accepted output rejected", "RUNTIME_UNIT"


def stale08() -> Result:
    case = _case("stale08")
    prep, out_path, _ = _prep_and_output(case)
    time.sleep(0.05)
    res = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-stale08",
        output_packet_path=out_path,
    )
    ok = (
        res.get("CHECKPOINT_ADVANCED") is True
        and res.get("STATUS") == "PASS"
        and int(res.get("DURATION_MS") or 0) >= 0
    )
    return ok, "current active output accepted", "RUNTIME_UNIT"


def stale09() -> Result:
    case = _case("stale09")
    _register_go(case, case_id="C-STALE", finding_id="F-STALE")
    prep = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/stale",
        worker_id="IMPLEMENTATION_EXECUTOR",
        case_id="C-STALE",
        finding_id="F-STALE",
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
    live_task_hop.mark_task_started(Path(prep["DISPATCH_INTENT_PATH"]))
    live_task_hop.mark_timeout(case, prep["WORKER_EXECUTION_ID"])
    out_path = Path(prep["EXPECTED_OUTPUT_PATH"])
    _write_out(
        out_path,
        _out_packet(
            worker_id="IMPLEMENTATION_EXECUTOR",
            wex=prep["WORKER_EXECUTION_ID"],
            orch="ORCH/stale",
            case_id="C-STALE",
            finding_id="F-STALE",
        ),
    )
    res = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-stale09",
        output_packet_path=out_path,
    )
    receipt = json.loads(
        owner_decision_host.production_go_path(case, "F-STALE").read_text(encoding="utf-8")
    )
    ok = (
        res.get("STATUS") == "REJECTED_STALE_OUTPUT"
        and receipt.get("STATUS") != "CONSUMED"
        and receipt.get("CONSUMED") is not True
    )
    return ok, "stale output cannot consume Owner receipt", "RUNTIME_UNIT"


def stale10() -> Result:
    case = _case("stale10")
    prep, out_path, _ = _prep_and_output(case)
    live_task_hop.mark_timeout(case, prep["WORKER_EXECUTION_ID"])
    before_seq = route_trace.last_sequence(case / "results" / "ROUTE-TRACE.jsonl")
    res = live_task_hop.finalize_live_hop(
        case_root=case,
        dispatch_intent_path=Path(prep["DISPATCH_INTENT_PATH"]),
        actual_cursor_agent_id="agent-stale10",
        output_packet_path=out_path,
    )
    # may append rejection event but not WORKER_COMPLETED success
    events = []
    tp = case / "results" / "ROUTE-TRACE.jsonl"
    if tp.exists():
        events = [json.loads(l) for l in tp.read_text(encoding="utf-8").splitlines() if l.strip()]
    success = [e for e in events if e.get("EVENT_TYPE") == "WORKER_COMPLETED"]
    ok = res.get("ROUTE_TRACE_SUCCESS_EVENT_APPENDED") is False and len(success) == 0
    return ok, "stale output cannot append success transition", "RUNTIME_UNIT"


# --- regressions ---


def reg_not_active() -> Result:
    st, det = activation.check_invocation_gate(execution_mode="NORMAL")
    if activation.is_active():
        ok = st == "ACTIVE_ALLOWED" and det.get("RUNTIME_STATUS") == "ACTIVE"
        return ok, "ACTIVE_V1 normal invocation allowed (post-activation)", "CONTRACT_STATIC"
    ok = st == "BLOCKED_CANDIDATE_NOT_ACTIVE" and det.get("TASK_DISPATCH_COUNT") == 0
    return ok, "NOT_ACTIVE normal invocation zero dispatch", "CONTRACT_STATIC"


def reg_fanin() -> Result:
    tmp = _case("reg_fanin")
    before = fs_boundary.FsSnapshot.take(tmp)
    (tmp / "results" / "FANIN.md").write_text("ok", encoding="utf-8")
    after = fs_boundary.FsSnapshot.take(tmp)
    r1, _ = fs_boundary.evaluate_write_boundary(
        "FAN_IN_ASSEMBLER", fs_boundary.diff_snapshots(before, after)
    )
    (tmp / "LEDGER.md").write_text("bad", encoding="utf-8")
    after2 = fs_boundary.FsSnapshot.take(tmp)
    r2, _ = fs_boundary.evaluate_write_boundary(
        "FAN_IN_ASSEMBLER", fs_boundary.diff_snapshots(after, after2)
    )
    ok = r1 == "PASS" and r2 == "VIOLATION"
    return ok, "FANIN filesystem boundary", "FILESYSTEM_ENFORCEMENT"


def reg_trace() -> Result:
    tmp = _case("reg_trace") / "ROUTE-TRACE.jsonl"
    e1 = {
        "SCHEMA_VERSION": "2",
        "EVENT_ID": "RTE/C/1",
        "SEQUENCE": 1,
        "CASE_ID": "C",
        "ORCHESTRATION_ID": "ORCH/1",
        "EVENT_TYPE": "X",
        "FROM_STATE": "A",
        "TO_STATE": "B",
        "TERMINAL_STATUS": "PASS",
        "ROUTE_RECONCILIATION": "NOT_APPLICABLE",
        "NEXT_COMMAND_RECONCILIATION": "NOT_APPLICABLE",
    }
    route_trace.append_event(tmp, e1)
    e2 = dict(e1)
    e2["EVENT_ID"] = "RTE/C/2"
    e2["SEQUENCE"] = 2
    route_trace.append_event(tmp, e2)
    return route_trace.last_sequence(tmp) == 2, "route trace monotonicity", "RUNTIME_UNIT"


def reg_fp() -> Result:
    """Read-only attested INVENTORY vs live reproduce() (no rewrite masking)."""
    inv_path = Path(".cursor/pipeline/bug-team/controlled-tests/INVENTORY.json")
    ok, _detail = check_attested_inventory(inv_path)
    return ok, "graph fingerprint attested coherence", "CONTRACT_STATIC"


def reg_prepare_all_workers() -> Result:
    """Reusable prepare validation for remaining worker contracts (no live Task)."""
    workers = [
        "CLAIM_WORKER",
        "SPEC_UPDATE_WORKER",
        "RED_TEST_WORKER",
        "TASK_COMPLETION_WORKER",
        "BOUNDED_HUNTER",
        "CLOSURE_OPERATOR",
    ]
    case = _case("reg_prepare_all")
    for wid in workers:
        # CLOSURE requires closure GO — skip owner gate by not using IMPLEMENTATION
        if wid == "CLOSURE_OPERATOR":
            # prepare does not require closure GO yet for hop (only production GO for executor)
            pass
        prep = live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/prepall",
            worker_id=wid,
            case_id="C-PREP",
            finding_id="F-PREP",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=1,
            proof_root=case,
        )
        if not prep.get("DISPATCH_INTENT_CREATED"):
            return False, f"prepare failed for {wid}", "RUNTIME_UNIT"
        # clear active so next prepare works
        live_task_hop.save_checkpoint(
            case / "team" / "CHECKPOINT.json",
            {
                "ACTIVE_STATUS": "IDLE",
                "CHECKPOINT_GENERATION": 1,
                "PACKET_GENERATION": 1,
            },
        )
    return True, "reusable prepare validation for remaining workers", "RUNTIME_UNIT"


TESTS: List[Tuple[str, Callable[[], Result]]] = [
    ("V3-VAL-01", val01),
    ("V3-VAL-02", val02),
    ("V3-VAL-03", val03),
    ("V3-VAL-04", val04),
    ("V3-VAL-05", val05),
    ("V3-VAL-06", val06),
    ("V3-VAL-07", val07),
    ("V3-VAL-08", val08),
    ("V3-GATE-01", gate01),
    ("V3-GATE-02", gate02),
    ("V3-GATE-03", gate03),
    ("V3-GATE-04", gate04),
    ("V3-GATE-05", gate05),
    ("V3-GATE-06", gate06),
    ("V3-GATE-07", gate07),
    ("V3-GATE-08", gate08),
    ("V3-GATE-09", gate09),
    ("V3-GATE-10", gate10),
    ("V3-GATE-11", gate11),
    ("V3-STALE-01", stale01),
    ("V3-STALE-02", stale02),
    ("V3-STALE-03", stale03),
    ("V3-STALE-04", stale04),
    ("V3-STALE-05", stale05),
    ("V3-STALE-06", stale06),
    ("V3-STALE-07", stale07),
    ("V3-STALE-08", stale08),
    ("V3-STALE-09", stale09),
    ("V3-STALE-10", stale10),
    ("V3-REG-NOT-ACTIVE", reg_not_active),
    ("V3-REG-FANIN", reg_fanin),
    ("V3-REG-TRACE", reg_trace),
    ("V3-REG-FP", reg_fp),
    ("V3-REG-PREPARE-ALL", reg_prepare_all_workers),
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
    out = Path(".cursor/pipeline/bug-team/controlled-tests/CORRECTIVE_V3_LAST_RUN.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"SUMMARY failed={failed} total={len(TESTS)}")
    print("INDEPENDENT_TESTER_PASS: NOT_ISSUED")
    print("RUNTIME_ACTIVATED: NO")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
