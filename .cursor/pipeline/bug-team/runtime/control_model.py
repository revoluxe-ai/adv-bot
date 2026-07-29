# -*- coding: utf-8 -*-
"""V7 control model: user reviews uncommitted worktree.

Default live mode after activation: CONTROLLED_LIVE_UNCOMMITTED.
- No intermediate Owner production GO for local worktree writes after valid RED.
- After fan-in READY_FOR_CLOSURE: FAMILY_LEARNING_WORKER then CLOSURE_OPERATOR
  (validated LEARNING_DECISION required; no Owner closure GO by default).
- Git commit/push/deploy/external mutations remain forbidden.
- Legacy OWNER_GATED mode preserves previous Owner GO behavior.

LIVE_RUNTIME_AUTHORITY: runtime/control_model.py (control policy only;
  live hop success authority remains live_task_hop.py).
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from . import learning_decision

CONTROL_MODEL = "USER_REVIEWS_UNCOMMITTED_WORKTREE"
MODE_CONTROLLED_LIVE_UNCOMMITTED = "CONTROLLED_LIVE_UNCOMMITTED"
MODE_OWNER_GATED = "OWNER_GATED"
MODE_REVIEW_PROOF_ONLY = "REVIEW_PROOF_ONLY"

DEFAULT_LIVE_EXECUTION_MODE = MODE_CONTROLLED_LIVE_UNCOMMITTED

FORBIDDEN_EXTERNAL_KEYWORDS = (
    "kubectl ",
    "helm ",
    "terraform ",
    "ansible ",
    "aws ",
    "gcloud ",
    "az ",
    "docker push",
    "deploy ",
    "production database",
    "DROP TABLE",
    "TRUNCATE ",
    "billing",
    "secret rotation",
    "customer data",
)

FORBIDDEN_GIT_COMMANDS = (
    "git commit",
    "git push",
    "git add",
    "gh pr create",
)

FORBIDDEN_DEPLOY_COMMANDS = (
    "kubectl apply",
    "kubectl delete",
    "helm upgrade",
    "helm install",
    "terraform apply",
)


class ControlModelError(Exception):
    """Control-model / local-authority rejection."""

    def __init__(self, code: str, detail: str = "", payload: Optional[Dict[str, Any]] = None) -> None:
        self.code = code
        self.detail = detail
        self.payload = payload or {}
        super().__init__(f"{code}: {detail}" if detail else code)


def uses_owner_production_gate(execution_mode: str) -> bool:
    """True when IMPLEMENTATION_EXECUTOR must reserve Owner production GO."""
    return execution_mode == MODE_OWNER_GATED


def uses_owner_closure_gate(execution_mode: str) -> bool:
    """True when CLOSURE_OPERATOR must wait for Owner final closure GO."""
    return execution_mode == MODE_OWNER_GATED


def uses_local_uncommitted_authority(execution_mode: str) -> bool:
    return execution_mode == MODE_CONTROLLED_LIVE_UNCOMMITTED


def validate_local_implementation_authority(
    *,
    execution_mode: str,
    red_status: str,
    red_packet_valid: bool,
    frozen_test_hashes_valid: bool,
    expected_execution_route_valid: bool,
    worker_write_boundary_valid: bool,
    external_mutation_required: bool = False,
    deploy_requested: bool = False,
    git_commit_requested: bool = False,
    git_push_requested: bool = False,
    irreversible_outside_repo: bool = False,
) -> Dict[str, Any]:
    """Authorize local IMPLEMENTATION_EXECUTOR without Owner GO (uncommitted mode)."""
    if not uses_local_uncommitted_authority(execution_mode):
        raise ControlModelError(
            "BLOCKED_LOCAL_AUTHORITY_MODE_MISMATCH",
            execution_mode,
        )
    if external_mutation_required or irreversible_outside_repo:
        raise ControlModelError(
            "BLOCKED_EXTERNAL_OR_IRREVERSIBLE_MUTATION_REQUIRED",
            "external_or_irreversible",
            {"LOCAL_IMPLEMENTATION_AUTHORIZED": False},
        )
    if deploy_requested:
        raise ControlModelError(
            "BLOCKED_DEPLOY_FORBIDDEN",
            "deploy",
            {"LOCAL_IMPLEMENTATION_AUTHORIZED": False, "DEPLOY": "FORBIDDEN"},
        )
    if git_commit_requested:
        raise ControlModelError(
            "BLOCKED_GIT_COMMIT_FORBIDDEN",
            "git_commit",
            {"LOCAL_IMPLEMENTATION_AUTHORIZED": False, "GIT_COMMIT": "FORBIDDEN"},
        )
    if git_push_requested:
        raise ControlModelError(
            "BLOCKED_GIT_PUSH_FORBIDDEN",
            "git_push",
            {"LOCAL_IMPLEMENTATION_AUTHORIZED": False, "GIT_PUSH": "FORBIDDEN"},
        )
    if red_status != "RED_CONFIRMED":
        raise ControlModelError(
            "BLOCKED_LOCAL_AUTHORITY_RED_REQUIRED",
            red_status,
            {"LOCAL_IMPLEMENTATION_AUTHORIZED": False},
        )
    if not red_packet_valid:
        raise ControlModelError("BLOCKED_LOCAL_AUTHORITY_RED_PACKET_INVALID")
    if not frozen_test_hashes_valid:
        raise ControlModelError("BLOCKED_LOCAL_AUTHORITY_FROZEN_HASHES_INVALID")
    if not expected_execution_route_valid:
        raise ControlModelError("BLOCKED_LOCAL_AUTHORITY_ROUTE_INVALID")
    if not worker_write_boundary_valid:
        raise ControlModelError("BLOCKED_LOCAL_AUTHORITY_WRITE_BOUNDARY_INVALID")

    return {
        "STATUS": "PASS",
        "LOCAL_IMPLEMENTATION_AUTHORIZED": True,
        "EXECUTION_MODE": execution_mode,
        "CONTROL_MODEL": CONTROL_MODEL,
        "OWNER_PRODUCTION_GO_REQUIRED": False,
        "WAITING_OWNER": False,
        "COMMIT_AUTHORITY": "USER_ONLY",
        "GIT_COMMIT": "FORBIDDEN",
        "GIT_PUSH": "FORBIDDEN",
        "DEPLOY": "FORBIDDEN",
        "EXTERNAL_PRODUCTION_MUTATIONS": "FORBIDDEN",
    }


def reject_forbidden_shell_command(command: str) -> Optional[str]:
    """Return block code if command is forbidden; else None."""
    text = (command or "").strip().lower()
    if not text:
        return None
    for frag in FORBIDDEN_GIT_COMMANDS:
        if frag in text:
            if "commit" in frag:
                return "BLOCKED_GIT_COMMIT_FORBIDDEN"
            if "push" in frag or "pr create" in frag:
                return "BLOCKED_GIT_PUSH_FORBIDDEN"
            return "BLOCKED_GIT_MUTATION_FORBIDDEN"
    for frag in FORBIDDEN_DEPLOY_COMMANDS:
        if frag in text:
            return "BLOCKED_DEPLOY_FORBIDDEN"
    for frag in FORBIDDEN_EXTERNAL_KEYWORDS:
        if frag.lower() in text:
            return "BLOCKED_EXTERNAL_OR_IRREVERSIBLE_MUTATION_REQUIRED"
    return None


def decide_auto_closure(
    *,
    execution_mode: str,
    closure_readiness: str,
    blocking_findings: Optional[List[str]] = None,
    case_root: Optional[Path] = None,
    learning_decision_obj: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Fan-in → learning → automatic CLOSURE_OPERATOR when uncommitted control model.

    After READY_FOR_CLOSURE, FAMILY_LEARNING_WORKER must complete a validated
    LEARNING_DECISION before CLOSURE_OPERATOR may dispatch.
    """
    blocking = [b for b in (blocking_findings or []) if b]
    if uses_owner_closure_gate(execution_mode):
        return {
            "STATUS": "WAITING_OWNER_FINAL_CLOSURE",
            "AUTO_CLOSURE": False,
            "WAITING_OWNER": True,
            "CLOSURE_OPERATOR_DISPATCH_ALLOWED": False,
            "LEARNING_DISPATCH_ALLOWED": False,
            "EXPECTED_NEXT_COMMAND": "OWNER_FINAL_CLOSURE_DECISION",
        }
    if blocking:
        return {
            "STATUS": "BLOCKED_FANIN_FINDINGS",
            "AUTO_CLOSURE": False,
            "CASE_STATUS": "OPEN_BLOCKED",
            "BLOCKING_FINDINGS": blocking,
            "CLOSURE_OPERATOR_DISPATCH_ALLOWED": False,
            "LEARNING_DISPATCH_ALLOWED": False,
            "EXPECTED_NEXT_COMMAND": None,
        }
    if closure_readiness not in ("READY_FOR_CLOSURE", "READY_FOR_FAMILY_CLOSURE"):
        return {
            "STATUS": "BLOCKED_FANIN_NOT_READY",
            "AUTO_CLOSURE": False,
            "CLOSURE_READINESS": closure_readiness,
            "CLOSURE_OPERATOR_DISPATCH_ALLOWED": False,
            "LEARNING_DISPATCH_ALLOWED": False,
            "EXPECTED_NEXT_COMMAND": None,
        }

    # Mandatory learning hop before closure.
    decision = learning_decision_obj
    if decision is None and case_root is not None:
        decision = learning_decision.load_learning_decision(case_root)

    if decision is None:
        return {
            "STATUS": "LEARNING_REQUIRED",
            "AUTO_CLOSURE": False,
            "WAITING_OWNER": False,
            "WAITING_OWNER_FINAL_CLOSURE": False,
            "CLOSURE_OPERATOR_DISPATCH_ALLOWED": False,
            "LEARNING_DISPATCH_ALLOWED": True,
            "EXPECTED_NEXT_COMMAND": "FAMILY_LEARNING_WORKER",
            "REASON": "BLOCKED_LEARNING_DECISION_MISSING",
        }

    try:
        if case_root is not None:
            learning_decision.evaluate_closure_learning_gate(case_root, decision=decision)
        else:
            learning_decision.validate_learning_decision(decision)
            if decision.get("LEARNING_STATUS") != "COMPLETE":
                raise learning_decision.LearningDecisionError(
                    "BLOCKED_LEARNING_INCOMPLETE",
                    f"status={decision.get('LEARNING_STATUS')}",
                )
            if decision.get("LEARNING_VERDICT") in learning_decision.CLOSURE_BLOCKING_VERDICTS:
                code = (
                    "BLOCKED_OWNER_LEARNING_DECISION_REQUIRED"
                    if decision.get("LEARNING_VERDICT") == "OWNER_DECISION_REQUIRED"
                    else "BLOCKED_LEARNING_INCOMPLETE"
                )
                raise learning_decision.LearningDecisionError(code)
            if decision.get("LEARNING_VERDICT") not in learning_decision.CLOSURE_ALLOWED_VERDICTS:
                raise learning_decision.LearningDecisionError(
                    "BLOCKED_LEARNING_DECISION_INVALID",
                    f"verdict={decision.get('LEARNING_VERDICT')}",
                )
    except learning_decision.LearningDecisionError as exc:
        if exc.code == "BLOCKED_OWNER_LEARNING_DECISION_REQUIRED":
            return {
                "STATUS": "BLOCKED_OWNER_LEARNING_DECISION_REQUIRED",
                "AUTO_CLOSURE": False,
                "WAITING_OWNER": True,
                "CLOSURE_OPERATOR_DISPATCH_ALLOWED": False,
                "LEARNING_DISPATCH_ALLOWED": False,
                "EXPECTED_NEXT_COMMAND": "OWNER_LEARNING_DECISION",
                "REASON": exc.detail,
            }
        if exc.code == "BLOCKED_LEARNING_DECISION_MISSING":
            return {
                "STATUS": "LEARNING_REQUIRED",
                "AUTO_CLOSURE": False,
                "CLOSURE_OPERATOR_DISPATCH_ALLOWED": False,
                "LEARNING_DISPATCH_ALLOWED": True,
                "EXPECTED_NEXT_COMMAND": "FAMILY_LEARNING_WORKER",
                "REASON": exc.code,
            }
        return {
            "STATUS": exc.code,
            "AUTO_CLOSURE": False,
            "CLOSURE_OPERATOR_DISPATCH_ALLOWED": False,
            "LEARNING_DISPATCH_ALLOWED": True,
            "EXPECTED_NEXT_COMMAND": "FAMILY_LEARNING_WORKER",
            "REASON": exc.detail,
        }

    return {
        "STATUS": "AUTO_CLOSURE_AUTHORIZED",
        "AUTO_CLOSURE": True,
        "WAITING_OWNER": False,
        "WAITING_OWNER_FINAL_CLOSURE": False,
        "CLOSURE_OPERATOR_DISPATCH_ALLOWED": True,
        "LEARNING_DISPATCH_ALLOWED": False,
        "EXPECTED_NEXT_COMMAND": "CLOSURE_OPERATOR",
        "CASE_STATUS": "CLOSING",
        "LEARNING_DECISION_VALIDATED": True,
    }


