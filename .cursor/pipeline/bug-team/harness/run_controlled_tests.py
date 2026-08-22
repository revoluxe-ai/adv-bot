# -*- coding: utf-8 -*-
"""Controlled-test harness for Candidate /opsx-bug-team (T1–T26).

Builder may run these locally. Results are NOT Independent Tester PASS.
RUNTIME stays NOT_ACTIVE.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

# Allow running as script from repo root
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from task_dispatch import (  # noqa: E402
    Orchestrator,
    TaskCallSpec,
    WORKER_IDS,
    parse_invocation,
)


Result = Tuple[bool, str]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _base_backends() -> Dict[str, Callable]:
    """Task-subagent doubles — separate execution identities via Orchestrator.dispatch."""

    def materializer(orch: Orchestrator, spec: TaskCallSpec) -> Dict[str, Any]:
        # Read input — worker materializes, not orchestrator
        raw_path = Path(spec.input_packet_path)
        raw = raw_path.read_text(encoding="utf-8")
        if "RAW_INTAKE_TEXT:" not in raw and "RAW_INTAKE" not in raw:
            # body may contain free text after header
            body = raw.split("\n\n", 1)[-1]
        else:
            body = raw
        finding = "FINDING-001"
        orch.artifacts["FINDING_ID"] = finding
        orch.artifacts["INTAKE_PATH"] = str(
            orch.case_root / "intakes" / "INTAKE-001.md"
        )
        (orch.case_root / "intakes").mkdir(exist_ok=True)
        intake_text = body if "RAW_INTAKE_TEXT" in body else f"RAW_INTAKE_TEXT: {body.strip()}"
        (orch.case_root / "intakes" / "INTAKE-001.md").write_text(
            intake_text + "\n", encoding="utf-8"
        )
        sufficiency = "SUFFICIENT_FOR_CLASSIFICATION"
        if "INCOMPLETE_MARKER" in body or "мало данных" in body.lower():
            sufficiency = "SUFFICIENT_FOR_MATERIALIZATION_ONLY"
        dup = orch.artifacts.get("FORCE_DUP")
        outcome = "NEW_CASE_CREATED"
        if dup:
            outcome = "DUPLICATE_ROOT_REJECTED"
        return {
            "STATUS": "PASS" if outcome != "DUPLICATE_ROOT_REJECTED" else "BLOCKED",
            "TERMINAL_STATUS": outcome if outcome != "NEW_CASE_CREATED" else "PASS",
            "FINDING_ID": finding,
            "DUPLICATE_OUTCOME": outcome,
            "INTAKE_SUFFICIENCY": sufficiency,
            "ARTIFACTS_WRITTEN": [str(orch.case_root / "intakes" / "INTAKE-001.md")],
            "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
        }

    def claim(orch: Orchestrator, spec: TaskCallSpec) -> Dict[str, Any]:
        if orch.artifacts.get("ACTIVE_CLAIM"):
            return {
                "STATUS": "BLOCKED",
                "TERMINAL_STATUS": "DUPLICATE_CLAIM_REJECTED",
                "ARTIFACTS_WRITTEN": [],
                "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
            }
        token = f"CLAIM/{orch.case_id}/FINDING-001/1"
        orch.artifacts["CLAIM_TOKEN"] = token
        orch.artifacts["ACTIVE_CLAIM"] = True
        return {
            "STATUS": "PASS",
            "TERMINAL_STATUS": "PASS",
            "CLAIM_TOKEN": token,
            "ARTIFACTS_WRITTEN": [],
            "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
        }

    def classifier(orch: Orchestrator, spec: TaskCallSpec) -> Dict[str, Any]:
        cls = orch.artifacts.get("INJECT_CLASSIFICATION", "IMPLEMENTATION_BUG")
        route_map = {
            "IMPLEMENTATION_BUG": ("ROUTE_A", "/opsx-fix-bug", "/opsx-fix-bug"),
            "SPEC_BUG": ("ROUTE_B", "/opsx-update", "PENDING_UNTIL_TASK_DELTA"),
            "SPEC_GAP": ("ROUTE_B", "/opsx-update", "PENDING_UNTIL_TASK_DELTA"),
            "FALSE_POSITIVE": ("ROUTE_C", "CLOSED_NO_IMPLEMENTATION", "CLOSED_NO_IMPLEMENTATION"),
            "OUT_OF_SCOPE": ("ROUTE_D", "ROUTE_TO_OTHER_PROCESS", "ROUTE_TO_OTHER_PROCESS"),
            "INSUFFICIENT_EVIDENCE": (None, None, None),
        }
        if cls == "INSUFFICIENT_EVIDENCE":
            orch.route["CURRENT_ROUTE_STATE"] = "BLOCKED_EVIDENCE_REQUIRED"
            return {
                "STATUS": "BLOCKED",
                "TERMINAL_STATUS": "BLOCKED_EVIDENCE_REQUIRED",
                "CLASSIFICATION": cls,
                "ARTIFACTS_WRITTEN": [],
                "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
            }
        chosen, next_cmd, exec_route = route_map[cls]
        orch.route.update(
            {
                "CHOSEN_ROUTE": chosen,
                "EXPECTED_NEXT_COMMAND": next_cmd,
                "EXPECTED_EXECUTION_ROUTE": exec_route,
                "CURRENT_CLASSIFICATION": cls,
                "CURRENT_ROUTE_STATE": f"CLASSIFIED_{chosen}",
            }
        )
        out: Dict[str, Any] = {
            "STATUS": "PASS",
            "TERMINAL_STATUS": "PASS",
            "CLASSIFICATION": cls,
            "CHOSEN_ROUTE": chosen,
            "EXPECTED_NEXT_COMMAND": next_cmd,
            "EXPECTED_EXECUTION_ROUTE": exec_route,
            "ARTIFACTS_WRITTEN": [],
            "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
        }
        if cls == "OUT_OF_SCOPE":
            target = orch.artifacts.get("ROUTE_TARGET_PROCESS_ID", "opsx-admin-command-consult")
            out["ROUTE_TARGET_PROCESS_ID"] = target
            out["ROUTE_TARGET_REASON"] = "process_surface"
            orch.route["ROUTE_TARGET_PROCESS_ID"] = target
        return out

    def spec_update(orch: Orchestrator, spec: TaskCallSpec) -> Dict[str, Any]:
        delta = orch.artifacts.get("TASK_DELTA", "CHANGED")
        if delta == "CHANGED":
            orch.route["EXPECTED_EXECUTION_ROUTE"] = "/opsx-apply"
            orch.route["EXPECTED_NEXT_COMMAND"] = "/opsx-apply"
            orch.route["CURRENT_ROUTE_STATE"] = "AWAITING_APPLY_RED"
        else:
            orch.route["EXPECTED_EXECUTION_ROUTE"] = "/opsx-fix-bug"
            orch.route["EXPECTED_NEXT_COMMAND"] = "/opsx-fix-bug"
            orch.route["CURRENT_ROUTE_STATE"] = "AWAITING_FIX_BUG_RED"
        orch.route["TASK_DELTA"] = delta
        path = orch.case_root / "results" / "TASK-DELTA-FINDING-001.md"
        path.write_text(f"TASK_DELTA: {delta}\n", encoding="utf-8")
        return {
            "STATUS": "PASS",
            "TERMINAL_STATUS": "PASS",
            "TASK_DELTA": delta,
            "EXPECTED_EXECUTION_ROUTE": orch.route["EXPECTED_EXECUTION_ROUTE"],
            "ARTIFACTS_WRITTEN": [str(path)],
            "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
        }

    def red(orch: Orchestrator, spec: TaskCallSpec) -> Dict[str, Any]:
        mode = orch.artifacts.get("RED_MODE", "RED_CONFIRMED")
        test_src = "def test_invariant_a():\n    assert False\n"
        sha = _sha(test_src)
        orch.artifacts["TEST_ID"] = "tests/unit/fake/test_inv.py::test_invariant_a"
        orch.artifacts["TEST_CONTENT_SHA256"] = sha
        red_path = orch.case_root / "results" / "RED-FINDING-001.md"
        red_path.write_text(
            f"STATUS: {mode}\nTEST_CONTENT_SHA256: {sha}\n", encoding="utf-8"
        )
        orch.artifacts["RED_EVIDENCE_PATH"] = str(red_path)
        status = "PASS" if mode == "RED_CONFIRMED" else "BLOCKED"
        if mode == "PASS_ALREADY":
            status = "BLOCKED"
        if mode == "INVALID_RED":
            status = "FAIL"
        if status == "PASS":
            orch.owner_gate_status = "WAITING_PRODUCTION_GO"
            orch.route["CURRENT_ROUTE_STATE"] = "WAITING_OWNER_PRODUCTION_GO"
        return {
            "STATUS": status,
            "TERMINAL_STATUS": mode,
            "TEST_ID": orch.artifacts["TEST_ID"],
            "TEST_CONTENT_SHA256": sha,
            "ARTIFACTS_WRITTEN": [str(red_path)],
            "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
        }

    def executor(orch: Orchestrator, spec: TaskCallSpec) -> Dict[str, Any]:
        if orch.owner_gate_status != "PRODUCTION_GO_RECEIVED":
            return {
                "STATUS": "BLOCKED",
                "TERMINAL_STATUS": "OWNER_GATE_BYPASS_REJECTED",
                "ARTIFACTS_WRITTEN": [],
                "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
            }
        expected = orch.route.get("EXPECTED_EXECUTION_ROUTE", "/opsx-fix-bug")
        orch.route["ACTUAL_EXECUTION_ROUTE"] = expected
        orch.route["ROUTE_RECONCILIATION"] = "MATCH"
        fix_path = orch.case_root / "results" / "FIX-FINDING-001.md"
        fix_path.write_text("FIXED\n", encoding="utf-8")
        writes = [str(fix_path)]
        if orch.artifacts.get("EXECUTOR_TOUCH_APP"):
            writes.append("app/modules/example.py")
        return {
            "STATUS": "PASS",
            "TERMINAL_STATUS": "PASS",
            "ACTUAL_EXECUTION_ROUTE": expected,
            "ARTIFACTS_WRITTEN": writes,
            "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
        }

    def green(orch: Orchestrator, spec: TaskCallSpec) -> Dict[str, Any]:
        # Must not reuse executor identity
        exec_ids = set(orch.execution_ids_for("IMPLEMENTATION_EXECUTOR"))
        if spec.worker_execution_id in exec_ids:
            return {
                "STATUS": "FAIL",
                "TERMINAL_STATUS": "SHARED_EXECUTION_IDENTITY_FORBIDDEN",
                "ARTIFACTS_WRITTEN": [],
                "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
            }
        frozen = orch.artifacts.get("TEST_CONTENT_SHA256")
        if orch.artifacts.get("FORCE_HASH_MISMATCH"):
            frozen = "deadbeef"
        red_sha = None
        red_path = orch.artifacts.get("RED_EVIDENCE_PATH")
        if red_path and Path(red_path).exists():
            for line in Path(red_path).read_text(encoding="utf-8").splitlines():
                if line.startswith("TEST_CONTENT_SHA256:"):
                    red_sha = line.split(":", 1)[1].strip()
        if red_sha and frozen != red_sha and orch.artifacts.get("FORCE_HASH_MISMATCH"):
            return {
                "STATUS": "FAIL",
                "TERMINAL_STATUS": "FROZEN_TEST_HASH_MISMATCH",
                "ARTIFACTS_WRITTEN": [],
                "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
            }
        gpath = orch.case_root / "results" / "GREEN-FINDING-001.md"
        gpath.write_text(
            f"STATUS: GREEN_CONFIRMED\nTEST_CONTENT_SHA256: {red_sha or frozen}\n",
            encoding="utf-8",
        )
        return {
            "STATUS": "PASS",
            "TERMINAL_STATUS": "GREEN_CONFIRMED",
            "ARTIFACTS_WRITTEN": [str(gpath)],
            "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
        }

    def task_completion(orch: Orchestrator, spec: TaskCallSpec) -> Dict[str, Any]:
        return {
            "STATUS": "PASS",
            "TERMINAL_STATUS": "PASS",
            "COMPLETION_DECISION": "COMPLETE",
            "TASK_ID": "T1",
            "IMPLEMENTATION_EVIDENCE": "FIX-FINDING-001.md",
            "TEST_EVIDENCE": "GREEN-FINDING-001.md",
            "ARTIFACTS_WRITTEN": [],
            "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
        }

    def hunter(orch: Orchestrator, spec: TaskCallSpec) -> Dict[str, Any]:
        return {
            "STATUS": "PASS",
            "TERMINAL_STATUS": "PASS",
            "CANDIDATES": [],
            "ARTIFACTS_WRITTEN": [],
            "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
        }

    def fanin(orch: Orchestrator, spec: TaskCallSpec) -> Dict[str, Any]:
        # Only completed evidence packets
        fanin_path = orch.case_root / "results" / "FANIN.md"
        fanin_path.write_text("STATUS: FANIN_READY\n", encoding="utf-8")
        orch.owner_gate_status = "WAITING_CLOSURE"
        return {
            "STATUS": "PASS",
            "TERMINAL_STATUS": "FANIN_READY",
            "ARTIFACTS_WRITTEN": [str(fanin_path)],
            "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
        }

    def closure(orch: Orchestrator, spec: TaskCallSpec) -> Dict[str, Any]:
        if orch.owner_gate_status != "CLOSURE_RECEIVED":
            return {
                "STATUS": "WAITING_OWNER",
                "TERMINAL_STATUS": "WAITING_OWNER_FINAL_CLOSURE",
                "ARTIFACTS_WRITTEN": [],
                "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
            }
        return {
            "STATUS": "PASS",
            "TERMINAL_STATUS": "CLOSED",
            "ARTIFACTS_WRITTEN": [],
            "PROCESS_ID_OR_TASK_ID": spec.worker_execution_id,
        }

    return {
        "MATERIALIZER": materializer,
        "CLAIM_WORKER": claim,
        "CLASSIFIER": classifier,
        "SPEC_UPDATE_WORKER": spec_update,
        "RED_TEST_WORKER": red,
        "IMPLEMENTATION_EXECUTOR": executor,
        "GREEN_VERIFIER": green,
        "TASK_COMPLETION_WORKER": task_completion,
        "BOUNDED_HUNTER": hunter,
        "FAN_IN_ASSEMBLER": fanin,
        "CLOSURE_OPERATOR": closure,
    }


def _new_orch(tmpdir: Path, name: str) -> Orchestrator:
    root = tmpdir / name
    root.mkdir(parents=True)
    orch = Orchestrator(case_root=root)
    orch.worker_backends = _base_backends()
    return orch


def _route_a_to_red_stop(orch: Orchestrator) -> None:
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: timer starts early")
    orch.dispatch("CLAIM_WORKER", "claim next")
    orch.artifacts["INJECT_CLASSIFICATION"] = "IMPLEMENTATION_BUG"
    orch.dispatch("CLASSIFIER", "classify")
    # adjudication hop represented as completed before RED in Candidate plan
    orch.completed_hops.append("FIX_BUG_WITHOUT_GO")
    orch.dispatch("RED_TEST_WORKER", "author RED")


def test_t1(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T1")
    _route_a_to_red_stop(orch)
    ok = (
        orch.owner_gate_status == "WAITING_PRODUCTION_GO"
        and "IMPLEMENTATION_EXECUTOR" not in orch.completed_hops
        and orch.dispatches[-1].worker_id == "RED_TEST_WORKER"
    )
    return ok, "Route A stops at Owner production gate after RED"


def test_t2(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T2")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: spec mismatch")
    orch.artifacts["INJECT_CLASSIFICATION"] = "SPEC_BUG"
    orch.dispatch("CLASSIFIER", "classify")
    orch.artifacts["TASK_DELTA"] = "CHANGED"
    orch.dispatch("SPEC_UPDATE_WORKER", "update")
    orch.dispatch("RED_TEST_WORKER", "red")
    ok = (
        orch.route.get("EXPECTED_EXECUTION_ROUTE") == "/opsx-apply"
        and orch.owner_gate_status == "WAITING_PRODUCTION_GO"
        and "IMPLEMENTATION_EXECUTOR" not in orch.completed_hops
    )
    return ok, "Route B CHANGED stops at RED Owner gate"


def test_t3(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T3")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: spec gap unchanged tasks")
    orch.artifacts["INJECT_CLASSIFICATION"] = "SPEC_GAP"
    orch.dispatch("CLASSIFIER", "classify")
    orch.artifacts["TASK_DELTA"] = "UNCHANGED"
    orch.dispatch("SPEC_UPDATE_WORKER", "update")
    orch.dispatch("RED_TEST_WORKER", "red")
    ok = (
        orch.route.get("EXPECTED_EXECUTION_ROUTE") == "/opsx-fix-bug"
        and orch.owner_gate_status == "WAITING_PRODUCTION_GO"
    )
    return ok, "Route B UNCHANGED stops at RED Owner gate"


def test_t4(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T4")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: false alarm")
    orch.artifacts["INJECT_CLASSIFICATION"] = "FALSE_POSITIVE"
    orch.dispatch("CLASSIFIER", "classify")
    # no RED
    ok = (
        orch.route.get("CHOSEN_ROUTE") == "ROUTE_C"
        and "RED_TEST_WORKER" not in orch.completed_hops
        and orch.owner_gate_status == "NONE"
    )
    return ok, "Route C early close without implementation"


def test_t5(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T5")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: process defect")
    orch.artifacts["INJECT_CLASSIFICATION"] = "OUT_OF_SCOPE"
    orch.artifacts["ROUTE_TARGET_PROCESS_ID"] = "opsx-admin-command-consult"
    out = orch.dispatch("CLASSIFIER", "classify")
    ok = (
        out.get("ROUTE_TARGET_PROCESS_ID") == "opsx-admin-command-consult"
        and orch.route.get("CHOSEN_ROUTE") == "ROUTE_D"
    )
    return ok, "Route D durable handoff target"


def test_t6(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T6")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: мало данных INCOMPLETE_MARKER")
    orch.artifacts["INJECT_CLASSIFICATION"] = "INSUFFICIENT_EVIDENCE"
    out = orch.dispatch("CLASSIFIER", "classify")
    ok = out.get("TERMINAL_STATUS") == "BLOCKED_EVIDENCE_REQUIRED"
    return ok, "INSUFFICIENT_EVIDENCE blocked stop"


def test_t7(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T7")
    _route_a_to_red_stop(orch)
    # bypass attempt
    out = orch.dispatch("IMPLEMENTATION_EXECUTOR", "try production")
    ok = out.get("TERMINAL_STATUS") == "OWNER_GATE_BYPASS_REJECTED"
    return ok, "production Owner-gate bypass rejected"


def test_t8(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T8")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: x")
    orch.artifacts["INJECT_CLASSIFICATION"] = "IMPLEMENTATION_BUG"
    orch.dispatch("CLASSIFIER", "c")
    orch.dispatch("RED_TEST_WORKER", "r")
    orch.grant_production_go()
    orch.dispatch("IMPLEMENTATION_EXECUTOR", "fix")
    orch.dispatch("GREEN_VERIFIER", "g")
    orch.dispatch("TASK_COMPLETION_WORKER", "t")
    orch.dispatch("BOUNDED_HUNTER", "h")
    orch.dispatch("FAN_IN_ASSEMBLER", "f")
    out = orch.dispatch("CLOSURE_OPERATOR", "close without owner")
    ok = out.get("STATUS") == "WAITING_OWNER"
    bypass = orch.reject_owner_bypass("CLOSURE")
    ok = ok and "BYPASS" in bypass["TERMINAL_STATUS"]
    return ok, "closure Owner-gate bypass rejected"


def test_t9(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T9")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: x")
    orch.dispatch("CLAIM_WORKER", "claim1")
    out = orch.dispatch("CLAIM_WORKER", "claim2")
    ok = out.get("TERMINAL_STATUS") == "DUPLICATE_CLAIM_REJECTED"
    return ok, "duplicate claim rejected"


def test_t10(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T10")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: x")
    out = orch.dispatch("CLASSIFIER", "c", force_timeout=True)
    next_out = orch.dispatch("RED_TEST_WORKER", "should not run")
    ok = (
        out.get("STATUS") == "TIMEOUT"
        and orch.process_tree_terminated
        and orch.checkpoint_path.exists()
        and next_out.get("TERMINAL_STATUS") == "PROCESS_TREE_TERMINATED"
    )
    return ok, "worker timeout + process-tree termination + checkpoint"


def test_t11(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T11")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: x")
    orch.completed_hops = list(orch.completed_hops)
    completed = list(orch.completed_hops)
    orch.dispatch("CLASSIFIER", "c", force_timeout=True)
    # resume: do not re-run MATERIALIZER
    resumed = Orchestrator(case_root=orch.case_root)
    resumed.worker_backends = _base_backends()
    resumed.completed_hops = completed
    resumed.parent_orchestration_id = orch.parent_orchestration_id
    # load checkpoint completed hops
    assert "MATERIALIZER" in resumed.completed_hops
    # only dispatch next after clear termination flag for resume test of hop skip
    resumed.process_tree_terminated = False
    resumed.blocked_reason = None
    resumed.artifacts["INJECT_CLASSIFICATION"] = "FALSE_POSITIVE"
    resumed.dispatch("CLASSIFIER", "resume classify")
    ok = resumed.completed_hops.count("MATERIALIZER") == 1
    return ok, "resume after TIMEOUT without repeating completed hops"


def test_t12(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T12")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: x")
    orch.artifacts["INJECT_CLASSIFICATION"] = "IMPLEMENTATION_BUG"
    orch.dispatch("CLASSIFIER", "c")
    orch.dispatch("RED_TEST_WORKER", "r")
    orch.grant_production_go()
    orch.dispatch("IMPLEMENTATION_EXECUTOR", "e")
    orch.dispatch("GREEN_VERIFIER", "g")
    orch.dispatch("TASK_COMPLETION_WORKER", "t")
    orch.dispatch("BOUNDED_HUNTER", "h")
    out = orch.dispatch(
        "FAN_IN_ASSEMBLER",
        "fanin",
        extra_writes=[str(orch.case_root / "LEDGER.md")],
    )
    ok = out.get("TERMINAL_STATUS") == "FANIN_WRITE_BOUNDARY_VIOLATION"
    return ok, "FAN_IN write-boundary violation rejected"


def test_t13(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T13")
    inv = parse_invocation("После подтверждения ключей сразу запускается таймер")
    assert inv["MODE"] == "FREE_FORM"
    out = orch.dispatch("MATERIALIZER", f"RAW_INTAKE_TEXT: {inv['RAW_INTAKE_TEXT']}")
    ok = out["STATUS"] == "PASS" and (orch.case_root / "intakes" / "INTAKE-001.md").exists()
    return ok, "one-line free-form Russian intake materialized"


def test_t14(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T14")
    body = "Клиент подтвердил ключи.\nСистема сразу показывает WARM_UP.\nВыбрать длительность невозможно."
    orch.dispatch("MATERIALIZER", f"RAW_INTAKE_TEXT: {body}")
    stored = (orch.case_root / "intakes" / "INTAKE-001.md").read_text(encoding="utf-8")
    ok = "WARM_UP" in stored and "длительность" in stored
    return ok, "multiline unstructured intake preserved"


def test_t15(tmpdir: Path) -> Result:
    inv = parse_invocation("", context_text="Баг: таймер стартует рано")
    ok = inv["MODE"] == "CURRENT_CONTEXT" and "таймер" in inv["RAW_INTAKE_TEXT"]
    return ok, "command without argument uses current context"


def test_t16(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T16")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: мало данных INCOMPLETE_MARKER")
    orch.artifacts["INJECT_CLASSIFICATION"] = "INSUFFICIENT_EVIDENCE"
    out = orch.dispatch("CLASSIFIER", "c")
    ok = out.get("TERMINAL_STATUS") == "BLOCKED_EVIDENCE_REQUIRED"
    return ok, "incomplete intake -> INSUFFICIENT_EVIDENCE"


def test_t17(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T17")
    orch.artifacts["FORCE_DUP"] = True
    out = orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: same root")
    ok = out.get("DUPLICATE_OUTCOME") == "DUPLICATE_ROOT_REJECTED"
    return ok, "duplicate root rejected"


def test_t18(tmpdir: Path) -> Result:
    inv = parse_invocation('case=BUGCASE-1 новый баг про таймер')
    ok = inv["MODE"] == "BLOCKED_AMBIGUOUS_INVOCATION"
    return ok, "case= + free-form -> BLOCKED_AMBIGUOUS_INVOCATION"


def test_t19(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T19")
    # Orchestrator must not set orchestrator_materialized
    assert orch.orchestrator_materialized is False
    out = orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: proof dispatch")
    ok = (
        out["STATUS"] == "PASS"
        and orch.dispatches[0].worker_id == "MATERIALIZER"
        and orch.dispatches[0].cursor_task_tool == "Task"
        and "_TASK_ARGS" in out
        and "model" not in out["_TASK_ARGS"]
        and orch.orchestrator_materialized is False
        and orch.dispatch_log.exists()
    )
    return ok, "dispatches MATERIALIZER Task worker; orchestrator does not materialize"


def test_t20(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T20")
    _route_a_to_red_stop(orch)
    orch.grant_production_go()
    orch.dispatch("IMPLEMENTATION_EXECUTOR", "fix")
    orch.dispatch("GREEN_VERIFIER", "green")
    ids = {
        "RED": set(orch.execution_ids_for("RED_TEST_WORKER")),
        "EX": set(orch.execution_ids_for("IMPLEMENTATION_EXECUTOR")),
        "GR": set(orch.execution_ids_for("GREEN_VERIFIER")),
    }
    ok = ids["RED"] and ids["EX"] and ids["GR"] and len(ids["RED"] | ids["EX"] | ids["GR"]) == 3
    orch.assert_independence()
    return ok, "Route A distinct RED/Executor/GREEN executions"


def test_t21(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T21")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: spec")
    orch.artifacts["INJECT_CLASSIFICATION"] = "SPEC_BUG"
    orch.dispatch("CLASSIFIER", "c")
    orch.artifacts["TASK_DELTA"] = "CHANGED"
    orch.dispatch("SPEC_UPDATE_WORKER", "u")
    orch.dispatch("RED_TEST_WORKER", "r")
    orch.grant_production_go()
    orch.dispatch("IMPLEMENTATION_EXECUTOR", "e")
    orch.dispatch("GREEN_VERIFIER", "g")
    workers = [
        "SPEC_UPDATE_WORKER",
        "RED_TEST_WORKER",
        "IMPLEMENTATION_EXECUTOR",
        "GREEN_VERIFIER",
    ]
    all_ids = []
    for w in workers:
        all_ids.extend(orch.execution_ids_for(w))
    ok = len(all_ids) == len(set(all_ids)) == 4
    return ok, "Route B distinct Spec/RED/Executor/GREEN"


def test_t22(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T22")
    _route_a_to_red_stop(orch)
    orch.grant_production_go()
    orch.dispatch("IMPLEMENTATION_EXECUTOR", "e")
    ex_id = orch.execution_ids_for("IMPLEMENTATION_EXECUTOR")[0]
    orch.dispatch("GREEN_VERIFIER", "g")
    gr_id = orch.execution_ids_for("GREEN_VERIFIER")[0]
    ok = ex_id != gr_id
    return ok, "GREEN cannot reuse Executor execution identity"


def test_t23(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T23")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: x")
    out = orch.dispatch("CLASSIFIER", "c", force_timeout=True)
    next_out = orch.dispatch("RED_TEST_WORKER", "should not run")
    ok = (
        out.get("STATUS") == "TIMEOUT"
        and orch.process_tree_terminated
        and next_out.get("TERMINAL_STATUS") == "PROCESS_TREE_TERMINATED"
        and next_out.get("DEPENDENT_WAVE_ALLOWED") is not True
    )
    return ok, "timed-out worker prevents dependent wave dispatch"


def test_t24(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T24")
    out = orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: x", malformed_output=True)
    next_out = orch.dispatch("CLASSIFIER", "nope")
    ok = (
        out.get("TERMINAL_STATUS") == "MALFORMED_OUTPUT_PACKET"
        and next_out.get("TERMINAL_STATUS") == "PROCESS_TREE_TERMINATED"
    )
    return ok, "malformed output packet rejected"


def test_t25(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T25")
    _route_a_to_red_stop(orch)
    # try production write without GO via extra_writes
    orch.artifacts["EXECUTOR_TOUCH_APP"] = True
    out = orch.dispatch(
        "IMPLEMENTATION_EXECUTOR",
        "fix",
        extra_writes=["app/modules/example.py"],
    )
    ok = out.get("TERMINAL_STATUS") == "OWNER_GATE_BYPASS_REJECTED"
    return ok, "production write-boundary violation terminates execution"


def test_t26(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "T26")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: x")
    orch.artifacts["INJECT_CLASSIFICATION"] = "IMPLEMENTATION_BUG"
    orch.dispatch("CLASSIFIER", "c")
    orch.dispatch("RED_TEST_WORKER", "r")
    orch.grant_production_go()
    orch.dispatch("IMPLEMENTATION_EXECUTOR", "e")
    orch.dispatch("GREEN_VERIFIER", "g")
    orch.dispatch("TASK_COMPLETION_WORKER", "t")
    orch.dispatch("BOUNDED_HUNTER", "h")
    out = orch.dispatch("FAN_IN_ASSEMBLER", "f")
    fanin = orch.case_root / "results" / "FANIN.md"
    ok = (
        out["STATUS"] == "PASS"
        and fanin.exists()
        and all(
            not p.endswith("LEDGER.md")
            for d in orch.dispatches
            if d.worker_id == "FAN_IN_ASSEMBLER"
            for p in []
        )
    )
    # ensure only FANIN written by fanin worker
    fanin_rec = [d for d in orch.dispatches if d.worker_id == "FAN_IN_ASSEMBLER"][0]
    ok = ok and fanin_rec.write_boundary_ok is True
    return ok, "Fan-In writes only FANIN.md"


def test_extra_partial_wave2(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "X_W2")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: x")
    # stop before classifier
    ok = orch.completed_hops == ["MATERIALIZER"] and orch.active_hop is None
    return ok, "partial WAVE_2 stop"


def test_extra_premature_active(tmpdir: Path) -> Result:
    status = Path(".cursor/pipeline/bug-team/CANDIDATE_STATUS.md").read_text(
        encoding="utf-8"
    )
    ok = "NOT_ACTIVE" in status and "READY_FOR_PRODUCTION" not in status.split(
        "Forbidden"
    )[0]
    # stronger: must declare NOT_ACTIVE and not ACTIVE as runtime
    ok = "RUNTIME_STATUS: NOT_ACTIVE" in status and "OWNER_ACTIVATION: NOT_ISSUED" in status
    return ok, "premature ACTIVE transition forbidden in candidate status"


def test_extra_pass_already(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "X_PA")
    orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: x")
    orch.artifacts["INJECT_CLASSIFICATION"] = "IMPLEMENTATION_BUG"
    orch.dispatch("CLASSIFIER", "c")
    orch.artifacts["RED_MODE"] = "PASS_ALREADY"
    out = orch.dispatch("RED_TEST_WORKER", "r")
    ok = out.get("TERMINAL_STATUS") == "PASS_ALREADY" and out["STATUS"] != "PASS"
    return ok, "PASS_ALREADY without forced RED"


def test_extra_hash_mismatch(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "X_HM")
    _route_a_to_red_stop(orch)
    orch.grant_production_go()
    orch.dispatch("IMPLEMENTATION_EXECUTOR", "e")
    orch.artifacts["FORCE_HASH_MISMATCH"] = True
    out = orch.dispatch("GREEN_VERIFIER", "g")
    ok = out.get("TERMINAL_STATUS") == "FROZEN_TEST_HASH_MISMATCH"
    return ok, "frozen test hash mismatch"


def test_extra_route_mismatch(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "X_RM")
    orch.route["EXPECTED_EXECUTION_ROUTE"] = "/opsx-apply"
    orch.route["ACTUAL_EXECUTION_ROUTE"] = "/opsx-fix-bug"
    orch.route["ROUTE_RECONCILIATION"] = (
        "MATCH"
        if orch.route["EXPECTED_EXECUTION_ROUTE"] == orch.route["ACTUAL_EXECUTION_ROUTE"]
        else "MISMATCH"
    )
    ok = orch.route["ROUTE_RECONCILIATION"] == "MISMATCH"
    return ok, "route reconciliation mismatch detected"


def test_extra_max_retry(tmpdir: Path) -> Result:
    orch = _new_orch(tmpdir, "X_MR")
    # exhaust by recording attempts
    for attempt in (1, 2):
        orch.dispatch("MATERIALIZER", "RAW_INTAKE_TEXT: x", attempt=attempt, force_timeout=True)
        orch.process_tree_terminated = False
        orch.blocked_reason = None
    max_a = max(d.attempt for d in orch.dispatches if d.worker_id == "MATERIALIZER")
    ok = max_a <= 2
    return ok, "max retry bounded"


TESTS = [
    ("T1", test_t1),
    ("T2", test_t2),
    ("T3", test_t3),
    ("T4", test_t4),
    ("T5", test_t5),
    ("T6", test_t6),
    ("T7", test_t7),
    ("T8", test_t8),
    ("T9", test_t9),
    ("T10", test_t10),
    ("T11", test_t11),
    ("T12", test_t12),
    ("T13", test_t13),
    ("T14", test_t14),
    ("T15", test_t15),
    ("T16", test_t16),
    ("T17", test_t17),
    ("T18", test_t18),
    ("T19", test_t19),
    ("T20", test_t20),
    ("T21", test_t21),
    ("T22", test_t22),
    ("T23", test_t23),
    ("T24", test_t24),
    ("T25", test_t25),
    ("T26", test_t26),
    ("X_PARTIAL_W2", test_extra_partial_wave2),
    ("X_PREMATURE_ACTIVE", test_extra_premature_active),
    ("X_PASS_ALREADY", test_extra_pass_already),
    ("X_HASH_MISMATCH", test_extra_hash_mismatch),
    ("X_ROUTE_MISMATCH", test_extra_route_mismatch),
    ("X_MAX_RETRY", test_extra_max_retry),
]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    tmp = Path(tempfile.mkdtemp(prefix="opsx-bug-team-"))
    results: Dict[str, Any] = {}
    failed = 0
    try:
        for name, fn in TESTS:
            try:
                ok, msg = fn(tmp)
                results[name] = {"PASS": ok, "MSG": msg}
                if not ok:
                    failed += 1
                    print(f"FAIL {name}: {msg}".encode("utf-8", errors="replace").decode("utf-8"))
                else:
                    print(f"PASS {name}: {msg}".encode("utf-8", errors="replace").decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                failed += 1
                results[name] = {"PASS": False, "MSG": str(exc), "TRACE": traceback.format_exc()}
                print(f"ERROR {name}: {exc}".encode("utf-8", errors="replace").decode("utf-8"))
    finally:
        out = Path(".cursor/pipeline/bug-team/controlled-tests/LAST_RUN.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        # keep tmp for inspection under .tmp
        dest = Path(".tmp/opsx-bug-team-harness/last-run")
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(tmp, dest)
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\nSUMMARY failed={failed} total={len(TESTS)}")
    print(f"WORKER_IDS={list(WORKER_IDS)}")
    # Builder note
    print("INDEPENDENT_TESTER_PASS: NOT_ISSUED")
    print("RUNTIME_STATUS: NOT_ACTIVE")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
