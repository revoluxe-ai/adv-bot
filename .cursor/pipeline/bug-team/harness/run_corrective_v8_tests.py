# -*- coding: utf-8 -*-
"""Corrective V8 tests — invariant-centered bug family fanout (shadow).

Does NOT enable BUG_FAMILY_FANOUT as default.
Does NOT mutate real .tmp/opsx-bug-cases/**.
Does NOT create commits.
"""

from __future__ import annotations

import json
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime import bug_family, control_model, family_fanout, family_policy  # noqa: E402

Result = Tuple[bool, str, str]
HARNESS = Path(".tmp/opsx-bug-team-harness/corrective-v8-unit")
MODE = family_policy.CONTROLLED_TEST_MODE


def _case(name: str) -> Path:
    p = HARNESS / name
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    (p / "results").mkdir(parents=True, exist_ok=True)
    (p / "findings").mkdir(parents=True, exist_ok=True)
    return p


def _invariant_kwargs() -> Dict[str, Any]:
    return {
        "plain_language": (
            "Когда эпоха уже владеет переходом, выключение FAIL→OFF должно "
            "случиться ровно один раз на границе входа в эпоху."
        ),
        "technical": (
            "When epoch management owns the transition, FAIL→OFF must occur "
            "exactly once at the epoch boundary, before conflicting writers can "
            "run, and must not repeat during later PENDING ticks."
        ),
        "scope": "card_ab_hold epoch ENTER + setup FAIL→OFF writers",
        "entry_conditions": "phase non-NULL after start_epoch_on_enable; Classification FAIL keywords",
        "required_behavior": "apply FAIL→OFF exactly once at ENTER before later PENDING ticks",
        "forbidden_behavior": "skip FAIL→OFF on ENTER; re-apply every PENDING tick; race dual writers",
        "known_writers": ["process_ab_setup", "process_ab_epoch"],
        "known_readers": ["shop-runner tick", "KeywordSetting"],
        "proof_from_root": "ROOT GREEN evidence + RED test for ENTER FAIL→OFF",
        "hunt_scope": "same epoch ENTER / FAIL→OFF writer neighborhood only",
    }


def _bootstrap(case: Path, case_id: str = "C-V8", root: str = "ROOT-1") -> Dict[str, Any]:
    return family_fanout.bootstrap_family_after_root_green(
        case,
        case_id=case_id,
        root_finding_id=root,
        execution_mode=MODE,
        proof_root=case,
        invariant_kwargs=_invariant_kwargs(),
    )


def _cand(cid: str, fid: str, paths: List[str] | None = None) -> Dict[str, Any]:
    return {
        "HUNT_CANDIDATE_ID": cid,
        "EVIDENCE_PATHS": [f"findings/{fid}.md"],
        "OBSERVED_BEHAVIOR": f"observed for {fid}",
        "POSSIBLE_INVARIANT_VIOLATION": "possible same-invariant violation",
        "AFFECTED_COMPONENT": "card_ab_hold",
        "CONFIDENCE": "high",
        "PROPOSED_FINDING_ID": fid,
        "EXPECTED_CHANGED_PATHS": paths or [f"app/{fid}.py"],
        "CLASSIFICATION": "IMPLEMENTATION_BUG",
        "CHOSEN_ROUTE": "ROUTE_A",
        "RATIONALE": "test",
    }


def _fix_branch(case: Path, fid: str, path: str, content: str, green: bool = True) -> Dict[str, Any]:
    family_fanout.set_branch_red(case, finding_id=fid, red_status="RED_CONFIRMED")
    family_fanout.apply_branch_local_change(
        case, finding_id=fid, relative_path=path, content=content
    )
    patch = f"--- a/{path}\n+++ b/{path}\n+{content}\n"
    return family_fanout.finalize_branch_patch(
        case,
        finding_id=fid,
        changed_paths=[path],
        patch_body=patch,
        green_pass=green,
        summary=f"fix {fid}",
    )


