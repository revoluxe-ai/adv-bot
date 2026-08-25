from __future__ import annotations

from pathlib import Path

import pytest

from conftest import run
from opsx_conflict.runtime import (
    ExecutionLedger,
    GitClient,
    StopRequired,
    classify_conflict,
    detect_operation_state,
)


def commit_all(repo: Path, message: str) -> None:
    run(["git", "add", "-A"], repo)
    run(["git", "commit", "-m", message], repo)


def test_real_merge_add_add(git_repo: Path, isolated_state: Path) -> None:
    (git_repo / "base.txt").write_text("base\n", encoding="utf-8")
    commit_all(git_repo, "base")
    run(["git", "checkout", "-b", "feature"], git_repo)
    (git_repo / "same.txt").write_text("feature\n", encoding="utf-8")
    commit_all(git_repo, "feature add")
    run(["git", "checkout", "main"], git_repo)
    (git_repo / "same.txt").write_text("main\n", encoding="utf-8")
    commit_all(git_repo, "main add")
    assert run(["git", "merge", "feature"], git_repo, check=False).returncode != 0

    ledger = ExecutionLedger(isolated_state / "add-add.jsonl")
    state = detect_operation_state(git_repo, GitClient(git_repo, ledger))
    entries = [x for x in state.unmerged if x.path == "same.txt"]
    assert {x.stage for x in entries} == {2, 3}
    assert classify_conflict("same.txt", entries) == "add/add"


def test_real_merge_modify_delete(git_repo: Path, isolated_state: Path) -> None:
    (git_repo / "victim.txt").write_text("base\n", encoding="utf-8")
    commit_all(git_repo, "base")
    run(["git", "checkout", "-b", "feature"], git_repo)
    (git_repo / "victim.txt").unlink()
    commit_all(git_repo, "feature delete")
    run(["git", "checkout", "main"], git_repo)
    (git_repo / "victim.txt").write_text("main modified\n", encoding="utf-8")
    commit_all(git_repo, "main modify")
    assert run(["git", "merge", "feature"], git_repo, check=False).returncode != 0

    ledger = ExecutionLedger(isolated_state / "modify-delete.jsonl")
    state = detect_operation_state(git_repo, GitClient(git_repo, ledger))
    entries = [x for x in state.unmerged if x.path == "victim.txt"]
    assert {x.stage for x in entries} == {1, 2}
    assert classify_conflict("victim.txt", entries) == "modify/delete"


def test_no_active_operation_fails_closed(git_repo: Path, isolated_state: Path) -> None:
    (git_repo / "x.txt").write_text("x\n", encoding="utf-8")
    commit_all(git_repo, "base")
    ledger = ExecutionLedger(isolated_state / "none.jsonl")
    with pytest.raises(StopRequired) as exc:
        detect_operation_state(git_repo, GitClient(git_repo, ledger))
    assert exc.value.reason == "NO_ACTIVE_SUPPORTED_GIT_OPERATION"
