from __future__ import annotations

from pathlib import Path

from conftest import run
from opsx_conflict.runtime import (
    ExecutionLedger,
    build_validation_snapshot,
)


def test_validation_snapshot_excludes_git_and_untracked(
    git_repo: Path, isolated_state: Path
) -> None:
    (git_repo / "tracked.py").write_text("value = 1\n", encoding="utf-8")
    run(["git", "add", "tracked.py"], git_repo)
    run(["git", "commit", "-m", "tracked"], git_repo)
    (git_repo / "untracked.py").write_text("raise RuntimeError('must not copy')\n", encoding="utf-8")
    run_dir = isolated_state / "run"
    run_dir.mkdir(parents=True)
    ledger = ExecutionLedger(run_dir / "ledger.jsonl")
    snap = build_validation_snapshot(git_repo, run_dir, ledger=ledger)
    assert (snap / "tracked.py").exists()
    assert not (snap / "untracked.py").exists()
    assert not (snap / ".git").exists()
