# -*- coding: utf-8 -*-
"""Corrective V7 tests — USER_REVIEWS_UNCOMMITTED_WORKTREE control model.

Does NOT activate runtime. Does NOT create real bug cases or commits.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import (  # noqa: E402
    activation,
    control_model,
    fs_boundary,
    learning_decision,
    live_task_hop,
    owner_decision_host,
)

Result = Tuple[bool, str, str]
HARNESS = Path(".tmp/opsx-bug-team-harness/corrective-v7-unit")


def _write_episode_learning(
    case: Path,
    *,
    case_id: str = "C-V7",
    verdict: str = "NO_REUSABLE_LESSON",
    fanin_rel: str = "results/FANIN.md",
) -> Dict[str, Any]:
    """Mandatory LEARNING_DECISION before episode closure (V11 corrective)."""
    fanin = case / fanin_rel
    decision = learning_decision.build_learning_decision(
        case_id=case_id,
        learning_verdict=verdict,
        learning_status="COMPLETE",
        promotion_decision="NONE",
        source_fanin_path=fanin_rel,
        source_fanin_hash=learning_decision.file_sha(fanin) if fanin.exists() else None,
        decision_rationale="V7 harness learning hop",
    )
    learning_decision.write_learning_decision(case, decision)
    return decision


def _case(name: str) -> Path:
    p = HARNESS / name
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    (p / "team" / "packets").mkdir(parents=True, exist_ok=True)
    (p / "results").mkdir(parents=True, exist_ok=True)
    (p / "gates").mkdir(parents=True, exist_ok=True)
    (p / "findings").mkdir(parents=True, exist_ok=True)
    return p


def _human_kwargs(**over: Any) -> Dict[str, Any]:
    base = {
        "what_happened": "Пользователь увидел, что таймер стартовал слишком рано.",
        "what_was_broken": "Программа запускала таймер до выбора длительности.",
        "why_problem": "Пользователь не успевал выбрать длительность.",
        "what_changed": "Теперь таймер стартует только после подтверждения длительности.",
        "files_changed": ["app/example.py"],
        "how_verified": "Прогнали проверочные тесты на сценарий таймера.",
        "extra_checks": "Проверили соседние экраны выбора ключей.",
        "not_changed": "Не трогали биллинг и удалённые серверы.",
        "remaining_risks": "Нужно глазами посмотреть diff перед коммитом.",
        "review_before_commit": "Откройте git diff и убедитесь, что изменения только про таймер.",
        "technical_details": "Функция set_warmup_duration в epoch_write.py — это место, где сохраняется длительность.",
        "tests_and_results": "unit tests PASS",
        "episode_files": ["app/example.py"],
        "unrelated_dirty_files": [".idea/workspace.xml"],
    }
    base.update(over)
    return base


def _sim_route_flow(case: Path, *, route: str, task_delta: str = "UNCHANGED") -> Dict[str, Any]:
    """Simulate end-to-end control decisions for a route (no real Task)."""
    mode = control_model.MODE_CONTROLLED_LIVE_UNCOMMITTED
    steps: List[str] = ["INTAKE", "MATERIALIZE", "CLAIM", "CLASSIFY", f"ROUTE_{route}"]
    if route == "C":
        _write_episode_learning(case)
        closure = control_model.apply_closure_artifacts(
            case,
            finding_id="F-C",
            human_summary_kwargs=_human_kwargs(
                what_changed="Исправление кода не делали — это ложное срабатывание / вне scope.",
                files_changed=[],
                episode_files=[],
            ),
            terminal_status="CLOSED_NO_IMPLEMENTATION",
        )
        return {
            "ROUTE": route,
            "STEPS": steps + ["CLOSE_RECOMMENDATION", "CLOSURE"],
            "IMPLEMENTATION": False,
            "WAITING_OWNER": False,
            **closure,
        }
    if route == "D":
        handoff = case / "results" / "ROUTE-D-HANDOFF.md"
        handoff.write_text(
            "ROUTE_TARGET_PROCESS_ID: PROC-DEMO\nFAKE_CLOSURE: NO\n",
            encoding="utf-8",
        )
        return {
            "ROUTE": "D",
            "STEPS": steps + ["HANDOFF"],
            "CASE_STATUS": "OPEN_HANDED_OFF",
            "TERMINAL_STATUS": "ROUTE_D_HANDOFF",
            "IMPLEMENTATION": False,
            "WAITING_OWNER": False,
            "AUTO_CLOSURE": False,
            "HANDOFF_PATH": str(handoff),
        }
    if route == "INSUFFICIENT":
        return {
            "ROUTE": "INSUFFICIENT_EVIDENCE",
            "STEPS": steps,
            "STATUS": "BLOCKED_INSUFFICIENT_EVIDENCE",
            "IMPLEMENTATION": False,
            "WAITING_OWNER": False,
            "CASE_STATUS": "OPEN_BLOCKED",
        }
    # A / B
    if route == "B":
        steps.append(f"TASK_DELTA_{task_delta}")
        if task_delta == "CHANGED":
            steps.append("SPEC_UPDATE")
    steps.append("RED")
    auth = control_model.validate_local_implementation_authority(
        execution_mode=mode,
        red_status="RED_CONFIRMED",
        red_packet_valid=True,
        frozen_test_hashes_valid=True,
        expected_execution_route_valid=True,
        worker_write_boundary_valid=True,
    )
    assert auth["WAITING_OWNER"] is False
    steps.append("LOCAL_AUTHORITY")
    # simulate local fix file
    fix = case / "results" / "FIX-ROOT.md"
    fix.write_text("local fix evidence\n", encoding="utf-8")
    (case / "app").mkdir(exist_ok=True)
    (case / "app" / "example.py").write_text("# fixed\n", encoding="utf-8")
    steps.extend(["EXECUTOR", "GREEN", "TASK_COMPLETION", "HUNT", "FANIN"])
    fanin = case / "results" / "FANIN.md"
    fanin.write_text(
        "CLOSURE_READINESS: READY_FOR_CLOSURE\nBLOCKING_FINDINGS: NONE\n",
        encoding="utf-8",
    )
    readiness, blocking = control_model.parse_fanin_readiness(fanin)
    pre = control_model.decide_auto_closure(
        execution_mode=mode,
        closure_readiness=readiness,
        blocking_findings=blocking,
        case_root=case,
    )
    assert pre.get("EXPECTED_NEXT_COMMAND") == "FAMILY_LEARNING_WORKER"
    assert pre.get("AUTO_CLOSURE") is False
    steps.append("FAMILY_LEARNING")
    _write_episode_learning(case)
    decision = control_model.decide_auto_closure(
        execution_mode=mode,
        closure_readiness=readiness,
        blocking_findings=blocking,
        case_root=case,
    )
    assert decision["AUTO_CLOSURE"] is True
    assert decision.get("WAITING_OWNER_FINAL_CLOSURE") is False
    steps.append("AUTO_CLOSURE")
    closure = control_model.apply_closure_artifacts(
        case,
        finding_id="F-ROOT",
        human_summary_kwargs=_human_kwargs(),
    )
    steps.append("HUMAN_SUMMARY")
    terminal = control_model.terminal_user_control_state(
        case_closed=True,
        commit_created=False,
        worktree_has_episode_changes=True,
    )
    return {
        "ROUTE": route,
        "TASK_DELTA": task_delta,
        "STEPS": steps,
        "IMPLEMENTATION": True,
        "WAITING_OWNER": False,
        "LOCAL_AUTHORITY": auth,
        "AUTO_CLOSURE": decision,
        **closure,
        **terminal,
    }


# --- Flows ---


def flow01() -> Result:
    case = _case("flow01")
    res = _sim_route_flow(case, route="A")
    ok = (
        res["IMPLEMENTATION"]
        and res["WAITING_OWNER"] is False
        and res["CASE_STATUS"] == "CLOSED"
        and (case / "results" / "HUMAN_SUMMARY.md").exists()
        and "EXECUTOR" in res["STEPS"]
        and "AUTO_CLOSURE" in res["STEPS"]
    )
    return ok, "Route A RED -> auto local executor -> GREEN -> closure", "RUNTIME_UNIT"


def flow02() -> Result:
    case = _case("flow02")
    res = _sim_route_flow(case, route="B", task_delta="CHANGED")
    ok = "SPEC_UPDATE" in res["STEPS"] and res["CASE_STATUS"] == "CLOSED"
    return ok, "Route B TASK_DELTA=CHANGED -> update -> RED -> apply -> closure", "RUNTIME_UNIT"


def flow03() -> Result:
    case = _case("flow03")
    res = _sim_route_flow(case, route="B", task_delta="UNCHANGED")
    ok = "SPEC_UPDATE" not in res["STEPS"] and res["CASE_STATUS"] == "CLOSED"
    return ok, "Route B TASK_DELTA=UNCHANGED -> RED -> fix -> closure", "RUNTIME_UNIT"


def flow04() -> Result:
    case = _case("flow04")
    res = _sim_route_flow(case, route="C")
    ok = res["IMPLEMENTATION"] is False and res["CASE_STATUS"] == "CLOSED"
    return ok, "Route C closed without implementation", "RUNTIME_UNIT"


def flow05() -> Result:
    case = _case("flow05")
    res = _sim_route_flow(case, route="D")
    ok = (
        res["TERMINAL_STATUS"] == "ROUTE_D_HANDOFF"
        and res["AUTO_CLOSURE"] is False
        and Path(res["HANDOFF_PATH"]).exists()
    )
    return ok, "Route D durable handoff, no fake closure", "RUNTIME_UNIT"


def flow06() -> Result:
    case = _case("flow06")
    res = _sim_route_flow(case, route="INSUFFICIENT")
    ok = (
        res["STATUS"] == "BLOCKED_INSUFFICIENT_EVIDENCE"
        and res["IMPLEMENTATION"] is False
        and not (case / "results" / "FIX-ROOT.md").exists()
    )
    return ok, "insufficient evidence blocked, no implementation", "RUNTIME_UNIT"


# --- Gates ---


def gate01() -> Result:
    case = _case("gate01")
    prep = live_task_hop.prepare_live_hop(
        case_root=case,
        orchestration_id="ORCH/v7",
        worker_id="IMPLEMENTATION_EXECUTOR",
        case_id="C-V7",
        finding_id="F-V7",
        execution_mode=control_model.MODE_CONTROLLED_LIVE_UNCOMMITTED,
        checkpoint_generation=1,
        packet_generation=1,
        proof_root=case,
        owner_gate_context={
            "red_status": "RED_CONFIRMED",
            "red_packet_valid": True,
            "frozen_test_hashes_valid": True,
            "expected_execution_route_valid": True,
            "worker_write_boundary_valid": True,
        },
    )
    intent = json.loads(Path(prep["DISPATCH_INTENT_PATH"]).read_text(encoding="utf-8"))
    ok = (
        prep.get("DISPATCH_INTENT_CREATED") is True
        and prep.get("LOCAL_IMPLEMENTATION_AUTHORIZED") is True
        and prep.get("WAITING_OWNER") is False
        and intent.get("OWNER_RECEIPT_GATE_ID") is None
        and intent.get("LOCAL_IMPLEMENTATION_AUTHORIZED") is True
    )
    return ok, "RED_CONFIRMED uncommitted: no WAITING_OWNER, executor allowed", "RUNTIME_UNIT"


def gate02() -> Result:
    case = _case("gate02")
    fanin = case / "results" / "FANIN.md"
    fanin.write_text(
        "CLOSURE_READINESS: READY_FOR_CLOSURE\nBLOCKING_FINDINGS: NONE\n",
        encoding="utf-8",
    )
    readiness, blocking = control_model.parse_fanin_readiness(fanin)
    pre = control_model.decide_auto_closure(
        execution_mode=control_model.MODE_CONTROLLED_LIVE_UNCOMMITTED,
        closure_readiness=readiness,
        blocking_findings=blocking,
        case_root=case,
    )
    ok = (
        pre.get("AUTO_CLOSURE") is False
        and pre.get("EXPECTED_NEXT_COMMAND") == "FAMILY_LEARNING_WORKER"
    )
    _write_episode_learning(case)
    d = control_model.decide_auto_closure(
        execution_mode=control_model.MODE_CONTROLLED_LIVE_UNCOMMITTED,
        closure_readiness=readiness,
        blocking_findings=blocking,
        case_root=case,
    )
    ok = ok and d["AUTO_CLOSURE"] is True and d.get("WAITING_OWNER") is False
    if ok:
        control_model.apply_closure_artifacts(
            case, finding_id="F-G2", human_summary_kwargs=_human_kwargs()
        )
        ok = (case / "results" / "HUMAN_SUMMARY.md").exists()
    return (
        ok,
        "FANIN ready -> learning -> no WAITING_OWNER_FINAL_CLOSURE; closure runs",
        "RUNTIME_UNIT",
    )


def gate03() -> Result:
    case = _case("gate03")
    try:
        live_task_hop.prepare_live_hop(
            case_root=case,
            orchestration_id="ORCH/v7",
            worker_id="IMPLEMENTATION_EXECUTOR",
            case_id="C-V7",
            finding_id="F-V7",
            execution_mode=control_model.MODE_OWNER_GATED,
            checkpoint_generation=1,
            packet_generation=1,
            proof_root=case,
        )
        return False, "OWNER_GATED should require GO", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc:
        # OWNER_GATED under NOT_ACTIVE may block at activation first
        ok = exc.code in {
            "BLOCKED_OWNER_PRODUCTION_GO_REQUIRED",
            "BLOCKED_CANDIDATE_NOT_ACTIVE",
            "BLOCKED_PROOF_ROOT_OUTSIDE_HARNESS",
        }
        # Force OWNER_GATED path via REVIEW_PROOF_ONLY legacy (Owner GO still required)
    case2 = _case("gate03b")
    try:
        live_task_hop.prepare_live_hop(
            case_root=case2,
            orchestration_id="ORCH/v7",
            worker_id="IMPLEMENTATION_EXECUTOR",
            case_id="C-V7",
            finding_id="F-V7",
            execution_mode="REVIEW_PROOF_ONLY",
            checkpoint_generation=1,
            packet_generation=1,
            proof_root=case2,
        )
        return False, "proof executor without GO should block", "RUNTIME_UNIT"
    except live_task_hop.LiveHopError as exc2:
        ok2 = exc2.code == "BLOCKED_OWNER_PRODUCTION_GO_REQUIRED"
        d = control_model.decide_auto_closure(
            execution_mode=control_model.MODE_OWNER_GATED,
            closure_readiness="READY_FOR_CLOSURE",
            blocking_findings=[],
        )
        ok3 = d["STATUS"] == "WAITING_OWNER_FINAL_CLOSURE" and d["AUTO_CLOSURE"] is False
        return ok2 and ok3, "OWNER_GATED / legacy Owner gate still enforced", "RUNTIME_UNIT"


def gate04() -> Result:
    try:
        control_model.validate_local_implementation_authority(
            execution_mode=control_model.MODE_CONTROLLED_LIVE_UNCOMMITTED,
            red_status="RED_CONFIRMED",
            red_packet_valid=True,
            frozen_test_hashes_valid=True,
            expected_execution_route_valid=True,
            worker_write_boundary_valid=True,
            external_mutation_required=True,
        )
        return False, "should block external", "RUNTIME_UNIT"
    except control_model.ControlModelError as exc:
        return (
            exc.code == "BLOCKED_EXTERNAL_OR_IRREVERSIBLE_MUTATION_REQUIRED",
            "external mutation required -> blocked",
            "RUNTIME_UNIT",
        )


def gate05() -> Result:
    code = control_model.reject_forbidden_shell_command("kubectl apply -f deploy.yaml")
    return code == "BLOCKED_DEPLOY_FORBIDDEN", "deploy command attempted -> rejected", "RUNTIME_UNIT"


def gate06() -> Result:
    code = control_model.reject_forbidden_shell_command("git commit -m 'x'")
    return code == "BLOCKED_GIT_COMMIT_FORBIDDEN", "git commit attempted -> rejected", "RUNTIME_UNIT"


# --- User control ---


def user01() -> Result:
    case = _case("user01")
    res = _sim_route_flow(case, route="A")
    ok = (
        (case / "app" / "example.py").exists()
        and res["WORKTREE_STATUS"] == "UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW"
    )
    return ok, "successful episode leaves uncommitted worktree changes", "RUNTIME_UNIT"


def user02() -> Result:
    # Builder must not create commits — assert control forbids
    code = control_model.reject_forbidden_shell_command("git commit -am msg")
    return code == "BLOCKED_GIT_COMMIT_FORBIDDEN", "no git commit created/allowed", "RUNTIME_UNIT"


def user03() -> Result:
    code = control_model.reject_forbidden_shell_command("git push origin HEAD")
    return code == "BLOCKED_GIT_PUSH_FORBIDDEN", "no git push executed/allowed", "RUNTIME_UNIT"


def user04() -> Result:
    classified = control_model.classify_worktree_changes(
        episode_paths={"app/example.py", "results/FIX-ROOT.md"},
        all_dirty_paths={"app/example.py", "results/FIX-ROOT.md", ".idea/workspace.xml"},
    )
    ok = (
        ".idea/workspace.xml"
        in classified["РАНЕЕ_СУЩЕСТВОВАВШИЕ_НЕСВЯЗАННЫЕ_ИЗМЕНЕНИЯ"]
        and "app/example.py" in classified["ИЗМЕНЕНИЯ_ЭТОГО_BUG_EPISODE"]
    )
    return ok, "unrelated dirty files separated from episode changes", "RUNTIME_UNIT"


def user05() -> Result:
    t = control_model.terminal_user_control_state(
        case_closed=True, commit_created=False, worktree_has_episode_changes=True
    )
    ok = (
        t["USER_ACTION_REQUIRED"] == "REVIEW_DIFF_AND_DECIDE_COMMIT"
        and t["WORKTREE_STATUS"] == "UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW"
        and t["COMMITTED"] is False
    )
    return ok, "terminal state says AWAITING_USER_REVIEW", "RUNTIME_UNIT"


# --- Human ---


def human01() -> Result:
    case = _case("human01")
    _write_episode_learning(case)
    control_model.apply_closure_artifacts(
        case, finding_id="F-H", human_summary_kwargs=_human_kwargs()
    )
    return (
        control_model.human_summary_path(case).exists(),
        "HUMAN_SUMMARY.md created",
        "RUNTIME_UNIT",
    )


def human02() -> Result:
    case = _case("human02")
    p = control_model.write_human_summary(case, **_human_kwargs())
    ok, missing = control_model.validate_human_summary_file(p)
    return ok and not missing, "contains all required simple-language sections", "RUNTIME_UNIT"


def human03() -> Result:
    case = _case("human03")
    p = control_model.write_human_summary(case, **_human_kwargs())
    text = p.read_text(encoding="utf-8")
    return "app/example.py" in text, "contains changed file list", "RUNTIME_UNIT"


def human04() -> Result:
    case = _case("human04")
    p = control_model.write_human_summary(case, **_human_kwargs())
    text = p.read_text(encoding="utf-8")
    return "unit tests PASS" in text, "contains tests and results", "RUNTIME_UNIT"


def human05() -> Result:
    case = _case("human05")
    p = control_model.write_human_summary(case, **_human_kwargs())
    text = p.read_text(encoding="utf-8")
    return "Оставшиеся риски" in text and "diff" in text.lower(), "contains remaining risks", "RUNTIME_UNIT"


def human06() -> Result:
    case = _case("human06")
    p = control_model.write_human_summary(case, **_human_kwargs())
    text = p.read_text(encoding="utf-8")
    ok = (
        "Изменения этого bug episode" in text
        and ".idea/workspace.xml" in text
        and "Ранее существовавшие несвязанные изменения" in text
    )
    return ok, "separates episode changes from unrelated dirty files", "RUNTIME_UNIT"


def human07() -> Result:
    case = _case("human07")
    p = control_model.write_human_summary(case, **_human_kwargs())
    text = p.read_text(encoding="utf-8")
    # technical name appears after plain explanation
    ok = "таймер" in text.lower() and "set_warmup_duration" in text
    return ok, "technical jargon has plain-language explanation", "RUNTIME_UNIT"


def human08() -> Result:
    chat = control_model.format_simple_explanation_chat(
        noticed="Таймер стартовал рано",
        broken="Слишком ранний старт",
        why="Старт до выбора длительности",
        changed="Старт после подтверждения",
        files=["app/example.py"],
        why_fixes="Пользователь успевает выбрать длительность",
        verified="Тесты зелёные",
        tests="unit PASS",
        extra="Соседние экраны",
        not_changed="Биллинг",
        risks="Нужен визуальный diff",
        before_commit="git diff",
    )
    ok = chat.startswith("ПРОСТОЕ ОБЪЯСНЕНИЕ") and "12." in chat
    return ok, "final chat output includes ПРОСТОЕ ОБЪЯСНЕНИЕ", "RUNTIME_UNIT"


def fs_closure_boundary() -> Result:
    case = _case("fs_closure")
    ok_hs = fs_boundary.path_allowed("CLOSURE_OPERATOR", "results/HUMAN_SUMMARY.md")
    ok_oc = fs_boundary.path_allowed("CLOSURE_OPERATOR", "results/OWNER-CLOSURE-F.md")
    ok_case = fs_boundary.path_allowed("CLOSURE_OPERATOR", "CASE.md")
    bad = fs_boundary.path_allowed("FAN_IN_ASSEMBLER", "results/HUMAN_SUMMARY.md")
    return (
        ok_hs and ok_oc and ok_case and not bad,
        "CLOSURE write boundary allows summary; FANIN does not",
        "FILESYSTEM_ENFORCEMENT",
    )


TESTS: List[Tuple[str, Callable[[], Result]]] = [
    ("V7-FLOW-01", flow01),
    ("V7-FLOW-02", flow02),
    ("V7-FLOW-03", flow03),
    ("V7-FLOW-04", flow04),
    ("V7-FLOW-05", flow05),
    ("V7-FLOW-06", flow06),
    ("V7-GATE-01", gate01),
    ("V7-GATE-02", gate02),
    ("V7-GATE-03", gate03),
    ("V7-GATE-04", gate04),
    ("V7-GATE-05", gate05),
    ("V7-GATE-06", gate06),
    ("V7-USER-01", user01),
    ("V7-USER-02", user02),
    ("V7-USER-03", user03),
    ("V7-USER-04", user04),
    ("V7-USER-05", user05),
    ("V7-HUMAN-01", human01),
    ("V7-HUMAN-02", human02),
    ("V7-HUMAN-03", human03),
    ("V7-HUMAN-04", human04),
    ("V7-HUMAN-05", human05),
    ("V7-HUMAN-06", human06),
    ("V7-HUMAN-07", human07),
    ("V7-HUMAN-08", human08),
    ("V7-FS-CLOSURE", fs_closure_boundary),
]


def main() -> int:
    print("=== Corrective V7 tests (uncommitted worktree control) ===")
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
    out = Path(".tmp/opsx-bug-team-harness/corrective-v7-unit/RESULTS.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"total": total, "passed": passed, "failed": failed, "rows": rows}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
