"""R33 WINDOWS_PREVIEW_ONLY advisory preview tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from opsx_conflict.attestation import assert_supported_platform
from opsx_conflict.errors import StopRequired
from opsx_conflict.preview_advisory import SAFETY_LABEL_RU, run_preview_advisory
from opsx_conflict.preview_readonly_git import PreviewReadonlyGit
from opsx_conflict.runtime import run_cli


def _run(argv: list[str], cwd: Path) -> None:
    import subprocess

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


def _make_merge_conflict(repo: Path) -> None:
    _run(["git", "config", "user.email", "preview@example.invalid"], repo)
    _run(["git", "config", "user.name", "Preview Fixture"], repo)
    (repo / "conflict.py").write_text(
        'def base():\n    return "base"\n',
        encoding="utf-8",
    )
    _run(["git", "add", "conflict.py"], repo)
    _run(["git", "commit", "-m", "base"], repo)
    _run(["git", "checkout", "-b", "feature"], repo)
    (repo / "conflict.py").write_text(
        'def base():\n    return "base"\n\ndef feature_write():\n    return "feature"\n',
        encoding="utf-8",
    )
    _run(["git", "add", "conflict.py"], repo)
    _run(["git", "commit", "-m", "feature"], repo)
    _run(["git", "checkout", "main"], repo)
    (repo / "conflict.py").write_text(
        'def base():\n    return "base"\n\ndef main_write():\n    return "main"\n',
        encoding="utf-8",
    )
    _run(["git", "add", "conflict.py"], repo)
    _run(["git", "commit", "-m", "main"], repo)
    proc = __import__("subprocess").run(
        ["git", "merge", "feature", "--no-edit"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def _make_rebase_conflict(repo: Path) -> None:
    _run(["git", "config", "user.email", "preview@example.invalid"], repo)
    _run(["git", "config", "user.name", "Preview Fixture"], repo)
    (repo / "x.py").write_text("v1 = 1\n", encoding="utf-8")
    _run(["git", "add", "x.py"], repo)
    _run(["git", "commit", "-m", "c1"], repo)
    _run(["git", "checkout", "-b", "topic"], repo)
    (repo / "x.py").write_text("v1 = 1\ntopic = 2\n", encoding="utf-8")
    _run(["git", "add", "x.py"], repo)
    _run(["git", "commit", "-m", "topic"], repo)
    _run(["git", "checkout", "main"], repo)
    (repo / "x.py").write_text("v1 = 1\nmain = 3\n", encoding="utf-8")
    _run(["git", "add", "x.py"], repo)
    _run(["git", "commit", "-m", "main2"], repo)
    _run(["git", "checkout", "topic"], repo)
    proc = __import__("subprocess").run(
        ["git", "rebase", "main"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


@pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")
def test_merge_preview(git_repo: Path) -> None:
    """Merge fixture yields advisory report with stage blobs."""
    _make_merge_conflict(git_repo)
    report = run_preview_advisory(git_repo)
    assert report["status"] == "PREVIEW_READY"
    assert report["safe_usage_scope"] == "PREVIEW_ONLY"
    assert report["go_capability"] is False
    assert report["CURRENT_CONFLICT"]["operation"] == "merge"
    ids = report["CURRENT_CONFLICT"]["stage_blob_identities"]
    assert ids["2"] and ids["3"]
    assert report["MUTATION_ASSERTION"]["index_unchanged"] is True
    assert SAFETY_LABEL_RU.splitlines()[0] in report["human_report_ru"]
    assert any("authority" in x.lower() or "producer" in x.lower() for x in report["LIMITATIONS"])
    assert any("sandbox" in x.lower() for x in report["LIMITATIONS"])
    assert len(report["RESOLUTION_OPTIONS"]) >= 2
    verbs = {e["argv"][0] for e in report["command_ledger"] if e["argv"]}
    assert "add" not in verbs
    assert "commit" not in verbs
    assert "push" not in verbs


@pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")
def test_rebase_preview(git_repo: Path) -> None:
    """Rebase fixture yields advisory report."""
    _make_rebase_conflict(git_repo)
    report = run_preview_advisory(git_repo)
    assert report["status"] == "PREVIEW_READY"
    assert report["CURRENT_CONFLICT"]["operation"] == "rebase"
    assert report["CURRENT_CONFLICT"]["stage_blob_identities"]["2"]
    assert report["CURRENT_CONFLICT"]["stage_blob_identities"]["3"]


@pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")
def test_single_path_and_invalid_path(git_repo: Path) -> None:
    """Path filter accepts unmerged path and rejects others."""
    _make_merge_conflict(git_repo)
    ok = run_preview_advisory(git_repo, path="conflict.py")
    assert ok["CURRENT_CONFLICT"]["path"] == "conflict.py"
    with pytest.raises(StopRequired) as exc:
        run_preview_advisory(git_repo, path="missing.py")
    assert exc.value.reason == "PREVIEW_PATH_NOT_UNMERGED"


@pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")
def test_no_unmerged_state(git_repo: Path) -> None:
    """Clean repo fails closed."""
    (git_repo / "a.txt").write_text("a\n", encoding="utf-8")
    _run(["git", "add", "a.txt"], git_repo)
    _run(["git", "commit", "-m", "a"], git_repo)
    with pytest.raises(StopRequired) as exc:
        run_preview_advisory(git_repo)
    assert exc.value.reason in {
        "PREVIEW_NO_ACTIVE_CONFLICT_OPERATION",
        "PREVIEW_NO_UNMERGED_PATHS",
    }


@pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")
def test_mutating_command_rejection(git_repo: Path) -> None:
    """Public API has no arbitrary argv path; config/add cannot be represented."""
    git = PreviewReadonlyGit(git_repo)
    assert not hasattr(git, "run") or not callable(getattr(git, "run", None))
    from opsx_conflict.preview_readonly_git import compile_operation_argv

    with pytest.raises(StopRequired) as exc:
        compile_operation_argv("config")
    assert exc.value.reason == "PREVIEW_UNKNOWN_OPERATION"
    with pytest.raises(StopRequired) as exc2:
        compile_operation_argv("symbolic-ref")
    assert exc2.value.reason == "PREVIEW_UNKNOWN_OPERATION"


@pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")
def test_worktree_mutation_detected(git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Worktree change during analysis invalidates report."""
    _make_merge_conflict(git_repo)
    real_capture = None
    import opsx_conflict.preview_advisory as adv

    calls = {"n": 0}
    real = adv._capture_state

    def flaky(git, *, paths):  # type: ignore[no-untyped-def]
        out = real(git, paths=paths)
        calls["n"] += 1
        if calls["n"] == 2:
            target = git_repo / paths[0]
            target.write_text(target.read_text(encoding="utf-8") + "\n# mutated\n", encoding="utf-8")
            out = real(git, paths=paths)
        return out

    monkeypatch.setattr(adv, "_capture_state", flaky)
    with pytest.raises(StopRequired) as exc:
        run_preview_advisory(git_repo)
    assert exc.value.reason == "PREVIEW_WORKTREE_MUTATION"