def _close_happy_path(case: Path, fids: List[str], combined_green: bool = True) -> Dict[str, Any]:
    main = case / "main_worktree"
    integ = family_fanout.integrate_branch_patches(
        case,
        main_workspace=main,
        finding_ids=fids,
        combined_green_pass=combined_green,
        unrelated_dirty=[".idea/workspace.xml"],
    )
    if not combined_green:
        return {"integ": integ}
    family_fanout.write_family_green_report(
        case,
        root_green=True,
        all_blocking_branch_greens=True,
        patch_integration=True,
        family_invariant_test=True,
        relevant_regression_tests=True,
    )
    family_fanout.write_family_fanin(case)
    family_fanout.run_learning(case)
    family_fanout.write_family_human_summary(
        case,
        original_bug="Таймер/эпоха вела себя неправильно на ENTER.",
        invariant_plain=_invariant_kwargs()["plain_language"],
        hunt_findings=fids,
        same_family=fids,
        separate_roots=[],
        branch_fixes={f: f"Исправлен {f}" for f in fids},
        branch_files={f: [f"app/{f}.py"] for f in fids},
        how_combined="Патчи применены в детерминированном порядке Integration Operator.",
        family_tests="FAMILY GREEN PASS",
        unresolved="Нужен визуальный git diff.",
        review_diff="Проверьте незакоммиченные файлы episode.",
        unrelated_dirty=[".idea/workspace.xml"],
    )
    closed = family_fanout.close_family(case)
    return {"integ": integ, "closed": closed}


# --- Family flows ---


def family01() -> Result:
    case = _case("family01")
    _bootstrap(case)
    family_fanout.validate_hunt_result({"HUNT_RESULT": "CLEAR", "CANDIDATES": []})
    # no siblings → empty integration + close
    (bug_family.family_dir(case) / "INTEGRATION.json").write_text(
        json.dumps({"INTEGRATION_STATUS": "PASS", "APPLIED_PATCHES": [], "CONFLICTS": []})
        + "\n",
        encoding="utf-8",
    )
    bug_family.update_family_status(case, integration_status="PASS")
    family_fanout.write_family_green_report(
        case,
        root_green=True,
        all_blocking_branch_greens=True,
        patch_integration=True,
        family_invariant_test=True,
        relevant_regression_tests=True,
    )
    family_fanout.write_family_fanin(case)
    family_fanout.run_learning(case)
    family_fanout.write_family_human_summary(
        case,
        original_bug="Корневой баг",
        invariant_plain=_invariant_kwargs()["plain_language"],
        hunt_findings=[],
        same_family=[],
        separate_roots=[],
        branch_fixes={},
        branch_files={},
        how_combined="Нет sibling-патчей",
        family_tests="PASS",
        unresolved="нет",
        review_diff="diff корня",
    )
    closed = family_fanout.close_family(case)
    ok = closed["FAMILY_STATUS"] == "CLOSED_FIXED_VERIFIED"
    return ok, "root fixed, hunt CLEAR → family closes", "RUNTIME_UNIT"


def family02() -> Result:
    case = _case("family02")
    _bootstrap(case)
    for cid, fid, path in (
        ("HC-7", "PBH-007", "app/pbh007.py"),
        ("HC-8", "PBH-008", "app/pbh008.py"),
    ):
        out = family_fanout.classify_relation(
            case,
            candidate=_cand(cid, fid, [path]),
            relation="SAME_INVARIANT_FINDING",
            rationale="same",
            finding_id=fid,
            expected_changed_paths=[path],
        )
        family_fanout.run_classifier_for_branch(
            case, finding_id=fid, classification="IMPLEMENTATION_BUG", chosen_route="ROUTE_A"
        )
        _fix_branch(case, fid, path, f"# {fid}\n")
    deps = bug_family.record_write_set_plan(
        case, {"PBH-007": ["app/pbh007.py"], "PBH-008": ["app/pbh008.py"]}
    )
    closed = _close_happy_path(case, ["PBH-007", "PBH-008"])
    hs = (case / "results" / "HUMAN_SUMMARY.md").read_text(encoding="utf-8")
    ok = (
        deps["PARALLEL_IMPLEMENTATION_ALLOWED"] is True
        and closed["closed"]["FAMILY_STATUS"] == "CLOSED_FIXED_VERIFIED"
        and "PBH-007" in hs
        and "PBH-008" in hs
        and (case / "results" / "FAMILY-FANIN.md").exists()
    )
    return ok, "root + two same-invariant branches → one family report", "RUNTIME_UNIT"


