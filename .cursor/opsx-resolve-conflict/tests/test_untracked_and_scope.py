from __future__ import annotations

from pathlib import Path

import pytest

from conftest import run
from opsx_conflict.runtime import (
    ExecutionLedger,
    GitClient,
    ScopeItem,
    ScopeManifest,
    StopRequired,
    detect_operation_state,
    untracked_gate,
)


def make_conflict(repo: Path) -> None:
    (repo / "x.py").write_text("value = 0\n", encoding="utf-8")
    run(["git", "add", "x.py"], repo)
    run(["git", "commit", "-m", "base"], repo)
    run(["git", "checkout", "-b", "feature"], repo)
    (repo / "x.py").write_text("value = 1\n", encoding="utf-8")
    run(["git", "commit", "-am", "feature"], repo)
    run(["git", "checkout", "main"], repo)
    (repo / "x.py").write_text("value = 2\n", encoding="utf-8")
    run(["git", "commit", "-am", "main"], repo)
    assert run(["git", "merge", "feature"], repo, check=False).returncode != 0


def test_any_untracked_path_is_fail_closed_without_exact_hash_allowlist(
    git_repo: Path, isolated_state: Path
) -> None:
    make_conflict(git_repo)
    (git_repo / "helper.py").write_text("print('contamination')\n", encoding="utf-8")
    ledger = ExecutionLedger(isolated_state / "ledger.jsonl")
    state = detect_operation_state(git_repo, GitClient(git_repo, ledger))
    with pytest.raises(StopRequired) as exc:
        untracked_gate(state)
    assert exc.value.reason == "UNTRACKED_CONTAMINATION"


def test_scope_manifest_rejects_new_non_conflicted_path() -> None:
    scope = ScopeManifest(
        [
            ScopeItem(
                path="x.py",
                unit_id="unit-1",
                reason="textual conflict",
                authority_source="git stages",
                authority_sha256="0" * 64,
                allowed_operation="write",
                expected_semantic_change="combine behavior",
                initial_stage_oids={"1": "a", "2": "b", "3": "c"},
                initial_worktree_sha256="0" * 64,
                required_checks=(("syntax-parse", "x.py"),),
            )
        ],
        run_id="run-1",
        frozen_at_fingerprint="fp",
    )
    assert scope.require("x.py", allowed_operation="write").path == "x.py"
    with pytest.raises(StopRequired) as exc:
        scope.require("consumer.py", allowed_operation="write")
    assert exc.value.reason == "SCOPE_EXPANSION_REQUIRED"
