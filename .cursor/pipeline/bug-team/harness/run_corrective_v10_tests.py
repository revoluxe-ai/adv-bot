# -*- coding: utf-8 -*-
"""Corrective V10 tests — authoritative execution identity validation.

Shadow only. Does not enable BUG_FAMILY_FANOUT, activate runtime, or touch
real bug cases / product files.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import execution_identity, family_fanout, orchestrator  # noqa: E402

Result = Tuple[bool, str, str]
HARNESS = Path(".tmp/opsx-bug-team-harness/corrective-v10-unit")

ORCH = "ORCH/V10-TEST"
CASE = "BUGCASE-V10-SYNTH"
FINDING = "FIND-V10-001"
BRANCH = "BR-V10-A"
AGENT_REAL = "agent-v10-real-9f3c2a1b"
WORKER = "RELATION_CLASSIFIER"


def _case(name: str) -> Path:
    p = HARNESS / name
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    (p / "team" / "packets").mkdir(parents=True, exist_ok=True)
    (p / "team" / "executions").mkdir(parents=True, exist_ok=True)
    (p / "results").mkdir(parents=True, exist_ok=True)
    return p


def _write_json(path: Path, obj: Dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    path.write_text(raw, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _packet(
    *,
    packet_id: str,
    packet_type: str,
    wex: str,
    attempt: int = 1,
    packet_generation: int = 1,
    checkpoint_generation: int = 1,
    parent: Optional[str] = None,
    orch: str = ORCH,
    case_id: str = CASE,
    finding_id: str = FINDING,
    worker_id: str = WORKER,
    status: str = "PASS",
) -> Dict[str, Any]:
    return {
        "SCHEMA_VERSION": "1",
        "PACKET_TYPE": packet_type,
        "PACKET_ID": packet_id,
        "ORCHESTRATION_ID": orch,
        "CASE_ID": case_id,
        "FINDING_ID": finding_id,
        "WORKER_ID": worker_id,
        "WORKER_EXECUTION_ID": wex,
        "ATTEMPT": attempt,
        "PACKET_GENERATION": packet_generation,
        "CHECKPOINT_GENERATION": checkpoint_generation,
        "PARENT_PACKET_ID": parent,
        "STATUS": status,
        "TERMINAL_STATUS": status,
        "PAYLOAD": {},
    }


def _checkpoint(
    *,
    active_wex: Optional[str],
    attempt: int = 1,
    cpg: int = 1,
    pkg: int = 1,
    status: str = "RUNNING",
    last_accepted: Optional[str] = None,
    superseded: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "ORCHESTRATION_ID": ORCH,
        "CASE_ID": CASE,
        "FINDING_ID": FINDING,
        "CHECKPOINT_GENERATION": cpg,
        "PACKET_GENERATION": pkg,
        "ACTIVE_STATUS": status,
        "ACTIVE_WORKER_EXECUTION_ID": active_wex,
        "ACTIVE_WORKER_ID": WORKER,
        "ACTIVE_ATTEMPT": attempt,
        "ACTIVE_PACKET_GENERATION": pkg,
        "ACTIVE_CHECKPOINT_GENERATION": cpg,
        "LAST_ACCEPTED_WEX": last_accepted,
        "SUPERSEDED_WEX": superseded or [],
        "COMPLETED_HOPS": [],
    }


def _build_valid_binding(
    case: Path,
    *,
    wex: str = "WEX/REL/V10-1",
    agent: str = AGENT_REAL,
    attempt: int = 1,
    branch_id: Any = BRANCH,
    orch: str = ORCH,
    case_id: str = CASE,
    finding_id: str = FINDING,
    mutate_identity: Optional[Callable[[Dict[str, Any]], None]] = None,
    checkpoint_override: Optional[Dict[str, Any]] = None,
    skip_dispatch: bool = False,
    identity_status: str = execution_identity.STATUS_OUTPUT_RECEIVED,
) -> Dict[str, Any]:
    """Create matching identity + dispatch + packets + checkpoint."""
    in_id = f"PKT/{wex}/IN"
    out_id = f"PKT/{wex}/OUT"
    in_path = case / "team" / "packets" / f"{execution_identity.wex_slug(wex)}.in.json"
    out_path = case / "team" / "packets" / f"{execution_identity.wex_slug(wex)}.out.json"
    cp_path = case / "team" / "CHECKPOINT.json"
    disp_path = case / "team" / "DISPATCH.jsonl"

    in_pkt = _packet(
        packet_id=in_id,
        packet_type="WORKER_INPUT",
        wex=wex,
        attempt=attempt,
        orch=orch,
        case_id=case_id,
        finding_id=finding_id,
    )
    out_pkt = _packet(
        packet_id=out_id,
        packet_type="WORKER_OUTPUT",
        wex=wex,
        attempt=attempt,
        parent=in_id,
        orch=orch,
        case_id=case_id,
        finding_id=finding_id,
    )
    in_hash = _write_json(in_path, in_pkt)
    out_hash = _write_json(out_path, out_pkt)

    cp = checkpoint_override or _checkpoint(active_wex=wex, attempt=attempt, status="RUNNING")
    _write_json(cp_path, cp)

    disp_id = execution_identity.dispatch_record_id_for(wex, attempt)
    dispatch_record = {
        "DISPATCH_RECORD_ID": disp_id,
        "ORCHESTRATION_ID": orch,
        "CASE_ID": case_id,
        "FINDING_ID": finding_id,
        "WORKER_EXECUTION_ID": wex,
        "WORKER_ID": WORKER,
        "ATTEMPT": attempt,
        "CURSOR_AGENT_ID": agent,
        "STATUS": "PASS",
        "TERMINAL_STATUS": "PASS",
    }
    if not skip_dispatch:
        disp_path.parent.mkdir(parents=True, exist_ok=True)
        with disp_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(dispatch_record, sort_keys=True, ensure_ascii=False) + "\n")
    disp_hash = execution_identity.hash_dispatch_record(dispatch_record)

    record = {
        "IDENTITY_RECORD_VERSION": execution_identity.IDENTITY_RECORD_VERSION,
        "ORCHESTRATION_ID": orch,
        "CASE_ID": case_id,
        "FINDING_ID": finding_id,
        "BRANCH_ID": branch_id,
        "WORKER_ID": WORKER,
        "WORKER_EXECUTION_ID": wex,
        "ATTEMPT": attempt,
        "CURSOR_AGENT_ID": agent,
        "CURSOR_AGENT_ID_SOURCE": "DISPATCH_RUNTIME",
        "CURSOR_AGENT_ID_RECONCILIATION": "MATCH",
        "DISPATCH_RECORD_ID": disp_id,
        "DISPATCH_LOG_PATH": str(disp_path),
        "DISPATCH_RECORD_HASH": disp_hash,
        "INPUT_PACKET_ID": in_id,
        "INPUT_PACKET_PATH": str(in_path),
        "INPUT_PACKET_HASH": in_hash,
        "INPUT_PACKET_GENERATION": 1,
        "OUTPUT_PACKET_ID": out_id,
        "OUTPUT_PACKET_PATH": str(out_path),
        "OUTPUT_PACKET_HASH": out_hash,
        "OUTPUT_PACKET_GENERATION": 1,
        "CHECKPOINT_PATH": str(cp_path),
        "CHECKPOINT_GENERATION": 1,
        "STARTED_AT": "2026-07-28T22:00:00Z",
        "FINISHED_AT": "2026-07-28T22:01:00Z",
        "IDENTITY_STATUS": identity_status,
    }
    if mutate_identity:
        mutate_identity(record)
    execution_identity.write_identity_record(case, record)
    return {
        "case": case,
        "wex": wex,
        "in_path": in_path,
        "out_path": out_path,
        "cp_path": cp_path,
        "disp_path": disp_path,
        "agent": agent,
        "branch_id": branch_id,
        "orch": orch,
        "case_id": case_id,
        "finding_id": finding_id,
        "id_path": execution_identity.identity_path(case, wex),
    }


def _validate(ctx: Dict[str, Any], **over: Any) -> execution_identity.ExecutionIdentityValidationResult:
    kwargs = {
        "identity_path": ctx["id_path"],
        "dispatch_log_path": ctx["disp_path"],
        "input_packet_path": ctx["in_path"],
        "output_packet_path": ctx["out_path"],
        "checkpoint_path": ctx["cp_path"],
        "expected_orchestration_id": ctx["orch"],
        "expected_case_id": ctx["case_id"],
        "expected_finding_id": ctx["finding_id"],
        "expected_worker_execution_id": ctx["wex"],
        "expected_branch_id": ctx["branch_id"],
        "case_root": ctx["case"],
    }
    kwargs.update(over)
    return execution_identity.validate_execution_identity(**kwargs)


# --- cases ---


def id01() -> Result:
    ctx = _build_valid_binding(_case("id01"))
    r = _validate(ctx)
    return r.VALID and r.REASON_CODE == "OK", f"valid binding -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id02() -> Result:
    ctx = _build_valid_binding(
        _case("id02"),
        mutate_identity=lambda rec: rec.update(
            {
                "CURSOR_AGENT_ID": execution_identity.PENDING,
                "IDENTITY_STATUS": execution_identity.STATUS_PENDING_DISPATCH,
            }
        ),
    )
    # reseal after mutate already done inside write — but PENDING was set before seal
    r = _validate(ctx)
    ok = (not r.VALID) and r.REASON_CODE == "CURSOR_AGENT_ID_NOT_FINALIZED"
    return ok, f"PENDING rejected -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id03() -> Result:
    ctx = _build_valid_binding(_case("id03"))
    # substitute agent in identity only (dispatch keeps real)
    rec = execution_identity.load_identity_record(ctx["id_path"])
    rec["CURSOR_AGENT_ID"] = "agent-substituted-evil"
    execution_identity.write_identity_record(ctx["case"], rec)
    r = _validate(ctx)
    ok = (not r.VALID) and r.REASON_CODE == "CURSOR_AGENT_ID_MISMATCH"
    return ok, f"substituted agent -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id04() -> Result:
    ctx = _build_valid_binding(_case("id04"), wex="WEX/REL/ORIG")
    other = "WEX/REL/OTHER"
    other_path = execution_identity.identity_path(ctx["case"], other)
    # copy identity bytes to another WEX canonical path
    other_path.write_text(ctx["id_path"].read_text(encoding="utf-8"), encoding="utf-8")
    r = execution_identity.validate_execution_identity(
        identity_path=other_path,
        dispatch_log_path=ctx["disp_path"],
        input_packet_path=ctx["in_path"],
        output_packet_path=ctx["out_path"],
        checkpoint_path=ctx["cp_path"],
        expected_orchestration_id=ORCH,
        expected_case_id=CASE,
        expected_finding_id=FINDING,
        expected_worker_execution_id=other,
        expected_branch_id=BRANCH,
        case_root=ctx["case"],
    )
    ok = (not r.VALID) and r.REASON_CODE in {
        "WORKER_EXECUTION_ID_MISMATCH",
        "IDENTITY_PATH_NON_CANONICAL",
    }
    return ok, f"copied identity -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id05() -> Result:
    ctx = _build_valid_binding(_case("id05"))
    # rewrite dispatch with different WEX
    bad = {
        "DISPATCH_RECORD_ID": "DISP/BAD",
        "ORCHESTRATION_ID": ORCH,
        "WORKER_EXECUTION_ID": "WEX/REL/DIFFERENT",
        "ATTEMPT": 1,
        "CURSOR_AGENT_ID": AGENT_REAL,
    }
    ctx["disp_path"].write_text(
        json.dumps(bad, sort_keys=True) + "\n", encoding="utf-8"
    )
    r = _validate(ctx)
    ok = (not r.VALID) and r.REASON_CODE in {
        "DISPATCH_RECORD_MISSING",
        "DISPATCH_RECORD_MISMATCH",
        "WORKER_EXECUTION_ID_MISMATCH",
    }
    return ok, f"dispatch WEX mismatch -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id06() -> Result:
    ctx = _build_valid_binding(_case("id06"))
    r = _validate(ctx, expected_orchestration_id="ORCH/OTHER")
    ok = (not r.VALID) and r.REASON_CODE == "ORCHESTRATION_ID_MISMATCH"
    return ok, f"orch mismatch -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id07() -> Result:
    ctx = _build_valid_binding(_case("id07"))
    r = _validate(ctx, expected_case_id="BUGCASE-OTHER")
    ok = (not r.VALID) and r.REASON_CODE == "CASE_ID_MISMATCH"
    return ok, f"case mismatch -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id08() -> Result:
    ctx = _build_valid_binding(_case("id08"))
    r = _validate(ctx, expected_finding_id="FIND-OTHER")
    ok = (not r.VALID) and r.REASON_CODE == "FINDING_ID_MISMATCH"
    return ok, f"finding mismatch -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id09() -> Result:
    ctx = _build_valid_binding(_case("id09"))
    r = _validate(ctx, expected_branch_id="BR-OTHER")
    ok = (not r.VALID) and r.REASON_CODE == "BRANCH_ID_MISMATCH"
    return ok, f"branch mismatch -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id10() -> Result:
    ctx = _build_valid_binding(_case("id10"))
    rec = execution_identity.load_identity_record(ctx["id_path"])
    rec["INPUT_PACKET_HASH"] = "0" * 64
    execution_identity.write_identity_record(ctx["case"], rec)
    r = _validate(ctx)
    ok = (not r.VALID) and r.REASON_CODE == "INPUT_PACKET_MISMATCH"
    return ok, f"input hash mismatch -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id11() -> Result:
    ctx = _build_valid_binding(_case("id11"))
    rec = execution_identity.load_identity_record(ctx["id_path"])
    rec["OUTPUT_PACKET_ID"] = "PKT/WRONG/OUT"
    execution_identity.write_identity_record(ctx["case"], rec)
    r = _validate(ctx)
    ok = (not r.VALID) and r.REASON_CODE == "OUTPUT_PACKET_MISMATCH"
    return ok, f"output id mismatch -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id12() -> Result:
    ctx = _build_valid_binding(_case("id12"))
    out = json.loads(ctx["out_path"].read_text(encoding="utf-8"))
    out["PARENT_PACKET_ID"] = "PKT/NOT/THE/INPUT"
    _write_json(ctx["out_path"], out)
    # refresh output hash in identity to isolate parent check
    rec = execution_identity.load_identity_record(ctx["id_path"])
    rec["OUTPUT_PACKET_HASH"] = hashlib.sha256(ctx["out_path"].read_bytes()).hexdigest()
    execution_identity.write_identity_record(ctx["case"], rec)
    r = _validate(ctx)
    ok = (not r.VALID) and r.REASON_CODE == "PACKET_PARENT_MISMATCH"
    return ok, f"parent mismatch -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id13() -> Result:
    ctx = _build_valid_binding(_case("id13"))
    rec = execution_identity.load_identity_record(ctx["id_path"])
    rec["DISPATCH_RECORD_HASH"] = "f" * 64
    execution_identity.write_identity_record(ctx["case"], rec)
    r = _validate(ctx)
    ok = (not r.VALID) and r.REASON_CODE == "DISPATCH_RECORD_MISMATCH"
    return ok, f"dispatch hash mismatch -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id14() -> Result:
    ctx = _build_valid_binding(_case("id14"), attempt=1)
    rec = execution_identity.load_identity_record(ctx["id_path"])
    rec["ATTEMPT"] = 9
    execution_identity.write_identity_record(ctx["case"], rec)
    r = _validate(ctx)
    ok = (not r.VALID) and r.REASON_CODE == "ATTEMPT_MISMATCH"
    return ok, f"attempt mismatch -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id15() -> Result:
    ctx = _build_valid_binding(_case("id15"))
    # Running hop with mismatched ACTIVE_CHECKPOINT_GENERATION
    cp = _checkpoint(active_wex=ctx["wex"], attempt=1, cpg=1, status="RUNNING")
    cp["ACTIVE_CHECKPOINT_GENERATION"] = 99
    _write_json(ctx["cp_path"], cp)
    rec = execution_identity.load_identity_record(ctx["id_path"])
    rec["CHECKPOINT_GENERATION"] = 1
    execution_identity.write_identity_record(ctx["case"], rec)
    r = _validate(ctx)
    ok = (not r.VALID) and r.REASON_CODE == "GENERATION_MISMATCH"
    return ok, f"checkpoint gen mismatch -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id16() -> Result:
    """Copied identity from previous retry must not authorize attempt 2."""
    case = _case("id16")
    wex1 = "WEX/REL/RETRY-1"
    wex2 = "WEX/REL/RETRY-2"
    ctx1 = _build_valid_binding(case, wex=wex1, attempt=1, agent="agent-attempt-1")
    # Now active is attempt 2 / wex2
    ctx2 = _build_valid_binding(
        case,
        wex=wex2,
        attempt=2,
        agent="agent-attempt-2",
        checkpoint_override=_checkpoint(
            active_wex=wex2,
            attempt=2,
            status="RUNNING",
            superseded=[wex1],
        ),
    )
    # Copy attempt-1 identity onto wex2 path (wrong retry identity)
    ctx2["id_path"].write_text(ctx1["id_path"].read_text(encoding="utf-8"), encoding="utf-8")
    r = execution_identity.validate_execution_identity(
        identity_path=ctx2["id_path"],
        dispatch_log_path=ctx2["disp_path"],
        input_packet_path=ctx2["in_path"],
        output_packet_path=ctx2["out_path"],
        checkpoint_path=ctx2["cp_path"],
        expected_orchestration_id=ORCH,
        expected_case_id=CASE,
        expected_finding_id=FINDING,
        expected_worker_execution_id=wex2,
        expected_branch_id=BRANCH,
        case_root=case,
    )
    ok = (not r.VALID) and r.REASON_CODE in {
        "WORKER_EXECUTION_ID_MISMATCH",
        "IDENTITY_PATH_NON_CANONICAL",
        "ATTEMPT_MISMATCH",
        "IDENTITY_SUPERSEDED",
        "CURSOR_AGENT_ID_MISMATCH",
        "DISPATCH_RECORD_MISMATCH",
        "INPUT_PACKET_MISMATCH",
        "OUTPUT_PACKET_MISMATCH",
    }
    return ok, f"prior retry identity rejected -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id17() -> Result:
    """Late superseded output with formerly valid identity."""
    ctx = _build_valid_binding(_case("id17"), wex="WEX/REL/OLD")
    # Mark validated then supersede
    execution_identity.mark_identity_validated(ctx["case"], ctx["wex"])
    ctx["id_path"] = execution_identity.identity_path(ctx["case"], ctx["wex"])
    cp = _checkpoint(
        active_wex="WEX/REL/NEW",
        attempt=2,
        status="RUNNING",
        last_accepted="WEX/REL/NEW",
        superseded=[ctx["wex"]],
    )
    _write_json(ctx["cp_path"], cp)
    r = _validate(ctx)
    ok = (not r.VALID) and r.REASON_CODE in {"IDENTITY_SUPERSEDED", "IDENTITY_STALE"}
    return ok, f"superseded late output -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id18() -> Result:
    ctx = _build_valid_binding(_case("id18"))
    # Modify bytes after hash without resealing
    text = ctx["id_path"].read_text(encoding="utf-8")
    obj = json.loads(text)
    obj["FINDING_ID"] = "FIND-TAMPERED"
    # keep old IDENTITY_RECORD_HASH / HOST_SIGNATURE
    ctx["id_path"].write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    r = _validate(ctx)
    ok = (not r.VALID) and r.REASON_CODE == "IDENTITY_RECORD_HASH_MISMATCH"
    return ok, f"tampered identity -> {r.REASON_CODE}", "RUNTIME_UNIT"


def id19() -> Result:
    """Output PASS but identity invalid -> orchestration does not advance."""
    case = _case("id19")
    ctx = _build_valid_binding(
        case,
        mutate_identity=lambda rec: rec.update({"CURSOR_AGENT_ID": execution_identity.PENDING}),
    )
    orch = orchestrator.OrchestratorRuntime(
        case_root=case, orchestration_id=ORCH, execution_mode="REVIEW_PROOF_ONLY", proof_root=case
    )
    orch.checkpoint_path = ctx["cp_path"]
    orch.dispatch_path = ctx["disp_path"]
    cpg_before = json.loads(ctx["cp_path"].read_text(encoding="utf-8")).get(
        "CHECKPOINT_GENERATION", 1
    )
    gate = orch.require_execution_identity(
        worker_execution_id=ctx["wex"],
        case_id=CASE,
        finding_id=FINDING,
        input_packet_path=ctx["in_path"],
        output_packet_path=ctx["out_path"],
        branch_id=BRANCH,
    )
    cpg_after = json.loads(ctx["cp_path"].read_text(encoding="utf-8")).get(
        "CHECKPOINT_GENERATION", 1
    )
    ok = (
        gate.get("VALID") is False
        and orch.blocked_reason is not None
        and cpg_before == cpg_after
        and "BLOCKED_EXECUTION_IDENTITY" in str(orch.blocked_reason)
    )
    return ok, f"orch blocked without advance -> {gate.get('REASON_CODE')}", "RUNTIME_UNIT"


def id20() -> Result:
    """Valid identity permits dependent transition gate."""
    ctx = _build_valid_binding(_case("id20"))
    execution_identity.mark_identity_validated(ctx["case"], ctx["wex"])
    ctx["id_path"] = execution_identity.identity_path(ctx["case"], ctx["wex"])
    orch = orchestrator.OrchestratorRuntime(
        case_root=ctx["case"],
        orchestration_id=ORCH,
        execution_mode="REVIEW_PROOF_ONLY",
        proof_root=ctx["case"],
    )
    orch.checkpoint_path = ctx["cp_path"]
    orch.dispatch_path = ctx["disp_path"]
    gate = orch.require_execution_identity(
        worker_execution_id=ctx["wex"],
        case_id=CASE,
        finding_id=FINDING,
        input_packet_path=ctx["in_path"],
        output_packet_path=ctx["out_path"],
        branch_id=BRANCH,
    )
    # Family worker gate also passes
    fam = family_fanout.assert_family_worker_identity_gate(
        case_root=ctx["case"],
        worker_id=WORKER,
        worker_execution_id=ctx["wex"],
        orchestration_id=ORCH,
        case_id=CASE,
        finding_id=FINDING,
        input_packet_path=ctx["in_path"],
        output_packet_path=ctx["out_path"],
        checkpoint_path=ctx["cp_path"],
        branch_id=BRANCH,
    )
    ok = gate.get("VALID") is True and fam.get("VALID") is True and orch.blocked_reason is None
    return ok, "valid identity permits dependent transition", "RUNTIME_UNIT"


def id_v9_missing_output() -> Result:
    """Regression: targeted-rerun ID_MISSING_OUTPUT must stay closed."""
    case = _case("id_missing_out")
    execution_identity.create_pending_identity(
        case, worker_execution_id="WEX/REL/MISS", input_packet_id="IN-1"
    )
    # Manually finalize-like without output — write agent but no OUTPUT_PACKET_ID
    path = execution_identity.identity_path(case, "WEX/REL/MISS")
    obj = execution_identity.load_identity_record(path)
    obj["CURSOR_AGENT_ID"] = AGENT_REAL
    obj["CURSOR_AGENT_ID_SOURCE"] = "DISPATCH_RUNTIME"
    obj["CURSOR_AGENT_ID_RECONCILIATION"] = "MATCH"
    obj["OUTPUT_PACKET_ID"] = None
    execution_identity.write_identity_record(case, obj)
    try:
        execution_identity.validate_identity(case, "WEX/REL/MISS")
        return False, "should reject missing OUTPUT_PACKET_ID", "RUNTIME_UNIT"
    except execution_identity.ExecutionIdentityError as exc:
        ok = exc.code == "BLOCKED_EXECUTION_IDENTITY_NOT_FINALIZED"
        return ok, "ID_MISSING_OUTPUT closed", "RUNTIME_UNIT"


def pbh006_compat() -> Result:
    required = [
        "RELATION_CLASSIFIER",
        "BRANCH_CLASSIFIER",
        "RED_WORKER",
        "IMPLEMENTATION_WORKER",
        "GREEN_WORKER",
        "INTEGRATION_OPERATOR",
        "FAMILY_FAN_IN_ASSEMBLER",
        "FAMILY_LEARNING_WORKER",
    ]
    ok = all(family_fanout.family_worker_requires_validated_identity(w) for w in required)
    return ok, "PBH-006 family workers require validated identity", "RUNTIME_UNIT"


CASES: List[Tuple[str, Callable[[], Result]]] = [
    ("V10-ID-01", id01),
    ("V10-ID-02", id02),
    ("V10-ID-03", id03),
    ("V10-ID-04", id04),
    ("V10-ID-05", id05),
    ("V10-ID-06", id06),
    ("V10-ID-07", id07),
    ("V10-ID-08", id08),
    ("V10-ID-09", id09),
    ("V10-ID-10", id10),
    ("V10-ID-11", id11),
    ("V10-ID-12", id12),
    ("V10-ID-13", id13),
    ("V10-ID-14", id14),
    ("V10-ID-15", id15),
    ("V10-ID-16", id16),
    ("V10-ID-17", id17),
    ("V10-ID-18", id18),
    ("V10-ID-19", id19),
    ("V10-ID-20", id20),
    ("V10-ID-MISSING-OUTPUT", id_v9_missing_output),
    ("V10-PBH006-COMPAT", pbh006_compat),
]


def main() -> int:
    results: List[Dict[str, Any]] = []
    passed = 0
    failed = 0
    for name, fn in CASES:
        try:
            ok, detail, kind = fn()
        except Exception as exc:  # noqa: BLE001
            ok = False
            detail = f"EXC: {exc}\n{traceback.format_exc()}"
            kind = "RUNTIME_UNIT"
        results.append({"CASE": name, "PASS": ok, "DETAIL": detail, "KIND": kind})
        if ok:
            passed += 1
            print(f"PASS {name}: {detail}")
        else:
            failed += 1
            print(f"FAIL {name}: {detail}")
    summary = {
        "SUITE": "corrective-v10",
        "TOTAL": len(CASES),
        "PASSED": passed,
        "FAILED": failed,
        "RESULTS": results,
    }
    out = Path(".tmp/opsx-bug-team-harness/corrective-v10-unit/SUMMARY.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"\nV10 SUMMARY: {passed}/{len(CASES)} PASS")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