def family03() -> Result:
    case = _case("family03")
    _bootstrap(case)
    family_fanout.classify_relation(
        case,
        candidate=_cand("HC-1", "F-RED"),
        relation="SAME_INVARIANT_FINDING",
        rationale="x",
        finding_id="F-RED",
    )
    family_fanout.run_classifier_for_branch(
        case, finding_id="F-RED", classification="IMPLEMENTATION_BUG", chosen_route="ROUTE_A"
    )
    family_fanout.set_branch_red(case, finding_id="F-RED", red_status="RED_FAILED")
    fam = bug_family.load_family(case)
    open_b = bug_family.blocking_open_branches(case)
    # ensure no patch workspace implementation
    no_patch = not (case / "branches" / "F-RED" / "PATCH.diff").exists()
    ok = fam["FAMILY_STATUS"] == "OPEN_BLOCKED" and open_b and no_patch
    return ok, "same-invariant RED fails → no implementation, OPEN_BLOCKED", "RUNTIME_UNIT"


def family04() -> Result:
    case = _case("family04")
    _bootstrap(case)
    family_fanout.classify_relation(
        case,
        candidate=_cand("HC-1", "F-G"),
        relation="SAME_INVARIANT_FINDING",
        rationale="x",
        finding_id="F-G",
    )
    _fix_branch(case, "F-G", "app/fg.py", "# fail green\n", green=False)
    try:
        family_fanout.close_family(case)
        return False, "should not close", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError:
        fam = bug_family.load_family(case)
        # family may still be FANOUT_ACTIVE; branch GREEN_FAILED blocks
        open_b = bug_family.blocking_open_branches(case)
        ok = any(b["FINDING_ID"] == "F-G" for b in open_b)
        return ok, "branch GREEN fails → family not closed", "RUNTIME_UNIT"


def family05() -> Result:
    case = _case("family05")
    _bootstrap(case)
    out = family_fanout.classify_relation(
        case,
        candidate=_cand("HC-N", "NRC-1"),
        relation="NEW_ROOT_CAUSE",
        rationale="different root",
        finding_id="NRC-1",
        linked_case_id="BUGCASE-LINKED-DEMO",
    )
    # parent may close without blocking
    (bug_family.family_dir(case) / "INTEGRATION.json").write_text(
        json.dumps({"INTEGRATION_STATUS": "PASS", "APPLIED_PATCHES": [], "CONFLICTS": []})
        + "\n",
        encoding="utf-8",
    )
    bug_family.update_family_status(case, integration_status="PASS")
    family_fanout.write_family_green_report(
        case,
        root_green=True,
        all_blocking_branch_greens=True,
        patch_integration=True,
        family_invariant_test=True,
        relevant_regression_tests=True,
    )
    family_fanout.write_family_fanin(case)
    family_fanout.run_learning(case)
    family_fanout.write_family_human_summary(
        case,
        original_bug="root",
        invariant_plain=_invariant_kwargs()["plain_language"],
        hunt_findings=["NRC-1"],
        same_family=[],
        separate_roots=["BUGCASE-LINKED-DEMO"],
        branch_fixes={},
        branch_files={},
        how_combined="n/a",
        family_tests="PASS",
        unresolved="linked case follow-up",
        review_diff="diff",
    )
    closed = family_fanout.close_family(case)
    ok = (
        out["BLOCKS_FAMILY_CLOSURE"] is False
        and Path(out["HANDOFF_PATH"]).exists()
        and closed["FAMILY_STATUS"] == "CLOSED_FIXED_VERIFIED"
        and "BUGCASE-LINKED-DEMO" in (case / "results" / "HUMAN_SUMMARY.md").read_text(encoding="utf-8")
    )
    return ok, "new root cause → linked case; parent may close", "RUNTIME_UNIT"


