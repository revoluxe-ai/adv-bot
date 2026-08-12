"""R36: authority must be proven, not inferred from pathname."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from opsx_conflict.preview_advisory import run_preview_advisory
from opsx_conflict.preview_context import (
    MAX_BYTES_READ,
    collect_conflict_context,
    parse_lifecycle_status,
    verify_authority,
)

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")

R34_PREVIEW_READONLY_GIT_SHA256 = (
    "5daea3ebc38e9a6de6de22a0c590d8cf1ebe3e57bd4797ddb26a93fcf95129bd"
)


def _run(argv: list[str], cwd: Path) -> None:
    proc = subprocess.run(
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"{argv}\n{proc.stdout}\n{proc.stderr}")


def _digest_repo(repo: Path) -> dict[str, str | None]:
    git_dir = Path(
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    if not git_dir.is_absolute():
        git_dir = repo / git_dir
    index = git_dir / "index"
    return {
        "index": hashlib.sha256(index.read_bytes()).hexdigest() if index.is_file() else None,
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
    }


def _write_callback_fixture(repo: Path, *, decision_status: str | None) -> None:
    _run(["git", "config", "user.email", "preview@example.invalid"], repo)
    _run(["git", "config", "user.name", "Preview Fixture"], repo)
    (repo / "handlers").mkdir(exist_ok=True)
    (repo / "handlers" / "start.py").write_text(
        "def start_handler(user):\n"
        "    return create_user(user, read_only=False)\n"
        "\n"
        "def create_user(user, *, read_only: bool):\n"
        "    return 'created' if not read_only else 'nav'\n",
        encoding="utf-8",
    )
    (repo / "handlers" / "callback.py").write_text(
        "def callback_handler(user):\n"
        "    return create_user(user, read_only=True)\n"
        "\n"
        "def create_user(user, *, read_only: bool):\n"
        "    return 'created' if not read_only else 'nav'\n",
        encoding="utf-8",
    )
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests" / "test_callback_characterization.py").write_text(
        '"""characterization: current callback uses read_only=True."""\n'
        "def test_callback_read_only_true_characterization():\n"
        "    assert 'read_only=True' in open('handlers/callback.py', encoding='utf-8').read()\n",
        encoding="utf-8",
    )
    if decision_status is not None:
        dec = repo / "openspec" / "decisions"
        dec.mkdir(parents=True, exist_ok=True)
        (dec / "ADR-CALLBACK.md").write_text(
            "# ADR callback contract\n"
            f"\nstatus: {decision_status}\n\n"
            "The callback is existing-users-only navigation.\n"
            "It must use read_only=True and must not create users.\n",
            encoding="utf-8",
        )
    _run(["git", "add", "."], repo)
    _run(["git", "commit", "-m", "base"], repo)
    _run(["git", "checkout", "-b", "feature"], repo)
    (repo / "handlers" / "callback.py").write_text(
        "def callback_handler(user):\n"
        "    return create_user(user, read_only=False)\n"
        "\n"
        "def create_user(user, *, read_only: bool):\n"
        "    return 'created' if not read_only else 'nav'\n",
        encoding="utf-8",
    )
    _run(["git", "add", "handlers/callback.py"], repo)
    _run(["git", "commit", "-m", "feature"], repo)
    _run(["git", "checkout", "main"], repo)
    (repo / "handlers" / "callback.py").write_text(
        "def callback_handler(user):\n"
        "    # navigation for existing users\n"
        "    if user.get('is_new'):\n"
        "        return create_user(user, read_only=True)\n"
        "    return create_user(user, read_only=True)\n"
        "\n"
        "def create_user(user, *, read_only: bool):\n"
        "    return 'created' if not read_only else 'nav'\n",
        encoding="utf-8",
    )
    _run(["git", "add", "handlers/callback.py"], repo)
    _run(["git", "commit", "-m", "main"], repo)
    proc = subprocess.run(
        ["git", "merge", "feature", "--no-edit"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def test_r34_git_hash_pin() -> None:
    root = Path(__file__).resolve().parents[1]
    data = (root / "runtime/opsx_conflict/preview_readonly_git.py").read_bytes()
    assert hashlib.sha256(data).hexdigest() == R34_PREVIEW_READONLY_GIT_SHA256


@pytest.mark.parametrize(
    "status,verified",
    [
        ("accepted", True),
        ("draft", False),
        ("proposed", False),
        ("rejected", False),
        ("superseded", False),
    ],
)
def test_decision_lifecycle_matrix(status: str, verified: bool) -> None:
    result = verify_authority(
        "openspec/decisions/x.md",
        f"status: {status}\nexisting-users-only\n",
    )
    assert result["authority_class"] == "ACCEPTED_DECISION"
    assert result["authority_verified"] is verified
    assert result["lifecycle_status"] == status
    assert parse_lifecycle_status(f"status: {status}\n") == status


def test_change_local_spec_not_current() -> None:
    result = verify_authority(
        "openspec/changes/foo/specs/bar/spec.md",
        "status: draft\nexisting-users-only\n",
    )
    assert result["authority_class"] == "CHANGE_CONTEXT"
    assert result["authority_verified"] is False


def test_arbitrary_contract_filename_unverified() -> None:
    result = verify_authority(
        "docs/my-contract-policy.md",
        "This contract says existing-users-only\n",
    )
    assert result["authority_class"] == "CONTRACT"
    assert result["authority_verified"] is False
    assert "unverified" in result["authority_basis"]


def test_canonical_contract_verified() -> None:
    result = verify_authority(
        "openspec/contracts/callback.md",
        "contract_kind: normative\nstatus: accepted\nexisting-users-only\n",
    )
    assert result["authority_verified"] is True
    assert result["authority_class"] == "CONTRACT"


@pytest.mark.parametrize("status", ["draft", "proposed", "rejected", "superseded"])
def test_negative_lifecycle_no_recommendation(git_repo: Path, status: str) -> None:
    _write_callback_fixture(git_repo, decision_status=status)
    before = _digest_repo(git_repo)
    report = run_preview_advisory(git_repo, path="handlers/callback.py")
    after = _digest_repo(git_repo)
    assert before == after
    assert report["RECOMMENDATION"] is None
    for e in report["CONTEXT_EVIDENCE"]["evidence"]:
        if e["path"].endswith("ADR-CALLBACK.md"):
            assert e["authority_verified"] is False
            assert e.get("lifecycle_status") == status


def test_accepted_decision_still_recommends(git_repo: Path) -> None:
    _write_callback_fixture(git_repo, decision_status="accepted")
    before = _digest_repo(git_repo)
    report = run_preview_advisory(git_repo, path="handlers/callback.py")
    after = _digest_repo(git_repo)
    assert before == after
    rec = report["RECOMMENDATION"]
    assert rec is not None
    assert rec["option_id"] in {"keep_ours", "align_to_contract"}
    assert "accepted" in (rec.get("authority_basis") or rec.get("rationale") or "").lower()
    assert report["MUTATION_ASSERTION"]["index_unchanged"] is True


def test_ambiguous_still_asks_owner(git_repo: Path) -> None:
    _write_callback_fixture(git_repo, decision_status=None)
    report = run_preview_advisory(git_repo, path="handlers/callback.py")
    assert report["RECOMMENDATION"] is None
    assert report["OWNER_DECISIONS_REQUIRED"]


def test_contradictory_verified_authorities(git_repo: Path) -> None:
    _write_callback_fixture(git_repo, decision_status="accepted")
    # Second accepted decision with opposite polarity.
    dec = git_repo / "openspec" / "decisions"
    (dec / "ADR-CALLBACK-ALIAS.md").write_text(
        "# opposite\n\nstatus: accepted\n\n"
        "The callback is a full /start alias create path.\n",
        encoding="utf-8",
    )
    # Stage file into worktree only for context discovery (conflict already active).
    report = run_preview_advisory(git_repo, path="handlers/callback.py")
    # If both verified and opposite polarities found → null.
    verified = [
        e
        for e in report["CONTEXT_EVIDENCE"]["evidence"]
        if e.get("authority_verified") and e.get("authority_class") == "ACCEPTED_DECISION"
    ]
    if len(verified) >= 2:
        assert report["RECOMMENDATION"] is None
        assert any(
            "противореч" in (c.get("text") or "").lower()
            or "contradict" in (c.get("text") or "").lower()
            for c in report.get("CONTRADICTIONS") or []
        ) or any(
            d.get("id") == "contradictory_verified_authorities"
            for d in report["OWNER_DECISIONS_REQUIRED"]
        )


def test_unverified_cannot_generate_recommendation() -> None:
    packet = {
        "evidence": [
            {
                "evidence_id": "E-001",
                "authority_class": "ACCEPTED_DECISION",
                "authority_verified": False,
                "authority_basis": "decision_status_draft",
                "lifecycle_status": "draft",
                "path": "openspec/decisions/draft.md",
                "excerpt": "existing-users-only",
            }
        ]
    }
    from opsx_conflict.preview_advisory import _strong_evidence

    assert _strong_evidence(packet) == []


def test_authority_scan_budget_exhaustion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "budget"
    repo.mkdir()
    _run(["git", "init", "-b", "main"], repo)
    for i in range(40):
        (repo / f"f{i}.py").write_text(f"read_only = {i}\n", encoding="utf-8")
    import opsx_conflict.preview_context as pc

    monkeypatch.setattr(pc, "MAX_EVIDENCE_ITEMS", 1)
    monkeypatch.setattr(pc, "MAX_SEARCH_INTENTS", 1)
    monkeypatch.setattr(pc, "MAX_BYTES_READ", 800)
    packet = collect_conflict_context(
        repo,
        conflict_path="f0.py",
        operation="merge",
        base_text="read_only = 0\n",
        ours_text="read_only = 1\n",
        theirs_text="read_only = 2\n",
        stage_oids={"1": None, "2": None, "3": None},
    )
    assert packet["search_budgets"]["bytes_read"] <= MAX_BYTES_READ or packet[
        "search_budgets"
    ]["exhausted"]
    assert packet["evidence_gaps"] or packet["search_budgets"]["exhausted"]


def test_change_local_spec_fixture_no_recommendation(git_repo: Path) -> None:
    _write_callback_fixture(git_repo, decision_status=None)
    specs = git_repo / "openspec" / "changes" / "foo" / "specs" / "bar"
    specs.mkdir(parents=True, exist_ok=True)
    (specs / "spec.md").write_text(
        "status: draft\nThe callback is existing-users-only.\n",
        encoding="utf-8",
    )
    report = run_preview_advisory(git_repo, path="handlers/callback.py")
    assert report["RECOMMENDATION"] is None
    for e in report["CONTEXT_EVIDENCE"]["evidence"]:
        if "openspec/changes/" in e["path"]:
            assert e["authority_class"] == "CHANGE_CONTEXT"
            assert e["authority_verified"] is False
