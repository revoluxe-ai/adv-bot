"""Operation fingerprint and R11 write-ahead recovery tests."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from conftest import run
from opsx_conflict.runtime import (
    ExecutionLedger,
    GitClient,
    RunManifest,
    StopRequired,
    detect_operation_state,
    resume_guard,
    save_run_manifest,
    load_run_manifest,
)
from opsx_conflict.write_atomic import recover_write_transactions


def make_merge_conflict(repo: Path) -> None:
    (repo / "x.txt").write_text("base\n", encoding="utf-8")
    run(["git", "add", "x.txt"], repo)
    run(["git", "commit", "-m", "base"], repo)
    run(["git", "checkout", "-b", "feature"], repo)
    (repo / "x.txt").write_text("feature\n", encoding="utf-8")
    run(["git", "commit", "-am", "feature"], repo)
    run(["git", "checkout", "main"], repo)
    (repo / "x.txt").write_text("main\n", encoding="utf-8")
    run(["git", "commit", "-am", "main"], repo)
    assert run(["git", "merge", "feature"], repo, check=False).returncode != 0


def test_state_fingerprint_detects_external_index_drift(git_repo: Path, isolated_state: Path) -> None:
    make_merge_conflict(git_repo)
    ledger = ExecutionLedger(isolated_state / "ledger.jsonl")
    git = GitClient(git_repo, ledger)
    before = detect_operation_state(git_repo, git)

    # External actor writes and stages a resolution.
    (git_repo / "x.txt").write_text("external\n", encoding="utf-8")
    run(["git", "add", "x.txt"], git_repo)
    after = detect_operation_state(git_repo, git)
    assert before.fingerprint != after.fingerprint


def test_restart_requires_exact_last_verified_fingerprint(git_repo: Path, isolated_state: Path) -> None:
    make_merge_conflict(git_repo)
    ledger = ExecutionLedger(isolated_state / "ledger.jsonl")
    git = GitClient(git_repo, ledger)
    state = detect_operation_state(git_repo, git)

    manifest = RunManifest(
        run_id="run-1",
        package_version="0.34.0",
        repository_identity=state.repository_identity,
        repository_root=str(git_repo.resolve()),
        operation=state.operation,
        initial_fingerprint=state.fingerprint,
        last_verified_fingerprint=state.fingerprint,
        status="ACTIVE",
        completed_units=(),
        staged_paths=(),
        owner_decision_state=None,
        ledger_final_hash=None,
    )
    path = isolated_state / "run.json"
    save_run_manifest(path, manifest)
    loaded = load_run_manifest(path)
    resume_guard(loaded, state)

    drifted = replace(state, fingerprint="0" * 64)
    with pytest.raises(StopRequired) as exc:
        resume_guard(loaded, drifted)
    assert exc.value.reason == "RUN_STATE_DRIFT"


@pytest.mark.parametrize(
    ("state", "target_content", "expected_content", "backup_remains"),
    [
        ("ORIGINAL_CLAIMED", None, b"original\n", False),
        ("CANDIDATE_INSTALLED", b"candidate\n", b"original\n", False),
        ("VERIFIED", b"candidate\n", b"original\n", False),
        ("RECOVERY_RELEASED", b"candidate\n", b"candidate\n", False),
    ],
)
def test_write_ahead_recovery_at_each_filesystem_boundary(
    tmp_path: Path,
    state: str,
    target_content: bytes | None,
    expected_content: bytes,
    backup_remains: bool,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "x.py"
    backup = repo / "x.py.opsx-original-test"
    temporary = repo / "x.py.opsx-tmp-test"
    original = b"original\n"
    candidate = b"candidate\n"
    backup.write_bytes(original)
    temporary.write_bytes(candidate)
    if target_content is not None:
        target.write_bytes(target_content)
    transaction_root = tmp_path / "state" / "write-transactions"
    journal = transaction_root / "run" / "tx.json"
    journal.parent.mkdir(parents=True)
    journal.write_text(
        json.dumps(
            {
                "schema": "opsx-resolve-conflict/write-transaction/v1",
                "repository_root": str(repo.resolve()),
                "run_id": "run",
                "path": "x.py",
                "tmp": "x.py.opsx-tmp-test",
                "backup": "x.py.opsx-original-test",
                "original_sha256": hashlib.sha256(original).hexdigest(),
                "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
                "metadata": {"mode": 420},
                "state": state,
            }
        ),
        encoding="utf-8",
    )

    recover_write_transactions(repo, transaction_root)

    assert target.read_bytes() == expected_content
    assert backup.exists() is backup_remains
    assert not temporary.exists()
    recovered = json.loads(journal.read_text(encoding="utf-8"))
    expected_state = (
        "RETIRED"
        if state == "RECOVERY_RELEASED"
        else "ROLLED_BACK"
    )
    assert recovered["state"] == expected_state