def family06() -> Result:
    case = _case("family06")
    _bootstrap(case)
    out = family_fanout.classify_relation(
        case,
        candidate=_cand("HC-FP", "FP-1"),
        relation="FALSE_POSITIVE",
        rationale="not a bug",
        finding_id="FP-1",
    )
    ok = (
        out["IMPLEMENTATION"] is False
        and (case / "findings" / "FP-1.md").exists()
        and not (case / "branches" / "FP-1" / "PATCH.diff").exists()
    )
    return ok, "false positive → rejected record, no implementation", "RUNTIME_UNIT"


def family07() -> Result:
    case = _case("family07")
    _bootstrap(case)
    out = family_fanout.classify_relation(
        case,
        candidate=_cand("HC-I", "INC-1"),
        relation="INCONCLUSIVE",
        rationale="missing logs",
        finding_id="INC-1",
    )
    fam = bug_family.load_family(case)
    ok = out["FAMILY_STATUS"] == "OPEN_BLOCKED" and fam["FAMILY_STATUS"] == "OPEN_BLOCKED"
    return ok, "inconclusive → family OPEN_BLOCKED", "RUNTIME_UNIT"


def family08() -> Result:
    case = _case("family08")
    _bootstrap(case)
    deps = bug_family.record_write_set_plan(
        case,
        {
            "A": ["app/shared.py", "app/a.py"],
            "B": ["app/shared.py", "app/b.py"],
        },
    )
    try:
        bug_family.assert_no_concurrent_overlapping_writes(
            active_main_writers=["A", "B"],
            write_sets={"A": ["app/shared.py"], "B": ["app/shared.py"]},
        )
        return False, "should block", "RUNTIME_UNIT"
    except bug_family.BugFamilyError as exc:
        ok = (
            exc.code == "BLOCKED_CONCURRENT_OVERLAPPING_MAIN_WORKTREE_WRITES"
            and deps["PARALLEL_IMPLEMENTATION_ALLOWED"] is False
            and deps["SERIALIZATION_ORDER"] == ["A", "B"]
        )
        return ok, "overlapping write sets → no concurrent main writes", "RUNTIME_UNIT"


def family09() -> Result:
    case = _case("family09")
    _bootstrap(case)
    deps = bug_family.record_write_set_plan(
        case, {"A": ["app/a.py"], "B": ["app/b.py"]}
    )
    bug_family.assert_no_concurrent_overlapping_writes(
        active_main_writers=["A", "B"],
        write_sets={"A": ["app/a.py"], "B": ["app/b.py"]},
    )
    ok = deps["PARALLEL_IMPLEMENTATION_ALLOWED"] is True and deps["PARALLEL_ALLOWED_PAIRS"]
    return ok, "disjoint branch work → parallel allowed", "RUNTIME_UNIT"


def family10() -> Result:
    case = _case("family10")
    _bootstrap(case)
    for fid, path in (("F1", "app/f1.py"), ("F2", "app/f2.py")):
        family_fanout.classify_relation(
            case,
            candidate=_cand(f"HC-{fid}", fid, [path]),
            relation="SAME_INVARIANT_FINDING",
            rationale="x",
            finding_id=fid,
            expected_changed_paths=[path],
        )
        _fix_branch(case, fid, path, f"# {fid}\n", green=True)
    integ = family_fanout.integrate_branch_patches(
        case,
        main_workspace=case / "main_worktree",
        finding_ids=["F1", "F2"],
        combined_green_pass=False,
    )
    try:
        family_fanout.close_family(case)
        closed = False
    except family_fanout.FamilyFanoutError:
        closed = False
    else:
        closed = True
    ok = (
        integ["INTEGRATION_STATUS"] == "FAMILY_GREEN_FAILED"
        and integ.get("FAMILY_CLOSURE") == "FORBIDDEN"
        and closed is False
    )
    return ok, "combined patch fails → family closure forbidden", "RUNTIME_UNIT"


def family11() -> Result:
    case = _case("family11")
    _bootstrap(case)
    family_fanout.classify_relation(
        case,
        candidate=_cand("HC-1", "OPEN-1"),
        relation="SAME_INVARIANT_FINDING",
        rationale="x",
        finding_id="OPEN-1",
    )
    try:
        family_fanout.write_family_fanin(case)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_FAMILY_FANIN_OPEN_BRANCHES",
            "fan-in with open blocking branch → rejected",
            "RUNTIME_UNIT",
        )


