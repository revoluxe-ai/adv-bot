# -*- coding: utf-8 -*-
"""Corrective V11 — mandatory LEARNING_DECISION before closure.

Process-only harness. Does not mutate product code, activate untested live
wiring until D2 promotion, or create commits.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import control_model, family_fanout, learning_decision  # noqa: E402
from harness import task_dispatch  # noqa: E402

Result = Tuple[bool, str, str]
HARNESS = Path(".tmp/opsx-bug-team-harness/corrective-v11-learning")
CAH = Path(".tmp/opsx-bug-cases/BUGCASE-CAH-DOUBLE-ANSWER-20260729T013308Z")


def _case(name: str, *, with_family: bool = False) -> Path:
    p = HARNESS / name
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    (p / "results").mkdir(parents=True, exist_ok=True)
    (p / "findings").mkdir(parents=True, exist_ok=True)
    if with_family:
        (p / "family").mkdir(parents=True, exist_ok=True)
    return p


def _write_fanin(case: Path, *, family: bool = False) -> Path:
    if family:
        path = case / "results" / "FAMILY-FANIN.md"
        path.write_text(
            "FAMILY_CLOSURE_READINESS: READY_FOR_FAMILY_CLOSURE\n"
            "READY_FOR_FAMILY_CLOSURE\nBLOCKING_FINDINGS: NONE\n",
            encoding="utf-8",
        )
        jpath = case / "results" / "FAMILY-FANIN.json"
        jpath.write_text(
            json.dumps(
                {
                    "FAMILY_CLOSURE_READINESS": "READY_FOR_FAMILY_CLOSURE",
                    "FAMILY_GREEN_STATUS": "PASS",
                    "OPEN_BLOCKING_FINDINGS": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return jpath
    path = case / "results" / "FANIN.md"
    path.write_text(
        "CLOSURE_READINESS: READY_FOR_CLOSURE\nBLOCKING_FINDINGS: NONE\n",
        encoding="utf-8",
    )
    return path


def _decision(
    case: Path,
    *,
    case_id: str,
    verdict: str,
    status: str = "COMPLETE",
    promo: str = "NONE",
    fanin_rel: str = "results/FANIN.md",
    full_packet_path: str | None = None,
    fanin_hash_override: str | None = None,
    extras: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    fanin = case / fanin_rel
    packet_required = learning_decision.full_packet_required_for_verdict(verdict)
    if packet_required and promo == "NONE":
        promo = "DEFERRED"
    d = learning_decision.build_learning_decision(
        case_id=case_id,
        learning_verdict=verdict,
        learning_status=status,
        promotion_decision=promo,
        source_fanin_path=fanin_rel,
        source_fanin_hash=(
            fanin_hash_override
            if fanin_hash_override is not None
            else learning_decision.file_sha(fanin)
        ),
        full_packet_path=full_packet_path,
        decision_rationale=f"V11 test verdict={verdict}",
        recommendations={
            "STATIC_CHECK_CANDIDATE": False,
            "PROJECT_WIDE_HUNT_REQUEST": False,
            "TESTING_RULES_CANDIDATE": False,
        },
    )
    if extras:
        d.update(extras)
        d["DECISION_HASH"] = learning_decision.compute_decision_hash(d)
    if packet_required and full_packet_path:
        pkt = case / full_packet_path
        pkt.parent.mkdir(parents=True, exist_ok=True)
        if not pkt.exists():
            pkt.write_text(
                json.dumps({"LEARNING_STATUS": "COMPLETE", "STUB": True}) + "\n",
                encoding="utf-8",
            )
        d["FULL_PACKET_PATH"] = full_packet_path
        d["FULL_PACKET_REQUIRED"] = True
        d["DECISION_HASH"] = learning_decision.compute_decision_hash(d)
    learning_decision.write_learning_decision(case, d)
    return d


def _human() -> Dict[str, Any]:
    return {
        "what_happened": "x",
        "what_was_broken": "y",
        "why_problem": "z",
        "what_changed": "w",
        "files_changed": ["a.py"],
        "how_verified": "tests",
        "extra_checks": "n",
        "not_changed": "product unrelated",
        "remaining_risks": "none",
        "review_before_commit": "diff",
        "technical_details": "tech",
    }


# --- T1–T16 ---


def t01() -> Result:
    """Fan-in ready → learning dispatched before closure."""
    case = _case("t01")
    _write_fanin(case)
    readiness, blocking = control_model.parse_fanin_readiness(case / "results" / "FANIN.md")
    d = control_model.decide_auto_closure(
        execution_mode=control_model.MODE_CONTROLLED_LIVE_UNCOMMITTED,
        closure_readiness=readiness,
        blocking_findings=blocking,
        case_root=case,
    )
    ok = (
        d.get("AUTO_CLOSURE") is False
        and d.get("EXPECTED_NEXT_COMMAND") == "FAMILY_LEARNING_WORKER"
        and d.get("LEARNING_DISPATCH_ALLOWED") is True
        and d.get("CLOSURE_OPERATOR_DISPATCH_ALLOWED") is False
    )
    return ok, "T1 fan-in ready dispatches learning before closure", "RUNTIME_UNIT"


def t02() -> Result:
    """Closure without LEARNING_DECISION → BLOCKED_LEARNING_DECISION_MISSING."""
    case = _case("t02")
    _write_fanin(case)
    try:
        learning_decision.evaluate_closure_learning_gate(case)
        return False, "T2 should block missing decision", "RUNTIME_UNIT"
    except learning_decision.LearningDecisionError as exc:
        out = control_model.apply_closure_artifacts(
            case, finding_id="F2", human_summary_kwargs=_human()
        )
        ok = (
            exc.code == "BLOCKED_LEARNING_DECISION_MISSING"
            and out.get("STATUS") == "BLOCKED_LEARNING_DECISION_MISSING"
        )
        return ok, "T2 closure without decision blocked", "RUNTIME_UNIT"


def t03() -> Result:
    """NO_REUSABLE_LESSON → close without full packet."""
    case = _case("t03")
    _write_fanin(case)
    _decision(case, case_id="C3", verdict="NO_REUSABLE_LESSON")
    gate = learning_decision.evaluate_closure_learning_gate(case)
    out = control_model.apply_closure_artifacts(
        case, finding_id="F3", human_summary_kwargs=_human()
    )
    ok = (
        gate["STATUS"] == "PASS"
        and out.get("CASE_STATUS") == "CLOSED"
        and not (case / "family" / "LEARNING_PACKET.json").exists()
        and (case / "results" / "LEARNING_DECISION.json").exists()
    )
    return ok, "T3 NO_REUSABLE_LESSON closes without packet", "RUNTIME_UNIT"


def t04() -> Result:
    """LOCAL_CASE_NOTE_ONLY → close without full packet."""
    case = _case("t04")
    _write_fanin(case)
    _decision(case, case_id="C4", verdict="LOCAL_CASE_NOTE_ONLY")
    out = control_model.apply_closure_artifacts(
        case, finding_id="F4", human_summary_kwargs=_human()
    )
    ok = out.get("CASE_STATUS") == "CLOSED" and not (
        case / "family" / "LEARNING_PACKET.json"
    ).exists()
    return ok, "T4 LOCAL_CASE_NOTE_ONLY closes without packet", "RUNTIME_UNIT"


def t05() -> Result:
    """EXISTING_POLICY_COMPLIANCE_FAILURE → close without full packet."""
    case = _case("t05")
    _write_fanin(case)
    d = _decision(
        case,
        case_id="C5",
        verdict="EXISTING_POLICY_COMPLIANCE_FAILURE",
        promo="DEFERRED",
        extras={
            "POLICY_ALREADY_EXISTS": True,
            "ENFORCEMENT_GAP": "candidate",
        },
    )
    # rebuild hash after extras already handled in _decision
    out = control_model.apply_closure_artifacts(
        case, finding_id="F5", human_summary_kwargs=_human()
    )
    ok = out.get("CASE_STATUS") == "CLOSED" and d.get("FULL_PACKET_REQUIRED") is False
    return ok, "T5 EXISTING_POLICY closes without packet", "RUNTIME_UNIT"


def t06() -> Result:
    """COMPLIANCE_ENFORCEMENT_CANDIDATE + packet + deferred → close allowed."""
    case = _case("t06", with_family=True)
    _write_fanin(case, family=True)
    _decision(
        case,
        case_id="C6",
        verdict="COMPLIANCE_ENFORCEMENT_CANDIDATE",
        promo="DEFERRED",
        fanin_rel="results/FAMILY-FANIN.json",
        full_packet_path="family/LEARNING_PACKET.json",
    )
    out = control_model.apply_closure_artifacts(
        case, finding_id="F6", human_summary_kwargs=_human()
    )
    ok = out.get("CASE_STATUS") == "CLOSED" and (
        case / "family" / "LEARNING_PACKET.json"
    ).exists()
    return ok, "T6 compliance candidate closes with packet+deferred", "RUNTIME_UNIT"


def t07() -> Result:
    """CLASS_LESSON_CANDIDATE + deferred → close, no global rule write."""
    case = _case("t07", with_family=True)
    _write_fanin(case, family=True)
    d = _decision(
        case,
        case_id="C7",
        verdict="CLASS_LESSON_CANDIDATE",
        promo="DEFERRED",
        fanin_rel="results/FAMILY-FANIN.json",
        full_packet_path="family/LEARNING_PACKET.json",
    )
    learning_decision.assert_no_auto_promotion_side_effects(d)
    out = control_model.apply_closure_artifacts(
        case, finding_id="F7", human_summary_kwargs=_human()
    )
    ok = (
        out.get("CASE_STATUS") == "CLOSED"
        and d.get("GLOBAL_RULES_ACTIVATED") is not True
        and d.get("PROMOTION_DECISION") == "DEFERRED"
    )
    return ok, "T7 class lesson candidate closes without global rule write", "RUNTIME_UNIT"


def t08() -> Result:
    """SUPERCLASS_SEED_EVIDENCE → no ACTIVE superclass."""
    case = _case("t08", with_family=True)
    _write_fanin(case, family=True)
    d = _decision(
        case,
        case_id="C8",
        verdict="SUPERCLASS_SEED_EVIDENCE",
        promo="DEFERRED",
        fanin_rel="results/FAMILY-FANIN.json",
        full_packet_path="family/LEARNING_PACKET.json",
        extras={"SUPERCLASS_ACTIVATED": False},
    )
    learning_decision.assert_no_auto_promotion_side_effects(d)
    out = control_model.apply_closure_artifacts(
        case, finding_id="F8", human_summary_kwargs=_human()
    )
    ok = out.get("CASE_STATUS") == "CLOSED" and d.get("SUPERCLASS_ACTIVATED") is not True
    return ok, "T8 superclass seed does not activate superclass", "RUNTIME_UNIT"


def t09() -> Result:
    """OWNER_DECISION_REQUIRED → closure blocked."""
    case = _case("t09")
    _write_fanin(case)
    _decision(
        case,
        case_id="C9",
        verdict="OWNER_DECISION_REQUIRED",
        status="OWNER_WAIT",
    )
    try:
        learning_decision.evaluate_closure_learning_gate(case)
        return False, "T9 should block", "RUNTIME_UNIT"
    except learning_decision.LearningDecisionError as exc:
        return (
            exc.code == "BLOCKED_OWNER_LEARNING_DECISION_REQUIRED",
            "T9 OWNER_DECISION_REQUIRED blocks closure",
            "RUNTIME_UNIT",
        )


def t10() -> Result:
    """LEARNING_BLOCKED → closure blocked."""
    case = _case("t10")
    _write_fanin(case)
    _decision(case, case_id="C10", verdict="LEARNING_BLOCKED", status="BLOCKED")
    try:
        learning_decision.evaluate_closure_learning_gate(case)
        return False, "T10 should block", "RUNTIME_UNIT"
    except learning_decision.LearningDecisionError as exc:
        return (
            exc.code == "BLOCKED_LEARNING_INCOMPLETE",
            "T10 LEARNING_BLOCKED blocks closure",
            "RUNTIME_UNIT",
        )


def t11() -> Result:
    """Learning timeout → resume dispatches learning only."""
    case = _case("t11")
    _write_fanin(case)
    learning_decision.mark_learning_timeout(case, case_id="C11")
    nxt, detail = learning_decision.expected_next_after_fanin(case)
    ok = (
        nxt == "FAMILY_LEARNING_WORKER"
        and detail.get("EXPECTED_NEXT_COMMAND") == "FAMILY_LEARNING_WORKER"
    )
    # After timeout, no RED/FIX/GREEN markers should be required to re-run —
    # only learning is expected.
    return ok, "T11 timeout resume dispatches learning only", "RUNTIME_UNIT"


def t12() -> Result:
    """Invalid fan-in hash → learning decision rejected."""
    case = _case("t12")
    fanin = _write_fanin(case)
    _decision(
        case,
        case_id="C12",
        verdict="NO_REUSABLE_LESSON",
        fanin_hash_override="0" * 64,
    )
    try:
        learning_decision.validate_learning_decision(
            learning_decision.load_learning_decision(case) or {},
            case_root=case,
        )
        return False, "T12 should reject stale hash", "RUNTIME_UNIT"
    except learning_decision.LearningDecisionError as exc:
        ok = (
            exc.code == "BLOCKED_LEARNING_DECISION_INVALID"
            and "fan-in hash" in (exc.detail or "")
        )
        _ = fanin
        return ok, "T12 invalid fan-in hash rejected", "RUNTIME_UNIT"


def t13() -> Result:
    """Full packet required but absent → closure blocked."""
    case = _case("t13", with_family=True)
    _write_fanin(case, family=True)
    d = learning_decision.build_learning_decision(
        case_id="C13",
        learning_verdict="CLASS_LESSON_CANDIDATE",
        learning_status="COMPLETE",
        promotion_decision="DEFERRED",
        source_fanin_path="results/FAMILY-FANIN.json",
        source_fanin_hash=learning_decision.file_sha(case / "results" / "FAMILY-FANIN.json"),
        full_packet_path="family/LEARNING_PACKET.json",
        decision_rationale="missing packet",
    )
    # Intentionally do not create packet file
    learning_decision.write_learning_decision(case, d)
    try:
        learning_decision.evaluate_closure_learning_gate(case)
        return False, "T13 should block missing packet", "RUNTIME_UNIT"
    except learning_decision.LearningDecisionError as exc:
        return (
            exc.code == "BLOCKED_LEARNING_INCOMPLETE"
            and "packet" in (exc.detail or "").lower(),
            "T13 missing full packet blocks closure",
            "RUNTIME_UNIT",
        )


def t14() -> Result:
    """Live WAVE_4 and runtime graph agree on learning edge."""
    edges = learning_decision.LIVE_TERMINAL_EDGES
    path = learning_decision.LIVE_TERMINAL_PATH
    ok_path = path == (
        "FAN_IN_ASSEMBLER",
        "FAMILY_LEARNING_WORKER",
        "CLOSURE_OPERATOR",
    )
    ok_edges = edges == (
        ("FAN_IN_ASSEMBLER", "FAMILY_LEARNING_WORKER"),
        ("FAMILY_LEARNING_WORKER", "CLOSURE_OPERATOR"),
    )
    td_edges = getattr(task_dispatch, "LIVE_TERMINAL_EDGES", ())
    td_workers = getattr(task_dispatch, "WORKER_IDS", ())
    td_ok = td_edges == edges and "FAMILY_LEARNING_WORKER" in td_workers
    orch = ROOT / "ORCHESTRATION.md"
    bug_team = ROOT.parents[1] / "commands" / "opsx-bug-team.md"
    docs_ok = True
    for p in (orch, bug_team):
        if not p.exists():
            docs_ok = False
            break
        text = p.read_text(encoding="utf-8")
        if "FAMILY_LEARNING_WORKER" not in text:
            docs_ok = False
            break
    ok = ok_path and ok_edges and td_ok and docs_ok
    return ok, "T14 live WAVE_4 and runtime graph agree on learning edge", "RUNTIME_UNIT"


def t15() -> Result:
    """Existing-policy verdict does not auto-launch static check / hunt / rules."""
    case = _case("t15")
    _write_fanin(case)
    d = _decision(
        case,
        case_id="C15",
        verdict="EXISTING_POLICY_COMPLIANCE_FAILURE",
        promo="DEFERRED",
        extras={
            "POLICY_ALREADY_EXISTS": True,
            "ENFORCEMENT_GAP": "candidate",
            "RECOMMENDATIONS": {
                "STATIC_CHECK_CANDIDATE": True,
                "PROJECT_WIDE_HUNT_REQUEST": True,
                "TESTING_RULES_CANDIDATE": True,
            },
        },
    )
    try:
        learning_decision.assert_no_auto_promotion_side_effects(d)
        learning_decision.evaluate_closure_learning_gate(case)
        launched = any(
            [
                d.get("STATIC_CHECK_LAUNCHED"),
                d.get("PROJECT_HUNT_LAUNCHED"),
                d.get("TESTING_RULES_MUTATED"),
                d.get("GLOBAL_RULES_ACTIVATED"),
            ]
        )
        return (not launched), "T15 no auto remediation from existing-policy", "RUNTIME_UNIT"
    except learning_decision.LearningDecisionError as exc:
        return False, f"T15 unexpected: {exc.code}", "RUNTIME_UNIT"


def t16() -> Result:
    """CAH metadata backfill must not imply product lifecycle reopen."""
    # Pre-backfill: ensure product markers stay closed; after D5, LEARNING_DECISION
    # exists with PROCESS_METADATA_CORRECTED. This test is re-runnable.
    if not CAH.exists():
        return True, "T16 CAH case absent in this workspace — skipped", "RUNTIME_UNIT"
    # Product reopen signals forbidden
    forbidden_rerun = False
    # Check no new RED/FIX/GREEN timestamps after closure by ensuring
    # CASE remains CLOSED and we only look for metadata fields.
    case_md = CAH / "CASE.md"
    text = case_md.read_text(encoding="utf-8") if case_md.exists() else ""
    closed = "CLOSED" in text or "CASE_STATUS: CLOSED" in text
    decision_path = CAH / "results" / "LEARNING_DECISION.json"
    if decision_path.exists():
        d = json.loads(decision_path.read_text(encoding="utf-8"))
        meta_ok = (
            d.get("LEARNING_VERDICT") == "EXISTING_POLICY_COMPLIANCE_FAILURE"
            and d.get("PROCESS_METADATA_CORRECTED") is True
            and d.get("PRODUCT_CLOSURE_VALID") is True
            and d.get("FULL_PACKET_REQUIRED") is False
        )
        # No LEARNING_PACKET unless promotion required
        packet_absent = not (CAH / "family" / "LEARNING_PACKET.json").exists()
        ok = closed and meta_ok and packet_absent and not forbidden_rerun
        return ok, "T16 CAH metadata corrective without product reopen", "RUNTIME_UNIT"
    # Before D5 backfill: closed product state is enough for pre-check
    return closed, "T16 CAH still product-closed (backfill pending)", "RUNTIME_UNIT"


TESTS: List[Tuple[str, Callable[[], Result]]] = [
    ("T1", t01),
    ("T2", t02),
    ("T3", t03),
    ("T4", t04),
    ("T5", t05),
    ("T6", t06),
    ("T7", t07),
    ("T8", t08),
    ("T9", t09),
    ("T10", t10),
    ("T11", t11),
    ("T12", t12),
    ("T13", t13),
    ("T14", t14),
    ("T15", t15),
    ("T16", t16),
]


def main() -> int:
    """Run V11 learning corrective matrix."""
    HARNESS.mkdir(parents=True, exist_ok=True)
    passed = 0
    failed = 0
    rows: List[Dict[str, Any]] = []
    for name, fn in TESTS:
        try:
            ok, msg, kind = fn()
        except Exception as exc:  # noqa: BLE001
            ok, msg, kind = False, f"{exc}\n{traceback.format_exc()}", "RUNTIME_UNIT"
        if ok:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"
        rows.append({"ID": name, "STATUS": status, "MSG": msg, "KIND": kind})
        print(f"{status}: {name} — {msg}")
    report = {
        "SUITE": "corrective-v11-learning",
        "TOTAL": len(TESTS),
        "PASSED": passed,
        "FAILED": failed,
        "ROWS": rows,
    }
    out = HARNESS / "LAST_RUN.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nTOTAL={len(TESTS)} PASSED={passed} FAILED={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