def terminal_user_control_state(
    *,
    case_closed: bool,
    commit_created: bool = False,
    worktree_has_episode_changes: bool = True,
) -> Dict[str, Any]:
    """Final episode state for USER_REVIEWS_UNCOMMITTED_WORKTREE."""
    if commit_created:
        # Must never claim commit unless user did it outside this command
        pass
    return {
        "PROCESS_STATUS": "COMPLETED" if case_closed else "BLOCKED",
        "CASE_STATUS": "CLOSED" if case_closed else "OPEN_BLOCKED",
        "WORKTREE_STATUS": "UNCOMMITTED_CHANGES_AWAITING_USER_REVIEW"
        if worktree_has_episode_changes
        else "CLEAN_OR_NO_EPISODE_CHANGES",
        "COMMIT_CREATED": False,
        "USER_ACTION_REQUIRED": "REVIEW_DIFF_AND_DECIDE_COMMIT",
        "CONTROL_MODEL": CONTROL_MODEL,
        "READY_TO_DEPLOY": False,
        "DEPLOYED": False,
        "COMMITTED": False,
        "PUSHED": False,
    }


REQUIRED_HUMAN_SECTIONS = (
    "Что произошло",
    "Что было сломано",
    "Почему это было проблемой",
    "Что мы изменили",
    "Какие файлы изменены",
    "Как мы проверили",
    "Какие дополнительные проверки сделали",
    "Что не изменяли",
    "Оставшиеся риски",
    "Что проверить перед коммитом",
    "Технические детали",
)