def family12() -> Result:
    case = _case("family12")
    _bootstrap(case)
    family_fanout.classify_relation(
        case,
        candidate=_cand("HC-1", "OPEN-2"),
        relation="SAME_INVARIANT_FINDING",
        rationale="x",
        finding_id="OPEN-2",
    )
    try:
        family_fanout.run_learning(case)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_LEARNING_BEFORE_FAMILY_READY",
            "learning before readiness → rejected",
            "RUNTIME_UNIT",
        )


def family13() -> Result:
    case = _case("family13")
    _bootstrap(case)
    for fid in ("B1", "B2"):
        family_fanout.classify_relation(
            case,
            candidate=_cand(f"HC-{fid}", fid),
            relation="SAME_INVARIANT_FINDING",
            rationale="x",
            finding_id=fid,
            expected_changed_paths=[f"app/{fid}.py"],
        )
        _fix_branch(case, fid, f"app/{fid}.py", f"# {fid}\n")
    _close_happy_path(case, ["B1", "B2"])
    text = (case / "results" / "HUMAN_SUMMARY.md").read_text(encoding="utf-8")
    ok = "B1" in text and "B2" in text and "Что исправили в каждой ветке" in text
    return ok, "human summary contains every branch", "RUNTIME_UNIT"


def family14() -> Result:
    case = _case("family14")
    _bootstrap(case)
    family_fanout.classify_relation(
        case,
        candidate=_cand("HC-1", "X1", ["app/x1.py"]),
        relation="SAME_INVARIANT_FINDING",
        rationale="x",
        finding_id="X1",
        expected_changed_paths=["app/x1.py"],
    )
    _fix_branch(case, "X1", "app/x1.py", "# x\n")
    integ = family_fanout.integrate_branch_patches(
        case,
        main_workspace=case / "main_worktree",
        finding_ids=["X1"],
        combined_green_pass=True,
        unrelated_dirty=[".idea/workspace.xml"],
    )
    classified = control_model.classify_worktree_changes(
        episode_paths={"app/x1.py"},
        all_dirty_paths={"app/x1.py", ".idea/workspace.xml"},
    )
    ok = (
        ".idea/workspace.xml" in (integ.get("UNRELATED_DIRTY_PRESERVED") or [])
        and (case / "main_worktree" / ".idea" / "workspace.xml").exists()
        and ".idea/workspace.xml"
        in classified["РАНЕЕ_СУЩЕСТВОВАВШИЕ_НЕСВЯЗАННЫЕ_ИЗМЕНЕНИЯ"]
    )
    return ok, "unrelated dirty files preserved and separated", "RUNTIME_UNIT"


def family15() -> Result:
    codes = [
        control_model.reject_forbidden_shell_command("git commit -m x"),
        control_model.reject_forbidden_shell_command("git push"),
        control_model.reject_forbidden_shell_command("kubectl apply -f x"),
    ]
    ok = codes == [
        "BLOCKED_GIT_COMMIT_FORBIDDEN",
        "BLOCKED_GIT_PUSH_FORBIDDEN",
        "BLOCKED_DEPLOY_FORBIDDEN",
    ]
    return ok, "no commit/push/deploy", "RUNTIME_UNIT"


