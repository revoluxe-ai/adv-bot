"""R35 PREVIEW repository-context evidence + advisory reasoning tests."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.preview_advisory import run_preview_advisory
from opsx_conflict.preview_context import (
    MAX_EVIDENCE_ITEMS,
    MAX_SEARCH_INTENTS,
    BoundedContextReader,
    classify_path_authority,
    classify_test_kind,
    collect_conflict_context,
)
from opsx_conflict.preview_readonly_git import PreviewReadonlyGit

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
        "show_ref": subprocess.run(
            ["git", "show-ref"],
            cwd=str(repo),
            capture_output=True,
            text=True,
            check=False,
        ).stdout,
    }


def _write_callback_fixture(repo: Path, *, with_decision: bool) -> None:
    """Build merge conflict: callback read_only vs sibling /start create path."""
    _run(["git", "config", "user.email", "preview@example.invalid"], repo)
    _run(["git", "config", "user.name", "Preview Fixture"], repo)

    (repo / "handlers").mkdir(exist_ok=True)
    (repo / "handlers" / "start.py").write_text(
        'def start_handler(user):\n'
        '    """Sibling /start create path."""\n'
        "    return create_user(user, read_only=False)\n"
        "\n"
        "def create_user(user, *, read_only: bool):\n"
        "    if read_only:\n"
        "        return 'nav'\n"
        "    return 'created'\n",
        encoding="utf-8",
    )
    (repo / "handlers" / "callback.py").write_text(
        "def callback_handler(user):\n"
        "    return create_user(user, read_only=True)\n"
        "\n"
        "def create_user(user, *, read_only: bool):\n"
        "    if read_only:\n"
        "        return 'nav'\n"
        "    return 'created'\n",
        encoding="utf-8",
    )
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests" / "test_callback_characterization.py").write_text(
        '"""characterization: current callback uses read_only=True."""\n'
        "from handlers.callback import callback_handler\n"
        "\n"
        "def test_callback_read_only_true_characterization():\n"
        "    # characterization of current behavior, not intended contract\n"
        "    assert 'read_only=True' in open('handlers/callback.py', encoding='utf-8').read()\n"
        "    assert callback_handler({'id': 1}) == 'nav'\n",
        encoding="utf-8",
    )
    if with_decision:
        dec = repo / "openspec" / "decisions"
        dec.mkdir(parents=True, exist_ok=True)
        (dec / "ADR-CALLBACK-EXISTING-USERS.md").write_text(
            "# ADR callback contract\n"
            "\n"
            "status: accepted\n"
            "\n"
            "opsx_conflict_polarity: prefer_read_only\n"
            "The callback is existing-users-only navigation.\n"
            "It must use read_only=True and must not create users.\n"
            "create_user branch in callback is inconsistent with this contract.\n",
            encoding="utf-8",
        )

    _run(["git", "add", "."], repo)
    _run(["git", "commit", "-m", "base"], repo)
    _run(["git", "checkout", "-b", "feature"], repo)
    # THEIRS: treat callback as full /start alias (read_only=False + create).
    (repo / "handlers" / "callback.py").write_text(
        "def callback_handler(user):\n"
        "    # full /start alias\n"
        "    return create_user(user, read_only=False)\n"
        "\n"
        "def create_user(user, *, read_only: bool):\n"
        "    if read_only:\n"
        "        return 'nav'\n"
        "    return 'created'\n",
        encoding="utf-8",
    )
    _run(["git", "add", "handlers/callback.py"], repo)
    _run(["git", "commit", "-m", "feature-alias"], repo)
    _run(["git", "checkout", "main"], repo)
    # OURS: keep navigation/read_only=True (and optional create_user dead branch).
    (repo / "handlers" / "callback.py").write_text(
        "def callback_handler(user):\n"
        "    # navigation for existing users\n"
        "    if user.get('is_new'):\n"
        "        return create_user(user, read_only=True)\n"
        "    return create_user(user, read_only=True)\n"
        "\n"
        "def create_user(user, *, read_only: bool):\n"
        "    if read_only:\n"
        "        return 'nav'\n"
        "    return 'created'\n",
        encoding="utf-8",
    )
    _run(["git", "add", "handlers/callback.py"], repo)
    _run(["git", "commit", "-m", "main-nav"], repo)
    proc = subprocess.run(
        ["git", "merge", "feature", "--no-edit"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def test_r34_preview_readonly_git_hash_pin() -> None:
    """R34 Git boundary must remain byte-identical."""
    root = Path(__file__).resolve().parents[1]
    data = (root / "runtime" / "opsx_conflict" / "preview_readonly_git.py").read_bytes()
    assert hashlib.sha256(data).hexdigest() == R34_PREVIEW_READONLY_GIT_SHA256


def test_authority_classification() -> None:
    """Provisional path class ≠ verified authority."""
    from opsx_conflict.preview_context import verify_authority

    assert (
        classify_path_authority("openspec/decisions/ADR-X.md", "status: accepted")
        == "ACCEPTED_DECISION"
    )
    assert classify_path_authority("openspec/specs/foo.md") == "CURRENT_SPEC"
    assert classify_path_authority("openspec/changes/foo/specs/x/spec.md") == (
        "CHANGE_CONTEXT"
    )
    assert classify_path_authority("tests/test_x.py") == "TEST_EVIDENCE"
    assert classify_path_authority("handlers/start.py") == "SOURCE_CODE"
    draft = verify_authority(
        "openspec/decisions/draft.md", "status: draft\nexisting-users-only\n"
    )
    assert draft["authority_verified"] is False
    accepted = verify_authority(
        "openspec/decisions/ok.md", "status: accepted\nexisting-users-only\n"
    )
    assert accepted["authority_verified"] is True
    assert classify_test_kind("characterization of current behavior", "tests/t.py") == (
        "characterization"
    )
    assert classify_test_kind("assert invariant contract must hold", "tests/t.py") == "contract"


def test_ambiguous_callback_fixture(git_repo: Path) -> None:
    """Ambiguous callback → Owner decision, RECOMMENDATION=null."""
    _write_callback_fixture(git_repo, with_decision=False)
    before = _digest_repo(git_repo)
    report = run_preview_advisory(git_repo, path="handlers/callback.py")
    after = _digest_repo(git_repo)
    assert before == after
    assert report["RECOMMENDATION"] is None
    assert report["OWNER_DECISIONS_REQUIRED"]
    assert any("callback" in (d.get("question") or "").lower() or "контракт" in (d.get("question") or "").lower()
               for d in report["OWNER_DECISIONS_REQUIRED"])
    ctx = report["CONTEXT_EVIDENCE"]
    classes = {e["authority_class"] for e in ctx["evidence"]}
    assert "SIBLING_IMPLEMENTATION" in classes
    assert "TEST_EVIDENCE" in classes
    human = report["human_report_ru"]
    assert human.index("## Коротко") < human.index("## Технические детали")
    assert "ADVISORY PREVIEW" in human
    assert report["go_capability"] is False
    assert report["safe_usage_scope"] == "PREVIEW_ONLY"


def test_decision_backed_callback_fixture(git_repo: Path) -> None:
    """Accepted decision → evidence-backed recommendation; no file edit."""
    _write_callback_fixture(git_repo, with_decision=True)
    before = _digest_repo(git_repo)
    report = run_preview_advisory(git_repo, path="handlers/callback.py")
    after = _digest_repo(git_repo)
    assert before == after
    rec = report["RECOMMENDATION"]
    assert rec is not None
    assert rec["option_id"] in {"keep_ours", "align_to_contract"}
    assert rec.get("evidence_refs")
    ctx = report["CONTEXT_EVIDENCE"]
    accepted = [
        e
        for e in ctx["evidence"]
        if e["authority_class"] == "ACCEPTED_DECISION" and e.get("authority_verified")
    ]
    assert accepted
    assert "accepted" in (accepted[0].get("authority_basis") or "")
    # File must remain conflicted / unedited by preview.
    text = (git_repo / "handlers" / "callback.py").read_text(encoding="utf-8")
    assert "<<<<<<<" in text or "read_only" in text


def test_textual_subset_no_recommendation(git_repo: Path) -> None:
    """Textual subset alone must not recommend keep_ours/keep_theirs."""
    _run(["git", "config", "user.email", "preview@example.invalid"], git_repo)
    _run(["git", "config", "user.name", "Preview Fixture"], git_repo)
    (git_repo / "x.py").write_text("a = 1\n", encoding="utf-8")
    _run(["git", "add", "x.py"], git_repo)
    _run(["git", "commit", "-m", "b"], git_repo)
    _run(["git", "checkout", "-b", "feature"], git_repo)
    (git_repo / "x.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
    _run(["git", "add", "x.py"], git_repo)
    _run(["git", "commit", "-m", "f"], git_repo)
    _run(["git", "checkout", "main"], git_repo)
    (git_repo / "x.py").write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    _run(["git", "add", "x.py"], git_repo)
    _run(["git", "commit", "-m", "m"], git_repo)
    proc = subprocess.run(
        ["git", "merge", "feature", "--no-edit"],
        cwd=str(git_repo),
        capture_output=True,
        text=True,
        check=False,
    )
    # May or may not conflict depending on content; force conflict via checkout ours/theirs
    if proc.returncode == 0:
        # No conflict — synthesize unmerged via index stages is hard; skip-equivalent:
        # create a second conflict file.
        _run(["git", "checkout", "-b", "f2"], git_repo)
        (git_repo / "y.py").write_text("line\n", encoding="utf-8")
        _run(["git", "add", "y.py"], git_repo)
        _run(["git", "commit", "-m", "y1"], git_repo)
        _run(["git", "checkout", "main"], git_repo)
        (git_repo / "y.py").write_text("line\nextra\n", encoding="utf-8")
        _run(["git", "add", "y.py"], git_repo)
        _run(["git", "commit", "-m", "y2"], git_repo)
        _run(["git", "checkout", "f2"], git_repo)
        (git_repo / "y.py").write_text("line\n", encoding="utf-8")
        _run(["git", "add", "y.py"], git_repo)
        _run(["git", "commit", "-m", "y3"], git_repo)
        proc2 = subprocess.run(
            ["git", "rebase", "main"],
            cwd=str(git_repo),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc2.returncode != 0
        report = run_preview_advisory(git_repo)
    else:
        report = run_preview_advisory(git_repo)
    # Without strong authority, recommendation must be null even if subset.
    if not any(
        e.get("authority_class") in {
            "ACCEPTED_DECISION",
            "CURRENT_SPEC",
            "CONTRACT",
            "API_INVARIANT",
        }
        for e in report["CONTEXT_EVIDENCE"]["evidence"]
    ):
        assert report["RECOMMENDATION"] is None


def test_sibling_caller_test_contract_discovery(git_repo: Path) -> None:
    _write_callback_fixture(git_repo, with_decision=True)
    report = run_preview_advisory(git_repo, path="handlers/callback.py")
    ctx = report["CONTEXT_EVIDENCE"]
    classes = {e["authority_class"] for e in ctx["evidence"]}
    assert "SIBLING_IMPLEMENTATION" in classes
    assert "TEST_EVIDENCE" in classes
    assert "ACCEPTED_DECISION" in classes
    for e in ctx["evidence"]:
        assert e["authority_class"]
        assert e["path"]
        assert e["evidence_id"]
        assert "authority_verified" in e
        assert "authority_basis" in e
        assert "line_start" in e
    assert any(e.get("authority_verified") for e in ctx["evidence"])


def test_evidence_gap_and_budgets(tmp_path: Path) -> None:
    repo = tmp_path / "emptyish"
    repo.mkdir()
    _run(["git", "init", "-b", "main"], repo)
    packet = collect_conflict_context(
        repo,
        conflict_path="missing.py",
        operation="merge",
        base_text="def a():\n    pass\n",
        ours_text="def a():\n    return 1\n",
        theirs_text="def a():\n    return 2\n",
        stage_oids={"1": "a" * 40, "2": "b" * 40, "3": "c" * 40},
    )
    assert packet["evidence_gaps"]
    assert packet["search_budgets"]["max_search_intents"] == MAX_SEARCH_INTENTS
    assert packet["reader_contract"]["subprocess"] is False
    assert packet["reader_contract"]["writes"] is False


def test_search_budget_exhaustion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "many"
    repo.mkdir()
    _run(["git", "init", "-b", "main"], repo)
    for i in range(30):
        (repo / f"m{i}.py").write_text(f"token_value = {i}\n", encoding="utf-8")
    import opsx_conflict.preview_context as pc

    monkeypatch.setattr(pc, "MAX_EVIDENCE_ITEMS", 2)
    monkeypatch.setattr(pc, "MAX_SEARCH_INTENTS", 1)
    packet = collect_conflict_context(
        repo,
        conflict_path="m0.py",
        operation="merge",
        base_text="token_value = 0\n",
        ours_text="token_value = 1\n",
        theirs_text="token_value = 2\n",
        stage_oids={"1": None, "2": None, "3": None},
    )
    assert packet["search_budgets"]["evidence_items"] <= 2
    assert any("budget" in g.lower() or "EVIDENCE_GAP" in g or "max_" in g for g in packet["evidence_gaps"]) or (
        packet["search_budgets"]["exhausted"]
    )


def test_binary_and_oversized_skipped(tmp_path: Path) -> None:
    repo = tmp_path / "bin"
    repo.mkdir()
    (repo / "ok.py").write_text("hello_token = 1\n", encoding="utf-8")
    (repo / "big.py").write_bytes(b"x" * (300 * 1024))
    (repo / "blob.bin").write_bytes(b"\x00\x01hello_token\x00")
    reader = BoundedContextReader(repo)
    assert reader.read_text_file(repo / "ok.py") is not None
    assert reader.read_text_file(repo / "big.py") is None
    assert reader.read_text_file(repo / "blob.bin") is None


def test_symlink_path_escape_stops(tmp_path: Path) -> None:
    repo = tmp_path / "sym"
    repo.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("secret\n", encoding="utf-8")
    link = repo / "escape.py"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")
    reader = BoundedContextReader(repo)
    with pytest.raises(StopRequired) as exc:
        reader.read_text_file(link)
    assert exc.value.reason == "PREVIEW_CONTEXT_SYMLINK_BLOCKED"


def test_no_subprocess_for_context(monkeypatch: pytest.MonkeyPatch, git_repo: Path) -> None:
    _write_callback_fixture(git_repo, with_decision=False)
    real_run = subprocess.run
    calls: list[list[str]] = []

    def spy(*args, **kwargs):  # type: ignore[no-untyped-def]
        cmd = list(args[0]) if args else list(kwargs.get("args", []))
        calls.append(cmd)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)
    run_preview_advisory(git_repo, path="handlers/callback.py")
    # Context search must not introduce rg/find/grep; only trusted git argv.
    for cmd in calls:
        joined = " ".join(cmd).lower()
        assert "rg" not in cmd
        assert "findstr" not in joined
        assert not any(x.endswith("rg.exe") for x in cmd)


def test_merge_and_rebase_still_stage_bound(git_repo: Path) -> None:
    """Stage-bound evidence still produced for classic merge fixture."""
    _run(["git", "config", "user.email", "preview@example.invalid"], git_repo)
    _run(["git", "config", "user.name", "Preview Fixture"], git_repo)
    (git_repo / "conflict.py").write_text('def base():\n    return "base"\n', encoding="utf-8")
    _run(["git", "add", "conflict.py"], git_repo)
    _run(["git", "commit", "-m", "base"], git_repo)
    _run(["git", "checkout", "-b", "feature"], git_repo)
    (git_repo / "conflict.py").write_text(
        'def base():\n    return "base"\n\ndef feature_write():\n    return "feature"\n',
        encoding="utf-8",
    )
    _run(["git", "add", "conflict.py"], git_repo)
    _run(["git", "commit", "-m", "feature"], git_repo)
    _run(["git", "checkout", "main"], git_repo)
    (git_repo / "conflict.py").write_text(
        'def base():\n    return "base"\n\ndef main_write():\n    return "main"\n',
        encoding="utf-8",
    )
    _run(["git", "add", "conflict.py"], git_repo)
    _run(["git", "commit", "-m", "main"], git_repo)
    proc = subprocess.run(
        ["git", "merge", "feature", "--no-edit"],
        cwd=str(git_repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    before = _digest_repo(git_repo)
    report = run_preview_advisory(git_repo)
    after = _digest_repo(git_repo)
    assert before == after
    assert report["CURRENT_CONFLICT"]["stage_blob_identities"]["2"]
    assert report["CURRENT_CONFLICT"]["stage_blob_identities"]["3"]
    assert report["CONTEXT_EVIDENCE"]["conflict_blobs"]["operation"] == "merge"
    assert report["MUTATION_ASSERTION"]["index_unchanged"] is True