def human_summary_path(case_root: Path) -> Path:
    return Path(case_root) / "results" / "HUMAN_SUMMARY.md"


def write_human_summary(
    case_root: Path,
    *,
    what_happened: str,
    what_was_broken: str,
    why_problem: str,
    what_changed: str,
    files_changed: List[str],
    how_verified: str,
    extra_checks: str,
    not_changed: str,
    remaining_risks: str,
    review_before_commit: str,
    technical_details: str,
    episode_files: Optional[List[str]] = None,
    unrelated_dirty_files: Optional[List[str]] = None,
    tests_and_results: str = "",
) -> Path:
    """Write HUMAN_SUMMARY.md in plain language (Russian section headers)."""
    path = human_summary_path(case_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    files_block = "\n".join(f"- {f}" for f in files_changed) or "- (нет)"
    episode_block = "\n".join(f"- {f}" for f in (episode_files or files_changed)) or "- (нет)"
    unrelated_block = (
        "\n".join(f"- {f}" for f in (unrelated_dirty_files or [])) or "- (нет)"
    )
    body = f"""# Что произошло

{what_happened.strip()}

# Что было сломано

{what_was_broken.strip()}

# Почему это было проблемой

{why_problem.strip()}

# Что мы изменили

{what_changed.strip()}

# Какие файлы изменены

{files_block}

## Изменения этого bug episode

{episode_block}

## Ранее существовавшие несвязанные изменения

{unrelated_block}

# Как мы проверили

{how_verified.strip()}

## Какие тесты прошли

{tests_and_results.strip() or "(см. evidence GREEN / pytest)"}

# Какие дополнительные проверки сделали

{extra_checks.strip()}

# Что не изменяли

{not_changed.strip()}

# Оставшиеся риски

{remaining_risks.strip()}

# Что проверить перед коммитом

{review_before_commit.strip()}

# Технические детали

{technical_details.strip()}
"""
    path.write_text(body, encoding="utf-8")
    return path


def validate_human_summary_file(path: Path) -> Tuple[bool, List[str]]:
    """Return (ok, missing_sections)."""
    if not path.exists():
        return False, list(REQUIRED_HUMAN_SECTIONS)
    text = path.read_text(encoding="utf-8")
    missing = [s for s in REQUIRED_HUMAN_SECTIONS if f"# {s}" not in text]
    return len(missing) == 0, missing


def apply_closure_artifacts(
    case_root: Path,
    *,
    finding_id: str,
    human_summary_kwargs: Dict[str, Any],
    terminal_status: str = "CLOSED_FIXED_VERIFIED",
    skip_learning_gate: bool = False,
) -> Dict[str, Any]:
    """CLOSURE_OPERATOR write set for uncommitted control model.

    Requires validated LEARNING_DECISION unless skip_learning_gate (tests only).
    """
    case_root = Path(case_root)
    if not skip_learning_gate:
        try:
            learning_decision.evaluate_closure_learning_gate(case_root)
        except learning_decision.LearningDecisionError as exc:
            return {
                "STATUS": exc.code,
                "CASE_STATUS": "OPEN_BLOCKED",
                "AUTO_CLOSURE": False,
                "CLOSURE_OPERATOR_DISPATCH_ALLOWED": False,
                "REASON": exc.detail,
                **exc.payload,
            }
    results = case_root / "results"
    results.mkdir(parents=True, exist_ok=True)

    closure_path = results / f"OWNER-CLOSURE-{finding_id}.md"
    closure_path.write_text(
        f"# Closure\n\nTERMINAL_STATUS: {terminal_status}\n"
        f"CONTROL_MODEL: {CONTROL_MODEL}\n"
        f"COMMIT_CREATED: NO\n"
        f"USER_ACTION_REQUIRED: REVIEW_DIFF_AND_DECIDE_COMMIT\n",
        encoding="utf-8",
    )
    summary_path = write_human_summary(case_root, **human_summary_kwargs)

    case_md = case_root / "CASE.md"
    if case_md.exists():
        prev = case_md.read_text(encoding="utf-8")
        if "CASE_STATUS:" in prev:
            prev = re.sub(r"CASE_STATUS:\s*\S+", "CASE_STATUS: CLOSED", prev)
        else:
            prev += f"\nCASE_STATUS: CLOSED\n"
        if "TERMINAL_STATUS:" in prev:
            prev = re.sub(r"TERMINAL_STATUS:\s*\S+", f"TERMINAL_STATUS: {terminal_status}", prev)
        else:
            prev += f"TERMINAL_STATUS: {terminal_status}\n"
        case_md.write_text(prev, encoding="utf-8")
    else:
        case_md.write_text(
            f"CASE_STATUS: CLOSED\nTERMINAL_STATUS: {terminal_status}\n",
            encoding="utf-8",
        )

    ledger = case_root / "LEDGER.md"
    line = f"\n- {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} CLOSED {terminal_status}\n"
    if ledger.exists():
        ledger.write_text(ledger.read_text(encoding="utf-8") + line, encoding="utf-8")
    else:
        ledger.write_text("# LEDGER\n" + line, encoding="utf-8")

    finding = case_root / "findings" / f"{finding_id}.md"
    finding.parent.mkdir(parents=True, exist_ok=True)
    if finding.exists():
        ft = finding.read_text(encoding="utf-8")
        ft += f"\nTERMINAL_STATUS: {terminal_status}\n"
        finding.write_text(ft, encoding="utf-8")
    else:
        finding.write_text(
            f"# {finding_id}\nTERMINAL_STATUS: {terminal_status}\n",
            encoding="utf-8",
        )

    # INDEX.md optional
    index = case_root / "INDEX.md"
    if index.exists():
        index.write_text(
            index.read_text(encoding="utf-8")
            + f"\n- closed {finding_id} {terminal_status}\n",
            encoding="utf-8",
        )

    terminal = terminal_user_control_state(
        case_closed=True,
        commit_created=False,
        worktree_has_episode_changes=True,
    )
    return {
        "STATUS": "CLOSED",
        "CASE_STATUS": "CLOSED",
        "EPISODE_STATUS": "CLOSED",
        "TERMINAL_STATUS": terminal_status,
        "HUMAN_SUMMARY_PATH": str(summary_path),
        "OWNER_CLOSURE_PATH": str(closure_path),
        **terminal,
    }


def parse_fanin_readiness(fanin_path: Path) -> Tuple[str, List[str]]:
    """Extract CLOSURE_READINESS and BLOCKING_FINDINGS from FANIN.md."""
    if not fanin_path.exists():
        return "MISSING", ["FANIN_MISSING"]
    text = fanin_path.read_text(encoding="utf-8")
    readiness = "READY_FOR_CLOSURE" if "READY_FOR_CLOSURE" in text else "NOT_READY"
    m = re.search(r"CLOSURE_READINESS:\s*(\S+)", text)
    if m:
        readiness = m.group(1)
    blocking: List[str] = []
    if re.search(r"BLOCKING_FINDINGS:\s*NONE\b", text):
        blocking = []
    else:
        bm = re.search(r"BLOCKING_FINDINGS:\s*(.+)", text)
        if bm and bm.group(1).strip() not in {"NONE", "[]", "-"}:
            blocking = [x.strip() for x in bm.group(1).split(",") if x.strip()]
    return readiness, blocking


def format_simple_explanation_chat(
    *,
    noticed: str,
    broken: str,
    why: str,
    changed: str,
    files: List[str],
    why_fixes: str,
    verified: str,
    tests: str,
    extra: str,
    not_changed: str,
    risks: str,
    before_commit: str,
) -> str:
    """Plain-language chat section ПРОСТОЕ ОБЪЯСНЕНИЕ."""
    files_s = ", ".join(files) if files else "(нет)"
    return f"""ПРОСТОЕ ОБЪЯСНЕНИЕ

1. Что пользователь заметил?
{noticed}

2. Что на самом деле было сломано?
{broken}

3. Почему это происходило?
{why}

4. Что именно было изменено?
{changed}

5. Какие файлы были изменены?
{files_s}

6. Почему это должно исправить проблему?
{why_fixes}

7. Как мы проверили исправление?
{verified}

8. Какие тесты прошли?
{tests}

9. Что команда дополнительно проверила рядом с багом?
{extra}

10. Что команда сознательно не меняла?
{not_changed}

11. Есть ли оставшиеся риски или сомнения?
{risks}

12. Что пользователю посмотреть перед коммитом?
{before_commit}
"""


def classify_worktree_changes(
    *,
    episode_paths: Set[str],
    all_dirty_paths: Set[str],
) -> Dict[str, List[str]]:
    """Separate episode changes from pre-existing unrelated dirty files."""
    episode = sorted(p for p in all_dirty_paths if p in episode_paths)
    unrelated = sorted(p for p in all_dirty_paths if p not in episode_paths)
    return {
        "ИЗМЕНЕНИЯ_ЭТОГО_BUG_EPISODE": episode,
        "РАНЕЕ_СУЩЕСТВОВАВШИЕ_НЕСВЯЗАННЫЕ_ИЗМЕНЕНИЯ": unrelated,
        "ИЗМЕНЁННЫЕ_ФАЙЛЫ": episode,
        "НОВЫЕ_ФАЙЛЫ": [],
        "УДАЛЁННЫЕ_ФАЙЛЫ": [],
        "НЕЗАКОММИЧЕННЫЕ_ИЗМЕНЕНИЯ": sorted(all_dirty_paths),
    }