def family16() -> Result:
    case = _case("family16-pbh006")
    # Synthetic resume fixture — does NOT touch real BUGCASE-PBH-006
    green = case / "results" / "GREEN-PBH-006.md"
    green.write_text("GREEN_STATUS: GREEN_CONFIRMED\nFINDING_ID: PBH-006\n", encoding="utf-8")
    candidates = [
        _cand("HC-007", "PBH-007", ["app/manager.py"]),
        _cand("HC-008", "PBH-008", ["app/process_ab_setup.py"]),
    ]
    # Disjoint-ish for plan; still same family
    res = family_fanout.resume_family_fanout_from_root_green(
        case,
        case_id="BUGCASE-PBH-006",
        root_finding_id="PBH-006",
        root_green_path=green,
        hunt_candidates=candidates,
        relations={
            "HC-007": "SAME_INVARIANT_FINDING",
            "HC-008": "SAME_INVARIANT_FINDING",
        },
        execution_mode=MODE,
        proof_root=case,
        invariant_kwargs=_invariant_kwargs(),
    )
    for fid, path in (("PBH-007", "app/manager.py"), ("PBH-008", "app/process_ab_setup.py")):
        _fix_branch(case, fid, path, f"# {fid}\n")
    bug_family.record_write_set_plan(
        case,
        {
            "PBH-007": ["app/manager.py"],
            "PBH-008": ["app/process_ab_setup.py"],
        },
    )
    _close_happy_path(case, ["PBH-007", "PBH-008"])
    ok = (
        res["ROOT_GREEN_REUSED"] is True
        and res["MODE"] == "resume-family-fanout"
        and (case / "findings" / "PBH-007.md").exists()
        and (case / "findings" / "PBH-008.md").exists()
        and bug_family.load_family(case)["FAMILY_STATUS"] == "CLOSED_FIXED_VERIFIED"
    )
    return ok, "resume PBH-006 from root GREEN → 007/008 fanout (harness)", "RUNTIME_UNIT"


# --- Invariant tests ---


def inv001() -> Result:
    case = _case("inv001")
    _bootstrap(case)
    out = family_fanout.classify_relation(
        case,
        candidate=_cand("HC-1", "INV-F1"),
        relation="SAME_INVARIANT_FINDING",
        rationale="x",
        finding_id="INV-F1",
    )
    return bool(out.get("FINDING_ID")), "every same-invariant hunt finding gets FINDING_ID", "INVARIANT"


def inv002() -> Result:
    case = _case("inv002")
    _bootstrap(case)
    family_fanout.classify_relation(
        case,
        candidate=_cand("HC-1", "INV-F2"),
        relation="SAME_INVARIANT_FINDING",
        rationale="x",
        finding_id="INV-F2",
    )
    r = family_fanout.run_classifier_for_branch(
        case, finding_id="INV-F2", classification="IMPLEMENTATION_BUG", chosen_route="ROUTE_A"
    )
    return r["BRANCH"]["CLASSIFICATION"] == "IMPLEMENTATION_BUG", "classifier on same-invariant", "INVARIANT"


def inv003() -> Result:
    case = _case("inv003")
    _bootstrap(case)
    family_fanout.classify_relation(
        case,
        candidate=_cand("HC-1", "SIB"),
        relation="SAME_INVARIANT_FINDING",
        rationale="x",
        finding_id="SIB",
    )
    try:
        family_fanout.assert_root_green_cannot_close_open_sibling(case)
        return False, "should block", "INVARIANT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_ROOT_GREEN_CANNOT_CLOSE_OPEN_SIBLING",
            "root GREEN cannot close open sibling",
            "INVARIANT",
        )


def inv004() -> Result:
    return family11()  # same assertion


def inv005() -> Result:
    case = _case("inv005")
    _bootstrap(case)
    family_fanout.classify_relation(
        case,
        candidate=_cand("HC-1", "BG"),
        relation="SAME_INVARIANT_FINDING",
        rationale="x",
        finding_id="BG",
    )
    _fix_branch(case, "BG", "app/bg.py", "# ok\n", green=True)
    # branch green alone — family green report must still be required
    try:
        family_fanout.assert_branch_cannot_close_family(case, "BG")
        return False, "should block", "INVARIANT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            "BRANCH" in exc.code,
            "branch GREEN does not replace family GREEN",
            "INVARIANT",
        )


def inv006() -> Result:
    try:
        family_fanout.validate_hunt_result(
            {
                "HUNT_RESULT": "CANDIDATES_FOUND",
                "CANDIDATES": [_cand("HC-1", "X")],
                "HUNTER_IMPLEMENTED_FIX": True,
            }
        )
        return False, "should block", "INVARIANT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_HUNTER_CANNOT_IMPLEMENT",
            "hunter cannot implement",
            "INVARIANT",
        )


def inv007() -> Result:
    return inv005()


def inv008() -> Result:
    return family12()


def inv009() -> Result:
    return family08()


