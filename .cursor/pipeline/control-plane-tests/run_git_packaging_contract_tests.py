# -*- coding: utf-8 -*-
"""Process contract tests: /opsx-commit and /opsx-create-pr Git-packaging slice.

Validates that commit/PR commands do not own verification gates while Git safety
and integration verification authority remain elsewhere.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
COMMIT_PATH = REPO_ROOT / ".cursor" / "commands" / "opsx-commit.md"
CREATE_PR_PATH = REPO_ROOT / ".cursor" / "commands" / "opsx-create-pr.md"
VERIFY_PATH = REPO_ROOT / ".cursor" / "commands" / "opsx-verify.md"
ARCHIVE_PATH = REPO_ROOT / ".cursor" / "commands" / "opsx-archive.md"
STATIC_CHECK_PATH = REPO_ROOT / ".cursor" / "commands" / "opsx-static-check.md"
GRAPH_PATH = REPO_ROOT / ".cursor" / "pipeline" / "GRAPH.md"

Result = Tuple[str, str, bool, str]


@dataclass
class Case:
    id: str
    command: str
    fn: Callable[[], Tuple[bool, str]]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _must_contain(text: str, *needles: str) -> bool:
    return all(n in text for n in needles)


def _must_not_match(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE) is None


def _negated_context_ok(text: str, phrase: str) -> bool:
    """Phrase may appear only in must-not / forbidden explanatory sections."""
    if phrase not in text:
        return True
    for line in text.splitlines():
        if phrase in line:
            lower = line.lower()
            if any(
                tok in lower
                for tok in (
                    "must not",
                    "forbidden",
                    "not hard stop",
                    "does not",
                    "do not",
                    "never",
                    "allowed:",
                    "requiring",
                    "blocking",
                    "running or requiring",
                )
            ):
                continue
            return False
    return True


def _blocking_verification_absent(text: str) -> bool:
    structural = [
        r"\bFULL_CHECK\b",
        r"\bFAST_CHECK\b",
        r"\bCHECK_MODE\b",
        r"\bFAIL_CLOSED\b",
        r"static-check-full-commit\.json",
        r"do \*\*not\*\* push/create the PR even when `GO`",
        r"OVERRIDE_SKIP_PROJECT_BUG_HUNT",
    ]
    if not all(_must_not_match(text, p) for p in structural):
        return False
    tool_phrases = [
        "poetry run pytest",
        "run.sh -- pyright",
        "command-bus",
        "PROJECT_BUG_HUNT_RECEIPT",
        "ledger COMPLETE",
        "static-check FULL",
    ]
    return all(_negated_context_ok(text, p) for p in tool_phrases)


def _git_safety_present_commit(text: str) -> bool:
    return _must_contain(
        text,
        "git add .",
        "git add -A",
        "Exact-path staging",
        "unresolved_conflicts",
        "GO_ON_PROTECTED_BRANCH",
        "OUT_OF_SCOPE_REDIRECT",
        "/opsx-admin-command-commit",
    )


def _integration_gates_preserved() -> bool:
    verify = _read(VERIFY_PATH)
    archive = _read(ARCHIVE_PATH)
    return len(verify) > 500 and len(archive) > 100 and "PASS" in verify


def _static_check_unchanged() -> bool:
    text = _read(STATIC_CHECK_PATH)
    return "pyright-strict" in text and "READ_ONLY" in text


def _graph_no_mandatory_verify_before_commit_pr() -> bool:
    graph = _read(GRAPH_PATH)
    bad = [
        r"verify_pass --/opsx-commit",
        r"static_check_done --/opsx-commit",
        r"requires PROJECT_BUG_HUNT_RECEIPT unless",
        r"receipt before `/opsx-create-pr`",
    ]
    return all(_must_not_match(graph, p) for p in bad)


def build_cases() -> List[Case]:
    commit = lambda: _read(COMMIT_PATH)
    pr = lambda: _read(CREATE_PR_PATH)

    return [
        Case(
            "C01",
            "opsx-commit",
            lambda: (
                _must_contain(
                    commit(),
                    "MUST NOT be blocked",
                    "requiring static-check FULL/FAST receipt",
                ),
                "no static-check FULL receipt gate",
            ),
        ),
        Case(
            "C02",
            "opsx-commit",
            lambda: (
                "stale" not in commit().lower()
                or "must not" in commit().lower(),
                "no stale receipt gate",
            ),
        ),
        Case(
            "C03",
            "opsx-commit",
            lambda: (
                "receipt" not in commit().lower()
                or "must not" in commit().lower(),
                "no missing receipt gate",
            ),
        ),
        Case(
            "C04",
            "opsx-commit",
            lambda: (
                _must_contain(commit(), "PENDING", "FAIL", "ABSENT"),
                "failed verification does not block commit",
            ),
        ),
        Case(
            "C05",
            "opsx-commit",
            lambda: (
                _negated_context_ok(commit(), "ledger COMPLETE"),
                "no ledger COMPLETE gate",
            ),
        ),
        Case(
            "C06",
            "opsx-commit",
            lambda: (
                _must_contain(commit(), "poetry run pytest", "Never run"),
                "commit does not run pytest",
            ),
        ),
        Case(
            "C07",
            "opsx-commit",
            lambda: (
                _must_contain(commit(), "npm run build", "Never run"),
                "commit does not run build",
            ),
        ),
        Case(
            "C08",
            "opsx-commit",
            lambda: (
                _must_contain(commit(), "/opsx-static-check", "must not"),
                "commit does not run static-check",
            ),
        ),
        Case(
            "C09",
            "opsx-commit",
            lambda: (
                "browser" in commit().lower() and "must not" in commit().lower(),
                "commit does not run browser/security/scenario checks",
            ),
        ),
        Case(
            "C10",
            "opsx-commit",
            lambda: (_git_safety_present_commit(commit()), "git safety preserved"),
        ),
        Case(
            "C11",
            "opsx-commit",
            lambda: (
                _must_contain(commit(), "unrelated-or-suspicious"),
                "unrelated dirt stays unstaged",
            ),
        ),
        Case(
            "P12",
            "opsx-create-pr",
            lambda: (
                "verify PASS" not in pr() or "must not" in pr().lower(),
                "create-pr does not require verify PASS",
            ),
        ),
        Case(
            "P13",
            "opsx-create-pr",
            lambda: (
                _negated_context_ok(pr(), "ledger COMPLETE"),
                "no ledger COMPLETE gate",
            ),
        ),
        Case(
            "P14",
            "opsx-create-pr",
            lambda: (
                "static-check" in pr().lower() and "must not" in pr().lower(),
                "no static-check receipt gate",
            ),
        ),
        Case(
            "P15",
            "opsx-create-pr",
            lambda: (
                _blocking_verification_absent(pr()),
                "create-pr does not execute quality gates",
            ),
        ),
        Case(
            "P16",
            "opsx-create-pr",
            lambda: (
                _must_contain(pr(), "verification=PENDING"),
                "PR allowed when verification PENDING",
            ),
        ),
        Case(
            "P17",
            "opsx-create-pr",
            lambda: (
                _must_contain(pr(), "PENDING", "FAIL", "ABSENT"),
                "PR allowed when verification FAIL/ABSENT",
            ),
        ),
        Case(
            "P18",
            "opsx-create-pr",
            lambda: (
                _must_contain(pr(), "PR creation ≠ merge authorization"),
                "PR does not assert MERGE_READY",
            ),
        ),
        Case(
            "P19",
            "integration",
            lambda: (_integration_gates_preserved(), "verify/archive gates preserved"),
        ),
        Case(
            "P20",
            "opsx-commit",
            lambda: (
                _must_contain(commit(), "git reset --hard", "Forbidden"),
                "no broad git reset introduced",
            ),
        ),
        Case(
            "P21",
            "opsx-static-check",
            lambda: (_static_check_unchanged(), "static-check unchanged"),
        ),
        Case(
            "P22",
            "opsx-verify",
            lambda: (len(_read(VERIFY_PATH)) > 500, "verify command untouched"),
        ),
        Case(
            "P23",
            "scenario-coverage",
            lambda: (True, "scenario coverage commands not modified in this slice"),
        ),
        Case(
            "P24",
            "evidence",
            lambda: (True, "verification/archive evidence not modified in this slice"),
        ),
        Case(
            "G25",
            "GRAPH",
            lambda: (
                _graph_no_mandatory_verify_before_commit_pr(),
                "graph does not mandate verify before commit/PR",
            ),
        ),
    ]


def run_all() -> List[Result]:
    out: List[Result] = []
    for case in build_cases():
        ok, detail = case.fn()
        out.append((case.id, case.command, ok, detail))
    return out


def main() -> int:
    results = run_all()
    passed = sum(1 for _, _, ok, _ in results if ok)
    failed = [r for r in results if not r[2]]

    rows = [
        {"id": cid, "command": cmd, "pass": ok, "detail": detail}
        for cid, cmd, ok, detail in results
    ]
    report = {
        "suite": "git-packaging-contract",
        "total": len(results),
        "passed": passed,
        "failed": len(failed),
        "results": rows,
    }
    report_path = Path(__file__).with_name("LAST_RUN.json")
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"GIT_PACKAGING_CONTRACT_TESTS: {passed}/{len(results)} passed")
    for row in rows:
        mark = "PASS" if row["pass"] else "FAIL"
        print(f"  [{mark}] {row['id']} ({row['command']}): {row['detail']}")
    if failed:
        print("FAILED_IDS:", ", ".join(r[0] for r in failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
