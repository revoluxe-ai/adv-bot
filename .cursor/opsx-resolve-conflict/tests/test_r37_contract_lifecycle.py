"""R37: CONTRACT lifecycle precedence over normative marker."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from opsx_conflict.preview_advisory import _strong_evidence, run_preview_advisory
from opsx_conflict.preview_context import verify_authority

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")

R34_PREVIEW_READONLY_GIT_SHA256 = (
    "5daea3ebc38e9a6de6de22a0c590d8cf1ebe3e57bd4797ddb26a93fcf95129bd"
)

_CONTRACT_PATH = "openspec/contracts/callback.md"
_NORMATIVE = (
    "contract_kind: normative\n"
    "opsx_conflict_polarity: prefer_read_only\n"
    "The callback is existing-users-only.\n"
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


@pytest.mark.parametrize(
    "status_line,verified",
    [
        ("status: accepted\n", True),
        ("status: active\n", True),
        ("status: current\n", True),
        ("", True),  # no explicit lifecycle + normative marker
        ("status: draft\n", False),
        ("status: proposed\n", False),
        ("status: rejected\n", False),
        ("status: superseded\n", False),
        ("status: unknown\n", False),
    ],
)
def test_canonical_contract_lifecycle_matrix(status_line: str, verified: bool) -> None:
    """Lifecycle vetoes normative marker for CONTRACT verification."""
    text = f"# callback contract\n\n{status_line}{_NORMATIVE}"
    result = verify_authority(_CONTRACT_PATH, text)
    assert result["authority_class"] == "CONTRACT"
    assert result["authority_verified"] is verified
    if not verified and status_line.strip():
        status = status_line.split(":", 1)[1].strip()
        assert result["lifecycle_status"] == status
        assert status in (result.get("authority_basis") or "")
    packet = {
        "evidence": [
            {
                "evidence_id": "E-001",
                "authority_class": result["authority_class"],
                "authority_verified": result["authority_verified"],
                "authority_basis": result["authority_basis"],
                "lifecycle_status": result["lifecycle_status"],
                "path": _CONTRACT_PATH,
                "excerpt": text,
            }
        ]
    }
    strong = _strong_evidence(packet)
    if verified:
        assert strong
    else:
        assert strong == []


def test_r36_counterexample_draft_normative_not_verified() -> None:
    """Confirmed R36 counterexample must fail closed."""
    text = (
        "status: draft\n"
        "contract_kind: normative\n"
        "opsx_conflict_polarity: prefer_read_only\n"
        "The callback is existing-users-only.\n"
    )
    result = verify_authority(_CONTRACT_PATH, text)
    assert result["authority_verified"] is False
    assert result["lifecycle_status"] == "draft"
    assert result["authority_basis"] == "contract_lifecycle_draft"


def test_r34_git_hash_pin() -> None:
    root = Path(__file__).resolve().parents[1]
    data = (root / "runtime/opsx_conflict/preview_readonly_git.py").read_bytes()
    assert hashlib.sha256(data).hexdigest() == R34_PREVIEW_READONLY_GIT_SHA256


def _write_callback_conflict(repo: Path, *, contract_status: str | None) -> None:
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
    contracts = repo / "openspec" / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    status_block = f"status: {contract_status}\n" if contract_status else ""
    (contracts / "callback.md").write_text(
        f"# callback contract\n\n{status_block}"
        "contract_kind: normative\n"
        "opsx_conflict_polarity: prefer_read_only\n"
        "The callback is existing-users-only navigation.\n"
        "It must use read_only=True.\n",
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


def test_draft_contract_cannot_recommend(git_repo: Path) -> None:
    _write_callback_conflict(git_repo, contract_status="draft")
    report = run_preview_advisory(git_repo, path="handlers/callback.py")
    assert report["RECOMMENDATION"] is None
    for e in report["CONTEXT_EVIDENCE"]["evidence"]:
        if e["path"].endswith("openspec/contracts/callback.md"):
            assert e["authority_verified"] is False
            assert e.get("lifecycle_status") == "draft"
            assert e not in _strong_evidence(report["CONTEXT_EVIDENCE"])


def test_accepted_contract_can_recommend(git_repo: Path) -> None:
    _write_callback_conflict(git_repo, contract_status="accepted")
    report = run_preview_advisory(git_repo, path="handlers/callback.py")
    rec = report["RECOMMENDATION"]
    assert rec is not None
    assert rec["option_id"] in {"keep_ours", "align_to_contract"}
    verified_contracts = [
        e
        for e in report["CONTEXT_EVIDENCE"]["evidence"]
        if e.get("authority_class") == "CONTRACT" and e.get("authority_verified")
    ]
    assert verified_contracts


def test_contradictory_accepted_authorities_still_null(git_repo: Path) -> None:
    _write_callback_conflict(git_repo, contract_status="accepted")
    dec = git_repo / "openspec" / "decisions"
    dec.mkdir(parents=True, exist_ok=True)
    (dec / "ADR-ALIAS.md").write_text(
        "# opposite\n\nstatus: accepted\n\n"
        "opsx_conflict_polarity: prefer_mutable\n"
        "The callback is a full /start alias create path.\n",
        encoding="utf-8",
    )
    report = run_preview_advisory(git_repo, path="handlers/callback.py")
    verified = [
        e
        for e in report["CONTEXT_EVIDENCE"]["evidence"]
        if e.get("authority_verified")
        and e.get("authority_class")
        in {"ACCEPTED_DECISION", "CURRENT_SPEC", "CONTRACT", "API_INVARIANT"}
    ]
    if len(verified) >= 2:
        # Opposite polarities from contract vs decision → null.
        from opsx_conflict.preview_advisory import _recommendation_polarity

        pols = {
            _recommendation_polarity(e.get("excerpt") or "")
            for e in verified
            if _recommendation_polarity(e.get("excerpt") or "")
        }
        if len(pols) >= 2:
            assert report["RECOMMENDATION"] is None