def inv010() -> Result:
    case = _case("inv010")
    _bootstrap(case)
    (bug_family.family_dir(case) / "INTEGRATION.json").write_text(
        json.dumps({"INTEGRATION_STATUS": "PASS", "APPLIED_PATCHES": [], "CONFLICTS": []})
        + "\n",
        encoding="utf-8",
    )
    bug_family.update_family_status(case, integration_status="PASS")
    family_fanout.write_family_green_report(
        case,
        root_green=True,
        all_blocking_branch_greens=True,
        patch_integration=True,
        family_invariant_test=True,
        relevant_regression_tests=True,
    )
    family_fanout.write_family_fanin(case)
    family_fanout.run_learning(case)
    family_fanout.write_family_human_summary(
        case,
        original_bug="x",
        invariant_plain=_invariant_kwargs()["plain_language"],
        hunt_findings=[],
        same_family=[],
        separate_roots=[],
        branch_fixes={},
        branch_files={},
        how_combined="n/a",
        family_tests="PASS",
        unresolved="n/a",
        review_diff="diff",
    )
    closed = family_fanout.close_family(case)
    ok = (
        closed["COMMIT_CREATED"] is False
        and closed["WORKTREE_STATUS"] == "UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW"
    )
    return ok, "final worktree remains uncommitted", "INVARIANT"


def shadow_disabled() -> Result:
    st, details = family_policy.check_family_fanout_gate(
        execution_mode="CONTROLLED_LIVE_UNCOMMITTED",
        proof_root=Path(".tmp/opsx-bug-team-harness/x"),
    )
    ok = (
        st == "BLOCKED_FAMILY_FANOUT_SHADOW_DISABLED"
        and family_policy.bug_family_fanout_enabled() is False
        and details.get("CURRENT_ACTIVE_RUNTIME") == "ACTIVE_V1"
    )
    return ok, "V8 shadow disabled by default; ACTIVE_V1 unchanged", "CONTRACT_STATIC"


def policy_file() -> Result:
    pol = family_policy.load_policy()
    needed = {
        "HUNT_RESULT_TYPES",
        "RELATION_TYPES",
        "BLOCKING_RULES",
        "BRANCH_TRANSITIONS",
        "FAMILY_CLOSURE_CONDITIONS",
        "LEARNING_CONDITIONS",
        "INTEGRATION_RULES",
    }
    ok = needed.issubset(pol.keys()) and pol.get("BUG_FAMILY_FANOUT_ENABLED") is False
    return ok, "canonical BUG_FAMILY_FANOUT_POLICY.json present", "CONTRACT_STATIC"


TESTS: List[Tuple[str, Callable[[], Result]]] = [
    ("V8-FAMILY-01", family01),
    ("V8-FAMILY-02", family02),
    ("V8-FAMILY-03", family03),
    ("V8-FAMILY-04", family04),
    ("V8-FAMILY-05", family05),
    ("V8-FAMILY-06", family06),
    ("V8-FAMILY-07", family07),
    ("V8-FAMILY-08", family08),
    ("V8-FAMILY-09", family09),
    ("V8-FAMILY-10", family10),
    ("V8-FAMILY-11", family11),
    ("V8-FAMILY-12", family12),
    ("V8-FAMILY-13", family13),
    ("V8-FAMILY-14", family14),
    ("V8-FAMILY-15", family15),
    ("V8-FAMILY-16", family16),
    ("INV-FAMILY-001", inv001),
    ("INV-FAMILY-002", inv002),
    ("INV-FAMILY-003", inv003),
    ("INV-FAMILY-004", inv004),
    ("INV-FAMILY-005", inv005),
    ("INV-FAMILY-006", inv006),
    ("INV-FAMILY-007", inv007),
    ("INV-FAMILY-008", inv008),
    ("INV-FAMILY-009", inv009),
    ("INV-FAMILY-010", inv010),
    ("V8-SHADOW-01", shadow_disabled),
    ("V8-POLICY-01", policy_file),
]


def main() -> int:
    print("=== Corrective V8 tests (family fanout shadow) ===")
    print(f"BUG_FAMILY_FANOUT_ENABLED={family_policy.bug_family_fanout_enabled()}")
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
    out = HARNESS / "RESULTS.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"total": total, "passed": passed, "failed": failed, "rows": rows}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