def test_non_windows_early_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Platform gate fires before advisory Git use."""
    import opsx_conflict.attestation as att

    monkeypatch.setattr(att, "_host_is_windows", lambda: False)
    with pytest.raises(StopRequired) as exc:
        assert_supported_platform()
    assert exc.value.reason == "UNSUPPORTED_PLATFORM"
    with pytest.raises(StopRequired) as exc2:
        run_preview_advisory(Path("."), path="x")
    assert exc2.value.reason == "UNSUPPORTED_PLATFORM"


@pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")
def test_cli_preview_json(git_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """CLI preview --format json returns PREVIEW_READY."""
    _make_merge_conflict(git_repo)
    code = run_cli(["preview", "--repo", str(git_repo), "--format", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "PREVIEW_READY"
    assert data["human_report_ru"].startswith("ADVISORY PREVIEW")


@pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")
def test_facts_vs_interpretations_schema(git_repo: Path) -> None:
    """Facts and interpretations are separate lists."""
    _make_merge_conflict(git_repo)
    report = run_preview_advisory(git_repo)
    assert isinstance(report["FACTS"], list) and report["FACTS"]
    assert isinstance(report["INTERPRETATIONS"], list)
    for item in report["INTERPRETATIONS"]:
        assert item.get("mark") == "inference"
    # Ambiguous both-sides change should request Owner decision.
    assert isinstance(report["OWNER_DECISIONS_REQUIRED"], list)
    assert report["RECOMMENDATION"] is None or isinstance(report["RECOMMENDATION"], dict)
