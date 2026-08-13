from __future__ import annotations

import json
from pathlib import Path
import os

from conftest import run
from opsx_conflict.runtime import (
    ExecutionLedger,
    GitClient,
    create_metadata_snapshot,
    detect_operation_state,
    stage_role_matrix,
)


def test_snapshot_contains_only_metadata_not_conflicted_plaintext(
    git_repo: Path, isolated_state: Path
) -> None:
    secret = "TOP_SECRET_VALUE_123"
    (git_repo / "secret.env").write_text(f"TOKEN={secret}\n", encoding="utf-8")
    run(["git", "add", "secret.env"], git_repo)
    run(["git", "commit", "-m", "base"], git_repo)
    run(["git", "checkout", "-b", "feature"], git_repo)
    (git_repo / "secret.env").write_text(f"TOKEN={secret}_feature\n", encoding="utf-8")
    run(["git", "commit", "-am", "feature"], git_repo)
    run(["git", "checkout", "main"], git_repo)
    (git_repo / "secret.env").write_text(f"TOKEN={secret}_main\n", encoding="utf-8")
    run(["git", "commit", "-am", "main"], git_repo)
    assert run(["git", "merge", "feature"], git_repo, check=False).returncode != 0

    run_dir = isolated_state / "run"
    run_dir.mkdir(parents=True)
    ledger = ExecutionLedger(run_dir / "ledger.jsonl")
    git = GitClient(git_repo, ledger)
    state = detect_operation_state(git_repo, git)
    matrix = stage_role_matrix(state, git)
    snapshot = create_metadata_snapshot(run_dir, state, stage_matrix=matrix)
    raw = snapshot.read_text(encoding="utf-8")
    assert secret not in raw
    data = json.loads(raw)
    assert data["snapshot_mode"] == "METADATA_ONLY_NO_FILE_CONTENT"
    if os.name != "nt":
        assert snapshot.stat().st_mode & 0o077 == 0
