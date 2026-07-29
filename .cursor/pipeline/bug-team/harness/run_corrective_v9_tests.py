# -*- coding: utf-8 -*-
"""Corrective V9 tests — invariant proof, fan-in, learning, parallelism.

Shadow only. Does not enable BUG_FAMILY_FANOUT or touch real bug cases.
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

from runtime import (  # noqa: E402
    bug_family,
    execution_identity,
    family_fanout,
    family_policy,
    invariant_proof,
    parallelism,
)

Result = Tuple[bool, str, str]
HARNESS = Path(".tmp/opsx-bug-team-harness/corrective-v9-unit")
MODE = family_policy.CONTROLLED_TEST_MODE


def _case(name: str) -> Path:
    p = HARNESS / name
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    (p / "results").mkdir(parents=True, exist_ok=True)
    (p / "findings").mkdir(parents=True, exist_ok=True)
    return p


def _inv_kwargs(**over: Any) -> Dict[str, Any]:
    base = {
        "plain_language": (
            "Когда эпоха владеет переходом, FAIL→OFF случается ровно один раз на ENTER."
        ),
        "technical": (
            "When epoch management owns the transition, FAIL→OFF must occur "
            "exactly once at the epoch boundary, before conflicting writers can "
            "run, and must not repeat during later PENDING ticks."
        ),
        "scope": "card_ab_hold epoch ENTER fail-off writers",
        "entry_conditions": "phase non-NULL after start_epoch_on_enable",
        "required_behavior": (
            "FAIL→OFF must occur exactly once at epoch ENTER before PENDING ticks"
        ),
        "forbidden_behavior": "skip FAIL→OFF on ENTER; re-apply every PENDING tick",
        "known_writers": ["process_ab_setup", "process_ab_epoch"],
        "known_readers": ["shop-runner"],
        "proof_from_root": "ROOT GREEN + RED for ENTER FAIL→OFF",
        "hunt_scope": "epoch ENTER / FAIL→OFF neighborhood",
    }
    base.update(over)
    return base


def _seed_root_proof(case: Path, family: Dict[str, Any]) -> None:
    (case / "results" / f"GREEN-{family['ROOT_FINDING_ID']}.md").write_text(
        "GREEN_STATUS: GREEN_CONFIRMED\n", encoding="utf-8"
    )
    (case / "results" / f"RED-{family['ROOT_FINDING_ID']}.md").write_text(
        "RED_STATUS: RED_CONFIRMED\n", encoding="utf-8"
    )
    invariant_proof.write_root_green_proof(
        case,
        invariant_id=family["INVARIANT_ID"],
        root_finding_id=family["ROOT_FINDING_ID"],
        root_red_claims=["FAIL→OFF missing on epoch ENTER"],
        root_failure_behavior="Classification FAIL keywords stay ON through WARM_UP",
        root_fix_claims=["apply FAIL→OFF on epoch-managed ENTER"],
        root_green_claims=[
            "FAIL→OFF must occur exactly once at epoch ENTER",
            "GREEN confirmed for ENTER fail-off",
        ],
        required_behavior_proven=[
            "FAIL→OFF must occur exactly once at epoch ENTER before PENDING ticks"
        ],
        forbidden_behavior_proven=["skip FAIL→OFF on ENTER"],
        evidence_paths={
            "ROOT_GREEN": f"results/GREEN-{family['ROOT_FINDING_ID']}.md",
            "ROOT_RED": f"results/RED-{family['ROOT_FINDING_ID']}.md",
        },
        scope_tokens=["epoch", "enter", "fail", "off", "card_ab_hold"],
    )


def _bootstrap(case: Path) -> Dict[str, Any]:
    family = family_fanout.bootstrap_family_after_root_green(
        case,
        case_id="C-V9",
        root_finding_id="ROOT-1",
        execution_mode=MODE,
        proof_root=case,
        invariant_kwargs=_inv_kwargs(),
    )
    return family


def _cand(cid: str, fid: str, paths: List[str] | None = None) -> Dict[str, Any]:
    return {
        "HUNT_CANDIDATE_ID": cid,
        "EVIDENCE_PATHS": [f"findings/{fid}.md"],
        "OBSERVED_BEHAVIOR": f"observed {fid}",
        "POSSIBLE_INVARIANT_VIOLATION": "same-invariant risk",
        "AFFECTED_COMPONENT": "card_ab_hold",
        "CONFIDENCE": "high",
        "PROPOSED_FINDING_ID": fid,
        "EXPECTED_CHANGED_PATHS": paths or [f"app/{fid}.py"],
        "CLASSIFICATION": "IMPLEMENTATION_BUG",
        "CHOSEN_ROUTE": "ROUTE_A",
        "RATIONALE": "v9",
    }


def _fix_branch(case: Path, fid: str, path: str, green: bool = True) -> None:
    family_fanout.set_branch_red(case, finding_id=fid, red_status="RED_CONFIRMED")
    family_fanout.apply_branch_local_change(
        case, finding_id=fid, relative_path=path, content=f"# {fid}\n"
    )
    family_fanout.finalize_branch_patch(
        case,
        finding_id=fid,
        changed_paths=[path],
        patch_body=f"--- a/{path}\n+++ b/{path}\n+fixed\n",
        green_pass=green,
        summary=f"fix {fid}",
    )


def _two_branch_ready(case: Path) -> None:
    family = _bootstrap(case)
    _seed_root_proof(case, family)
    # re-capture with proof present
    family_fanout.capture_invariant(
        case, invariant_id=family["INVARIANT_ID"], **_inv_kwargs(), require_root_proof=True
    )
    cands = [_cand("HC-A", "A", ["app/a.py"]), _cand("HC-B", "B", ["app/b.py"])]
    family_fanout.validate_hunt_result(
        {"HUNT_RESULT": "CANDIDATES_FOUND", "CANDIDATES": cands}, case_root=case
    )
    for c, path in ((cands[0], "app/a.py"), (cands[1], "app/b.py")):
        out = family_fanout.classify_relation(
            case,
            candidate=c,
            relation="SAME_INVARIANT_FINDING",
            rationale="same",
            finding_id=c["PROPOSED_FINDING_ID"],
            expected_changed_paths=[path],
        )
        family_fanout.run_classifier_for_branch(
            case,
            finding_id=out["FINDING_ID"],
            classification="IMPLEMENTATION_BUG",
            chosen_route="ROUTE_A",
        )
        _fix_branch(case, out["FINDING_ID"], path)
    family_fanout.integrate_branch_patches(
        case,
        main_workspace=case / "main_worktree",
        finding_ids=["A", "B"],
        combined_green_pass=True,
        unrelated_dirty=[".idea/workspace.xml"],
    )
    family_fanout.write_family_green_report(
        case,
        root_green=True,
        all_blocking_branch_greens=True,
        patch_integration=True,
        family_invariant_test=True,
        relevant_regression_tests=True,
    )


# --- INV ---


def inv01() -> Result:
    case = _case("inv01")
    family = _bootstrap(case)
    _seed_root_proof(case, family)
    family_fanout.capture_invariant(
        case, invariant_id=family["INVARIANT_ID"], **_inv_kwargs(), require_root_proof=True
    )
    return True, "valid invariant agrees with root GREEN", "RUNTIME_UNIT"


def inv02() -> Result:
    case = _case("inv02")
    family = _bootstrap(case)
    _seed_root_proof(case, family)
    try:
        family_fanout.capture_invariant(
            case,
            invariant_id=family["INVARIANT_ID"],
            **_inv_kwargs(
                required_behavior="must never apply FAIL→OFF on ENTER",
            ),
            require_root_proof=True,
            contradicts_root_green=True,
        )
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH",
            "invariant contradicts root GREEN → rejected",
            "RUNTIME_UNIT",
        )


def inv03() -> Result:
    case = _case("inv03")
    family = _bootstrap(case)
    _seed_root_proof(case, family)
    try:
        family_fanout.capture_invariant(
            case,
            invariant_id=family["INVARIANT_ID"],
            **_inv_kwargs(
                required_behavior="billing must rotate customer secrets nightly xyz",
            ),
            require_root_proof=True,
            introduces_unrelated_rule=True,
        )
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH",
            "unsupported behavior → rejected",
            "RUNTIME_UNIT",
        )


def inv04() -> Result:
    case = _case("inv04")
    family = _bootstrap(case)
    _seed_root_proof(case, family)
    # stale hash
    proof = json.loads(invariant_proof.root_proof_path(case).read_text(encoding="utf-8"))
    proof["EVIDENCE_HASHES"]["ROOT_GREEN"] = "0" * 64
    invariant_proof.root_proof_path(case).write_text(json.dumps(proof, indent=2) + "\n")
    try:
        family_fanout.capture_invariant(
            case, invariant_id=family["INVARIANT_ID"], **_inv_kwargs(), require_root_proof=True
        )
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH"
            and "stale" in (exc.detail or ""),
            "stale evidence hash → rejected",
            "RUNTIME_UNIT",
        )


def inv05() -> Result:
    case = _case("inv05")
    family = _bootstrap(case)
    _seed_root_proof(case, family)
    try:
        family_fanout.capture_invariant(
            case,
            invariant_id=family["INVARIANT_ID"],
            **_inv_kwargs(scope="unrelated kubernetes kubernetes kubernetes kubernetes kubernetes"),
            require_root_proof=True,
        )
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_INVARIANT_ROOT_PROOF_MISMATCH",
            "unrelated scope → rejected",
            "RUNTIME_UNIT",
        )


# --- FANIN ---


def fanin01() -> Result:
    case = _case("fanin01")
    _two_branch_ready(case)
    out = family_fanout.write_family_fanin(case)
    data = json.loads((case / "results" / "FAMILY-FANIN.json").read_text(encoding="utf-8"))
    ok = (
        out["READY"]
        and data["FAMILY_CLOSURE_READINESS"] == "READY_FOR_FAMILY_CLOSURE"
        and all(b.get("PATCH_HASH") for b in data["BRANCHES"] if b["RELATION_TO_INVARIANT"] == "SAME_INVARIANT_FINDING")
    )
    return ok, "complete root + two branches → READY", "RUNTIME_UNIT"


def fanin02() -> Result:
    case = _case("fanin02")
    _two_branch_ready(case)
    bug_family.upsert_branch(case, {"FINDING_ID": "A", "PATCH_HASH": None})
    try:
        family_fanout.write_family_fanin(case)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_INCOMPLETE_FAMILY_FANIN",
            "missing branch patch hash → rejected",
            "RUNTIME_UNIT",
        )


def fanin03() -> Result:
    case = _case("fanin03")
    _two_branch_ready(case)
    bug_family.upsert_branch(case, {"FINDING_ID": "A", "RED_STATUS": None, "RED_EVIDENCE_HASH": None})
    try:
        family_fanout.write_family_fanin(case)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return exc.code == "BLOCKED_INCOMPLETE_FAMILY_FANIN", "missing branch RED → rejected", "RUNTIME_UNIT"


def fanin04() -> Result:
    case = _case("fanin04")
    _two_branch_ready(case)
    bug_family.upsert_branch(
        case, {"FINDING_ID": "B", "GREEN_STATUS": None, "GREEN_REPORT_HASH": None}
    )
    try:
        family_fanout.write_family_fanin(case)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_INCOMPLETE_FAMILY_FANIN",
            "missing branch GREEN → rejected",
            "RUNTIME_UNIT",
        )


def fanin05() -> Result:
    case = _case("fanin05")
    _two_branch_ready(case)
    # add orphan hunt candidate
    hunt = json.loads((bug_family.family_dir(case) / "HUNT_CANDIDATES.json").read_text())
    hunt["CANDIDATES"].append(_cand("HC-ORPHAN", "ORPHAN"))
    (bug_family.family_dir(case) / "HUNT_CANDIDATES.json").write_text(json.dumps(hunt, indent=2))
    try:
        family_fanout.write_family_fanin(case)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_INCOMPLETE_FAMILY_FANIN",
            "omitted hunt candidate → rejected",
            "RUNTIME_UNIT",
        )


def fanin06() -> Result:
    case = _case("fanin06")
    _bootstrap(case)
    family_fanout.classify_relation(
        case,
        candidate=_cand("HC-1", "OPEN"),
        relation="SAME_INVARIANT_FINDING",
        rationale="x",
        finding_id="OPEN",
    )
    try:
        family_fanout.write_family_fanin(case)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_FAMILY_FANIN_OPEN_BRANCHES",
            "open blocking branch → rejected",
            "RUNTIME_UNIT",
        )


def fanin07() -> Result:
    case = _case("fanin07")
    _two_branch_ready(case)
    family_fanout.write_family_fanin(case)
    data = json.loads((case / "results" / "FAMILY-FANIN.json").read_text(encoding="utf-8"))
    md = (case / "results" / "FAMILY-FANIN.md").read_text(encoding="utf-8")
    ok = data["BUG_FAMILY_ID"] in md and data["FAMILY_CLOSURE_READINESS"] in md
    return ok, "Markdown projection matches canonical JSON", "RUNTIME_UNIT"


# --- LEARN ---


def learn01() -> Result:
    case = _case("learn01")
    _two_branch_ready(case)
    family_fanout.write_family_fanin(case)
    packet = family_fanout.run_learning(case)
    ok = packet["LEARNING_STATUS"] == "COMPLETE" and "MISSED_ORIGINAL_DETECTION_POINTS" in packet
    return ok, "complete two-branch family → learning accepted", "RUNTIME_UNIT"


def learn02() -> Result:
    case = _case("learn02")
    _two_branch_ready(case)
    family_fanout.write_family_fanin(case)
    packet = family_fanout.run_learning(case)
    del packet["ALL_SAME_INVARIANT_FINDINGS"]
    try:
        family_fanout.validate_learning_packet(packet, case)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_LEARNING_PACKET_INCOMPLETE",
            "missing ALL_SAME_INVARIANT_FINDINGS → rejected",
            "RUNTIME_UNIT",
        )


def learn03() -> Result:
    case = _case("learn03")
    _two_branch_ready(case)
    family_fanout.write_family_fanin(case)
    packet = family_fanout.run_learning(case)
    del packet["MISSED_ORIGINAL_DETECTION_POINTS"]
    try:
        family_fanout.validate_learning_packet(packet)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_LEARNING_PACKET_INCOMPLETE",
            "missing MISSED_ORIGINAL_DETECTION_POINTS → rejected",
            "RUNTIME_UNIT",
        )


def learn04() -> Result:
    case = _case("learn04")
    _two_branch_ready(case)
    family_fanout.write_family_fanin(case)
    packet = family_fanout.run_learning(case)
    del packet["HUNT_EFFECTIVENESS"]
    try:
        family_fanout.validate_learning_packet(packet)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_LEARNING_PACKET_INCOMPLETE",
            "missing HUNT_EFFECTIVENESS → rejected",
            "RUNTIME_UNIT",
        )


def learn05() -> Result:
    case = _case("learn05")
    _two_branch_ready(case)
    family_fanout.write_family_fanin(case)
    packet = family_fanout.run_learning(case)
    del packet["BRANCH_PATCH_HASHES"]
    try:
        family_fanout.validate_learning_packet(packet)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_LEARNING_PACKET_INCOMPLETE",
            "missing branch patch hashes → rejected",
            "RUNTIME_UNIT",
        )


def learn06() -> Result:
    case = _case("learn06")
    _bootstrap(case)
    family_fanout.classify_relation(
        case,
        candidate=_cand("HC-1", "OPEN"),
        relation="SAME_INVARIANT_FINDING",
        rationale="x",
        finding_id="OPEN",
    )
    try:
        family_fanout.run_learning(case)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            "LEARNING" in exc.code or "FAMILY" in exc.code or "BEFORE" in exc.code,
            "root GREEN but sibling open → rejected",
            "RUNTIME_UNIT",
        )


def learn07() -> Result:
    case = _case("learn07")
    _two_branch_ready(case)
    family_fanout.write_family_fanin(case)
    packet = family_fanout.run_learning(case)
    packet["SOURCE_ARTIFACT_HASHES"]["FAMILY_FANIN_JSON"] = "0" * 64
    try:
        family_fanout.validate_learning_packet(packet, case)
        return False, "should reject", "RUNTIME_UNIT"
    except family_fanout.FamilyFanoutError as exc:
        return (
            exc.code == "BLOCKED_LEARNING_SOURCE_STALE",
            "stale fan-in hash → rejected",
            "RUNTIME_UNIT",
        )


# --- PAR ---


def par01() -> Result:
    case = _case("par01")
    _bootstrap(case)
    elig = parallelism.evaluate_parallel_eligibility({"A": ["a.py"], "B": ["b.py"]})
    parallelism.record_parallel_dispatch(
        case,
        finding_ids=["A", "B"],
        eligibility=elig,
        dispatch_mode="DISPATCHED_WITHOUT_INTER_BRANCH_DEPENDENCY",
    )
    obs = parallelism.observe_parallel_execution(
        case,
        started_at={"A": 1.0, "B": 1.5},
        finished_at={"A": 3.0, "B": 4.0},
    )
    ok = obs["ARCHITECTURE_PASS"] and obs["PARALLEL_EXECUTION_OBSERVED"] == "YES"
    return ok, "disjoint + overlap → PASS / OBSERVED_PARALLEL", "RUNTIME_UNIT"


def par02() -> Result:
    case = _case("par02")
    _bootstrap(case)
    elig = parallelism.evaluate_parallel_eligibility({"A": ["a.py"], "B": ["b.py"]})
    parallelism.record_parallel_dispatch(
        case,
        finding_ids=["A", "B"],
        eligibility=elig,
        dispatch_mode="DISPATCHED_WITHOUT_INTER_BRANCH_DEPENDENCY",
    )
    obs = parallelism.observe_parallel_execution(
        case,
        started_at={"A": 1.0, "B": 5.0},
        finished_at={"A": 4.0, "B": 8.0},
    )
    ok = (
        obs["ARCHITECTURE_PASS"]
        and obs["PARALLEL_EXECUTION_OBSERVED"] == "NO_PLATFORM_SERIALIZED"
    )
    return ok, "platform serializes → PASS / PLATFORM_SERIALIZED", "RUNTIME_UNIT"


def par03() -> Result:
    case = _case("par03")
    _bootstrap(case)
    elig = parallelism.evaluate_parallel_eligibility({"A": ["a.py"], "B": ["b.py"]})
    try:
        parallelism.record_parallel_dispatch(
            case,
            finding_ids=["A", "B"],
            eligibility=elig,
            dispatch_mode="DISPATCHED_WITHOUT_INTER_BRANCH_DEPENDENCY",
            orchestrator_added_dependency=True,
        )
        return False, "should fail", "RUNTIME_UNIT"
    except parallelism.ParallelismError as exc:
        return (
            exc.code == "BLOCKED_ORCHESTRATOR_UNNECESSARY_DEPENDENCY",
            "orchestrator adds dependency → FAIL",
            "RUNTIME_UNIT",
        )


def par04() -> Result:
    elig = parallelism.evaluate_parallel_eligibility(
        {"A": ["shared.py"], "B": ["shared.py"]}
    )
    return (
        elig["PARALLEL_ELIGIBILITY"] == "FORBIDDEN_WRITE_SET_OVERLAP",
        "overlapping write sets → parallel forbidden",
        "RUNTIME_UNIT",
    )


def par05() -> Result:
    case = _case("par05")
    _bootstrap(case)
    elig = parallelism.evaluate_parallel_eligibility({"A": ["a.py"], "B": ["b.py"]})
    parallelism.record_parallel_dispatch(
        case,
        finding_ids=["A", "B"],
        eligibility=elig,
        dispatch_mode="DISPATCHED_WITHOUT_INTER_BRANCH_DEPENDENCY",
    )
    obs = parallelism.observe_parallel_execution(
        case, started_at={"A": 1.0}, finished_at={"A": 2.0}
    )
    ok = obs["PARALLEL_EXECUTION_OBSERVED"] == "UNKNOWN_TIMESTAMPS_INSUFFICIENT"
    return ok, "timestamps insufficient → UNKNOWN", "RUNTIME_UNIT"


def par06() -> Result:
    case = _case("par06")
    _bootstrap(case)
    elig = parallelism.evaluate_parallel_eligibility({"A": ["a.py"], "B": ["b.py"]})
    parallelism.record_parallel_dispatch(
        case,
        finding_ids=["A", "B"],
        eligibility=elig,
        dispatch_mode="DISPATCHED_WITHOUT_INTER_BRANCH_DEPENDENCY",
    )
    try:
        parallelism.observe_parallel_execution(
            case,
            started_at={"A": 1.0, "B": 1.2},
            finished_at={"A": 3.0, "B": 3.5},
            main_worktree_concurrent_writers=["A", "B"],
        )
        return False, "should fail", "RUNTIME_UNIT"
    except parallelism.ParallelismError as exc:
        return (
            exc.code == "BLOCKED_CONCURRENT_MAIN_WORKTREE_WRITES",
            "concurrent main-worktree writes → FAIL",
            "RUNTIME_UNIT",
        )


# --- NF ---


def registry01() -> Result:
    text = Path(".cursor/pipeline/bug-team/REGISTRY.md").read_text(encoding="utf-8")
    needed = [
        "INVARIANT_CAPTURE_WORKER",
        "RELATION_CLASSIFIER",
        "INTEGRATION_OPERATOR",
        "FAMILY_FAN_IN_ASSEMBLER",
        "FAMILY_LEARNING_WORKER",
        "LEARNING_DECISION",
    ]
    ok = all(n in text for n in needed)
    return ok, "family roles + LEARNING_DECISION registered", "CONTRACT_STATIC"


def identity01() -> Result:
    case = _case("id01")
    execution_identity.create_pending_identity(
        case, worker_execution_id="WEX/REL/1", input_packet_id="PKT-IN-1"
    )
    obj = json.loads(
        execution_identity.identity_path(case, "WEX/REL/1").read_text(encoding="utf-8")
    )
    return obj["CURSOR_AGENT_ID"] == "PENDING_DISPATCH", "pending agent id before dispatch", "RUNTIME_UNIT"


def identity02() -> Result:
    case = _case("id02")
    execution_identity.create_pending_identity(
        case, worker_execution_id="WEX/REL/2", input_packet_id="PKT-IN-2"
    )
    fin = execution_identity.finalize_identity(
        case,
        worker_execution_id="WEX/REL/2",
        cursor_agent_id="b2fcb61d-a5bb-449b-a769-870555af9b3d",
        output_packet_id="PKT-OUT-2",
        dispatch_record_id="DISP-2",
    )
    ok = (
        fin["CURSOR_AGENT_ID_RECONCILIATION"] == "MATCH"
        and fin["CURSOR_AGENT_ID_SOURCE"] == "DISPATCH_RUNTIME"
    )
    return ok, "real agent id reconciled after dispatch", "RUNTIME_UNIT"


def identity03() -> Result:
    case = _case("id03")
    execution_identity.create_pending_identity(
        case, worker_execution_id="WEX/REL/3", input_packet_id="PKT-IN-3"
    )
    try:
        execution_identity.finalize_identity(
            case,
            worker_execution_id="WEX/REL/3",
            cursor_agent_id="PLACEHOLDER",
            output_packet_id="PKT-OUT-3",
        )
        return False, "should reject", "RUNTIME_UNIT"
    except execution_identity.ExecutionIdentityError as exc:
        return (
            exc.code == "BLOCKED_CURSOR_AGENT_ID_PLACEHOLDER",
            "placeholder agent id rejected",
            "RUNTIME_UNIT",
        )


def policy_block01() -> Result:
    blocks = family_policy.blocks_closure_from_policy("SAME_INVARIANT_FINDING")
    return blocks is True, "SAME_INVARIANT blocks from policy", "RUNTIME_UNIT"


def policy_block02() -> Result:
    blocks = family_policy.blocks_closure_from_policy("NEW_ROOT_CAUSE")
    return blocks is False, "NEW_ROOT_CAUSE does not block from policy", "RUNTIME_UNIT"


def policy_block03() -> Result:
    case = _case("pol03")
    _bootstrap(case)
    # Mutate a policy copy and prove helper reads it
    pol = family_policy.load_policy()
    pol = json.loads(json.dumps(pol))
    pol["RELATION_RULES"]["FALSE_POSITIVE"]["BLOCKS_FAMILY_CLOSURE"] = True
    flipped = family_policy.blocks_closure_from_policy("FALSE_POSITIVE", pol)
    live = family_policy.blocks_closure_from_policy("FALSE_POSITIVE")
    out = family_fanout.classify_relation(
        case,
        candidate=_cand("HC-FP", "FPX"),
        relation="FALSE_POSITIVE",
        rationale="x",
        finding_id="FPX",
    )
    ok = flipped is True and live is False and out["BLOCKS_FAMILY_CLOSURE"] is False
    return ok, "policy change reflected without classifier hardcode", "RUNTIME_UNIT"


def pbh006_resume() -> Result:
    case = _case("pbh006")
    green = case / "results" / "GREEN-PBH-006.md"
    green.write_text("GREEN_STATUS: GREEN_CONFIRMED\n", encoding="utf-8")
    (case / "results" / "RED-PBH-006.md").write_text("RED_STATUS: RED_CONFIRMED\n", encoding="utf-8")
    res = family_fanout.resume_family_fanout_from_root_green(
        case,
        case_id="BUGCASE-PBH-006",
        root_finding_id="PBH-006",
        root_green_path=green,
        hunt_candidates=[
            _cand("HC-007", "PBH-007", ["app/manager.py"]),
            _cand("HC-008", "PBH-008", ["app/setup.py"]),
        ],
        relations={
            "HC-007": "SAME_INVARIANT_FINDING",
            "HC-008": "SAME_INVARIANT_FINDING",
        },
        execution_mode=MODE,
        proof_root=case,
        invariant_kwargs=_inv_kwargs(),
    )
    fids = {m["FINDING_ID"] for m in res["MATERIALIZED"]}
    ok = res["ROOT_GREEN_REUSED"] and fids == {"PBH-007", "PBH-008"}
    return ok, "controlled PBH-006 resume fanout plan", "RUNTIME_UNIT"


TESTS: List[Tuple[str, Callable[[], Result]]] = [
    ("V9-INV-01", inv01),
    ("V9-INV-02", inv02),
    ("V9-INV-03", inv03),
    ("V9-INV-04", inv04),
    ("V9-INV-05", inv05),
    ("V9-FANIN-01", fanin01),
    ("V9-FANIN-02", fanin02),
    ("V9-FANIN-03", fanin03),
    ("V9-FANIN-04", fanin04),
    ("V9-FANIN-05", fanin05),
    ("V9-FANIN-06", fanin06),
    ("V9-FANIN-07", fanin07),
    ("V9-LEARN-01", learn01),
    ("V9-LEARN-02", learn02),
    ("V9-LEARN-03", learn03),
    ("V9-LEARN-04", learn04),
    ("V9-LEARN-05", learn05),
    ("V9-LEARN-06", learn06),
    ("V9-LEARN-07", learn07),
    ("V9-PAR-01", par01),
    ("V9-PAR-02", par02),
    ("V9-PAR-03", par03),
    ("V9-PAR-04", par04),
    ("V9-PAR-05", par05),
    ("V9-PAR-06", par06),
    ("V9-REGISTRY-01", registry01),
    ("V9-IDENTITY-01", identity01),
    ("V9-IDENTITY-02", identity02),
    ("V9-IDENTITY-03", identity03),
    ("V9-POLICY-BLOCKING-01", policy_block01),
    ("V9-POLICY-BLOCKING-02", policy_block02),
    ("V9-POLICY-BLOCKING-03", policy_block03),
    ("V9-PBH006-RESUME-01", pbh006_resume),
]


def main() -> int:
    print("=== Corrective V9 tests ===")
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
