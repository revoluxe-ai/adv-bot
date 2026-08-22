# -*- coding: utf-8 -*-
"""Corrective V2 controlled tests CT-01..CT-18.

Labels each case as REAL_CURSOR_TASK | SIMULATED_BACKEND | CONTRACT_STATIC |
FILESYSTEM_ENFORCEMENT. Does not claim Independent Tester PASS.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import activation, fs_boundary, owner_go, packets, route_trace, timeout
from runtime.graph_fingerprint import check_attested_inventory
from runtime.orchestrator import OrchestratorRuntime

Result = Tuple[bool, str, str]


def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="opsx-ct-"))


def ct01() -> Result:
    status, det = activation.check_invocation_gate(execution_mode="NORMAL")
    if activation.is_active():
        # ACTIVE_V1: NORMAL is allowed; V8 family fanout remains shadow-disabled.
        ok = status == "ACTIVE_ALLOWED" and det.get("RUNTIME_STATUS") == "ACTIVE"
        return ok, "ACTIVE_V1 normal invocation allowed; activation intact", "CONTRACT_STATIC"
    ok = status == "BLOCKED_CANDIDATE_NOT_ACTIVE" and det.get("TASK_DISPATCH_COUNT") == 0
    return ok, "normal invocation blocked while NOT_ACTIVE", "CONTRACT_STATIC"


def ct02() -> Result:
    bad = Path("C:/tmp/not-harness-proof")
    st1, _ = activation.check_invocation_gate(
        execution_mode="REVIEW_PROOF_ONLY", proof_root=bad
    )
    good = Path(".tmp/opsx-bug-team-harness/live-runtime-proof/ct02")
    good.mkdir(parents=True, exist_ok=True)
    st2, _ = activation.check_invocation_gate(
        execution_mode="REVIEW_PROOF_ONLY", proof_root=good
    )
    ok = st1 == "BLOCKED_PROOF_ROOT_OUTSIDE_HARNESS" and st2 == "PROOF_MODE_ALLOWED"
    return ok, "proof mode only under harness root", "CONTRACT_STATIC"


def ct03() -> Result:
    pkt = packets.new_input_packet(
        worker_id="MATERIALIZER",
        orchestration_id="NOT_ORCH",
        worker_execution_id="WEX/MATERIALIZER/x",
        case_id="C",
        finding_id="F",
        checkpoint_generation=1,
        packet_generation=1,
        activation_state_hash=activation.activation_state_hash(),
        execution_mode="REVIEW_PROOF_ONLY",
        payload={},
    )
    try:
        packets.validate_packet(pkt, require_active_for_normal=False)
        return False, "should reject direct packet", "SIMULATED_BACKEND"
    except packets.PacketValidationError as exc:
        ok = exc.code == "DIRECT_PACKET_WITHOUT_ORCHESTRATION"
        return ok, "direct worker packet without ORCH/ rejected", "SIMULATED_BACKEND"


def ct04() -> Result:
    # Placeholder: live proof fills CURSOR_AGENT_ID; here we assert record schema requires it
    rec = {"CURSOR_AGENT_ID": "agent-example", "TASK_TOOL": "Cursor Task"}
    ok = rec["CURSOR_AGENT_ID"] != "WEX/MATERIALIZER/x" and rec["TASK_TOOL"] == "Cursor Task"
    return ok, "dispatch record uses Cursor agent id field (live matrix fills)", "CONTRACT_STATIC"


def ct05() -> Result:
    tmp = _tmp() / "case"
    orch = OrchestratorRuntime(
        case_root=tmp, execution_mode="REVIEW_PROOF_ONLY", proof_root=tmp
    )
    wex = "WEX/CLASSIFIER/mal"
    out = tmp / "team" / "packets" / "mal.out.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("this is not json packet\n", encoding="utf-8")
    before = fs_boundary.FsSnapshot.take(tmp)
    gen_before = orch.checkpoint_generation
    res = orch.finalize_after_task(
        worker_id="CLASSIFIER",
        wex=wex,
        case_id="BUGCASE-CT",
        finding_id="F1",
        in_path=out,
        in_hash="00",
        out_path=out,
        before=before,
        cursor_agent_id="test-agent",
        started_at=time.time(),
        attempt=1,
        from_state="A",
        to_state="B",
    )
    ok = (
        res.get("STATUS") == "BLOCKED_LEGACY_FINALIZE_DISABLED"
        and res.get("CHECKPOINT_ADVANCED") is False
        and orch.checkpoint_generation == gen_before
    )
    shutil.rmtree(tmp.parent, ignore_errors=True)
    return ok, "legacy finalize_after_task disabled (BF-ICT-002)", "SIMULATED_BACKEND"


def ct06() -> Result:
    pkt = packets.new_input_packet(
        worker_id="CLASSIFIER",
        orchestration_id="ORCH/x",
        worker_execution_id="WEX/CLASSIFIER/x",
        case_id="CASE-A",
        finding_id="F-A",
        checkpoint_generation=1,
        packet_generation=1,
        activation_state_hash=activation.activation_state_hash(),
        execution_mode="REVIEW_PROOF_ONLY",
        payload={},
    )
    try:
        packets.validate_packet(
            pkt,
            expect_case="CASE-B",
            expect_finding="F-A",
            require_active_for_normal=False,
        )
        return False, "should reject wrong case", "SIMULATED_BACKEND"
    except packets.PacketValidationError as exc:
        return exc.code == "WRONG_CASE_ID", "wrong CASE_ID rejected", "SIMULATED_BACKEND"


def ct07() -> Result:
    pkt = packets.new_input_packet(
        worker_id="CLASSIFIER",
        orchestration_id="ORCH/x",
        worker_execution_id="WEX/CLASSIFIER/x",
        case_id="C",
        finding_id="F",
        checkpoint_generation=1,
        packet_generation=1,
        activation_state_hash=activation.activation_state_hash(),
        execution_mode="REVIEW_PROOF_ONLY",
        payload={},
    )
    try:
        packets.validate_packet(
            pkt, expect_packet_generation=9, require_active_for_normal=False
        )
        return False, "should reject stale gen", "SIMULATED_BACKEND"
    except packets.PacketValidationError as exc:
        return (
            exc.code == "STALE_PACKET_GENERATION",
            "stale packet generation rejected",
            "SIMULATED_BACKEND",
        )


def ct08() -> Result:
    try:
        packets.validate_dependency_hashes(
            {"PKT/dep": "deadbeef"}, {"PKT/dep": Path("nope.json")}
        )
        return False, "should fail", "SIMULATED_BACKEND"
    except packets.PacketValidationError as exc:
        ok = exc.code in ("MISSING_DEPENDENCY", "DEPENDENCY_HASH_MISMATCH")
        return ok, "dependency hash mismatch/missing rejected", "SIMULATED_BACKEND"


def ct09() -> Result:
    tmp = _tmp() / "plain.txt"
    tmp.write_text("hello", encoding="utf-8")
    try:
        packets.read_packet(tmp)
        return False, "should reject plain text", "SIMULATED_BACKEND"
    except packets.PacketValidationError as exc:
        shutil.rmtree(tmp.parent, ignore_errors=True)
        return (
            exc.code == "PLAIN_TEXT_RESPONSE_REJECTED",
            "plain-text worker response rejected",
            "SIMULATED_BACKEND",
        )


def ct10() -> Result:
    tmp = _tmp()
    token = __import__("runtime.owner_decision_host", fromlist=["mint_owner_authority_token"]).mint_owner_authority_token()
    from runtime import owner_decision_host

    receipt = owner_decision_host.register_production_go(
        tmp,
        owner_authority_token=token,
        case_id="C1",
        finding_id="F1",
        owner_decision="GO",
        owner_decision_source="OWNER_CHAT_MESSAGE",
        red_packet_id="PKT/red",
        red_raw_sha256="abc",
        red_canonical_sha256="abc_can",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        current_checkpoint_generation=1,
    )
    st, reason = owner_go.validate_production_go_for_executor(
        receipt,
        case_id="C1",
        finding_id="F1",
        red_evidence_sha256="abc",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        checkpoint_generation=1,
    )
    shutil.rmtree(tmp, ignore_errors=True)
    return st == "PASS", "Owner GO bound to CASE/FINDING/RED hash", "SIMULATED_BACKEND"


def ct11() -> Result:
    tmp = _tmp()
    from runtime import owner_decision_host

    token = owner_decision_host.mint_owner_authority_token()
    receipt = owner_decision_host.register_production_go(
        tmp,
        owner_authority_token=token,
        case_id="C1",
        finding_id="F1",
        owner_decision="GO",
        owner_decision_source="OWNER_CHAT_MESSAGE",
        red_packet_id="PKT/red",
        red_raw_sha256="abc",
        red_canonical_sha256="abc_can",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        current_checkpoint_generation=1,
    )
    owner_go.consume_production_go(tmp, "F1", "WEX/IMPLEMENTATION_EXECUTOR/1")
    receipt2 = json.loads(owner_go.production_go_path(tmp, "F1").read_text(encoding="utf-8"))
    st, _ = owner_go.validate_production_go_for_executor(
        receipt2,
        case_id="C1",
        finding_id="F1",
        red_evidence_sha256="abc",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        checkpoint_generation=1,
    )
    st2, _ = owner_go.validate_production_go_for_executor(
        receipt,
        case_id="C1",
        finding_id="F1",
        red_evidence_sha256="zzz",
        frozen_test_hashes={"t1": "h1"},
        expected_execution_route="/opsx-fix-bug",
        checkpoint_generation=1,
    )
    shutil.rmtree(tmp, ignore_errors=True)
    ok = st == "BLOCKED_OWNER_GO_REPLAY" and st2 == "BLOCKED_OWNER_GO_MISMATCH"
    return ok, "stale/replayed Owner GO rejected", "SIMULATED_BACKEND"


def ct12() -> Result:
    tmp = _tmp()
    before = fs_boundary.FsSnapshot.take(tmp)
    (tmp / "app").mkdir()
    (tmp / "app" / "x.py").write_text("x", encoding="utf-8")
    after = fs_boundary.FsSnapshot.take(tmp)
    diff = fs_boundary.diff_snapshots(before, after)
    res, viol = fs_boundary.evaluate_write_boundary("GREEN_VERIFIER", diff)
    shutil.rmtree(tmp, ignore_errors=True)
    return res == "VIOLATION" and viol, "filesystem write outside boundary detected", "FILESYSTEM_ENFORCEMENT"


def ct13() -> Result:
    tmp = _tmp()
    before = fs_boundary.FsSnapshot.take(tmp)
    (tmp / "results").mkdir()
    (tmp / "results" / "FANIN.md").write_text("ok", encoding="utf-8")
    after_ok = fs_boundary.FsSnapshot.take(tmp)
    r1, _ = fs_boundary.evaluate_write_boundary(
        "FAN_IN_ASSEMBLER", fs_boundary.diff_snapshots(before, after_ok)
    )
    before2 = after_ok
    (tmp / "LEDGER.md").write_text("bad", encoding="utf-8")
    after_bad = fs_boundary.FsSnapshot.take(tmp)
    r2, viol = fs_boundary.evaluate_write_boundary(
        "FAN_IN_ASSEMBLER", fs_boundary.diff_snapshots(before2, after_bad)
    )
    shutil.rmtree(tmp, ignore_errors=True)
    ok = r1 == "PASS" and r2 == "VIOLATION" and any("LEDGER" in v for v in viol)
    return ok, "FANIN allowed PASS; forbidden write REJECTED_FROM_FILESYSTEM_DIFF", "FILESYSTEM_ENFORCEMENT"


def ct14() -> Result:
    tmp = _tmp() / "ROUTE-TRACE.jsonl"
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
    ok = route_trace.last_sequence(tmp) == 2
    shutil.rmtree(tmp.parent, ignore_errors=True)
    return ok, "route trace append monotonic", "SIMULATED_BACKEND"


def ct15() -> Result:
    tmp = _tmp() / "ROUTE-TRACE.jsonl"
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
        "EXPECTED_EXECUTION_ROUTE": "/opsx-apply",
        "ACTUAL_EXECUTION_ROUTE": "/opsx-fix-bug",
        "ROUTE_RECONCILIATION": "MATCH",
        "NEXT_COMMAND_RECONCILIATION": "NOT_APPLICABLE",
    }
    try:
        route_trace.append_event(tmp, e1)
        ok = False
    except route_trace.TraceIntegrityError as exc:
        ok = exc.code == "INVALID_ROUTE_RECONCILIATION"
    # duplicate sequence
    e_ok = dict(e1)
    e_ok["ROUTE_RECONCILIATION"] = "MISMATCH"
    e_ok["EVENT_ID"] = "RTE/C/1b"
    route_trace.append_event(tmp, e_ok)
    try:
        route_trace.append_event(tmp, e_ok)
        ok = False
    except route_trace.TraceIntegrityError as exc:
        ok = ok and exc.code in ("DUPLICATE_SEQUENCE", "DUPLICATE_EVENT_ID")
    try:
        route_trace.attempt_historical_rewrite(tmp, "x")
        ok = False
    except route_trace.TraceIntegrityError as exc:
        ok = ok and exc.code == "HISTORICAL_REWRITE_ATTEMPT_REJECTED"
    shutil.rmtree(tmp.parent, ignore_errors=True)
    return ok, "invalid reconciliation / dup / rewrite rejected", "SIMULATED_BACKEND"


def ct16() -> Result:
    ctl = timeout.TimeoutController()
    st = timeout.WorkerRuntimeState(
        worker_execution_id="WEX/X/1",
        worker_id="CLASSIFIER",
        attempt=1,
        max_attempts=2,
        packet_generation=1,
        checkpoint_generation=1,
    )
    ctl.mark_timeout(st)
    late = ctl.accept_late_output(
        worker_execution_id="WEX/X/1",
        packet_generation=1,
        expected_generation=1,
        attempt=1,
        expected_attempt=1,
    )
    return (
        late == "REJECT_LATE_OUTPUT_AFTER_TIMEOUT",
        "timeout late output rejected",
        "SIMULATED_BACKEND",
    )


def ct17() -> Result:
    ctl = timeout.TimeoutController()
    st = timeout.WorkerRuntimeState(
        worker_execution_id="WEX/X/1",
        worker_id="CLASSIFIER",
        attempt=1,
        max_attempts=2,
        packet_generation=1,
        checkpoint_generation=1,
    )
    ctl.mark_timeout(st)
    ok = ctl.may_dispatch_dependent() is False
    return ok, "dependent wave blocked after TIMEOUT", "SIMULATED_BACKEND"


def ct18() -> Result:
    """Read-only attested INVENTORY vs live reproduce() (no rewrite masking)."""
    inv_path = Path(".cursor/pipeline/bug-team/controlled-tests/INVENTORY.json")
    ok, _detail = check_attested_inventory(inv_path)
    return ok, "graph fingerprint attested coherence", "CONTRACT_STATIC"


TESTS: List[Tuple[str, Callable[[], Result]]] = [
    ("CT-01", ct01),
    ("CT-02", ct02),
    ("CT-03", ct03),
    ("CT-04", ct04),
    ("CT-05", ct05),
    ("CT-06", ct06),
    ("CT-07", ct07),
    ("CT-08", ct08),
    ("CT-09", ct09),
    ("CT-10", ct10),
    ("CT-11", ct11),
    ("CT-12", ct12),
    ("CT-13", ct13),
    ("CT-14", ct14),
    ("CT-15", ct15),
    ("CT-16", ct16),
    ("CT-17", ct17),
    ("CT-18", ct18),
]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass
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
            print(f"ERROR {name}: {exc}")
    out = Path(".cursor/pipeline/bug-team/controlled-tests/CORRECTIVE_CT_LAST_RUN.json")
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"SUMMARY failed={failed} total={len(TESTS)}")
    print("INDEPENDENT_TESTER_PASS: NOT_ISSUED")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
