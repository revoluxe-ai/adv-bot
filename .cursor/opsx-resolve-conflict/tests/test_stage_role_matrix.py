from __future__ import annotations

from pathlib import Path

from conftest import run
from opsx_conflict.runtime import ExecutionLedger, GitClient, detect_operation_state, stage_role_matrix


def commit_file(repo: Path, text: str, message: str) -> None:
    (repo / "conflict.txt").write_text(text, encoding="utf-8")
    run(["git", "add", "conflict.txt"], repo)
    run(["git", "commit", "-m", message], repo)


def test_merge_stage_role_matrix(git_repo: Path, isolated_state: Path) -> None:
    commit_file(git_repo, "base\n", "base")
    run(["git", "checkout", "-b", "feature"], git_repo)
    commit_file(git_repo, "feature\n", "feature")
    run(["git", "checkout", "main"], git_repo)
    commit_file(git_repo, "main\n", "main")
    result = run(["git", "merge", "feature"], git_repo, check=False)
    assert result.returncode != 0

    ledger = ExecutionLedger(isolated_state / "merge-ledger.jsonl")
    git = GitClient(git_repo, ledger)
    state = detect_operation_state(git_repo, git)
    assert state.operation == "merge"
    matrix = stage_role_matrix(state, git)
    roles = {r.stage: r for r in matrix["conflict.txt"]}
    assert roles[1].role == "merge_base"
    assert roles[2].role == "current_HEAD"
    assert roles[3].role == "incoming_MERGE_HEAD"
    assert all(r.verified for r in roles.values())


def test_rebase_stage_role_matrix_after_clean_replayed_commit(git_repo: Path, isolated_state: Path) -> None:
    commit_file(git_repo, "base\n", "base")
    run(["git", "checkout", "-b", "feature"], git_repo)

    # First feature commit is replayed cleanly.
    (git_repo / "clean.txt").write_text("feature clean\n", encoding="utf-8")
    run(["git", "add", "clean.txt"], git_repo)
    run(["git", "commit", "-m", "feature clean"], git_repo)

    # Second feature commit conflicts.
    commit_file(git_repo, "feature conflict\n", "feature conflict")

    run(["git", "checkout", "main"], git_repo)
    commit_file(git_repo, "target conflict\n", "target conflict")
    run(["git", "checkout", "feature"], git_repo)
    result = run(["git", "rebase", "main"], git_repo, check=False)
    assert result.returncode != 0

    ledger = ExecutionLedger(isolated_state / "rebase-ledger.jsonl")
    git = GitClient(git_repo, ledger)
    state = detect_operation_state(git_repo, git)
    assert state.operation == "rebase"
    assert state.rebase_backend in {"rebase-merge", "rebase-apply"}
    matrix = stage_role_matrix(state, git)
    roles = {r.stage: r for r in matrix["conflict.txt"]}
    assert roles[1].role == "parent_of_replayed_commit"
    assert roles[2].role == "accumulated_onto_plus_replayed_commits"
    assert roles[3].role == "current_replayed_commit"
    assert roles[2].commit_oid == state.head_oid
    assert roles[3].commit_oid == state.operation_head_oid
    assert all(r.verified for r in roles.values())
    assert (git_repo / "clean.txt").exists(), "first replayed commit must already be in accumulated side"
