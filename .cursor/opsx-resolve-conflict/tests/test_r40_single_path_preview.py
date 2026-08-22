"""R40: PREVIEW analyzes exactly one conflicted path per invocation.

Closes BUGBOT-HIGH-002 — omit --path with multiple unmerged paths must STOP
with PREVIEW_PATH_REQUIRED_MULTIPLE_CONFLICTS; successful reports never imply
multi-path semantic coverage.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from opsx_conflict.attestation import PACKAGE_VERSION
from opsx_conflict.errors import StopRequired
from opsx_conflict.preview_advisory import run_preview_advisory
from opsx_conflict.runtime import run_cli

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
R34_PREVIEW_READONLY_GIT_SHA256 = (
    "5daea3ebc38e9a6de6de22a0c590d8cf1ebe3e57bd4797ddb26a93fcf95129bd"
)


def _run(argv: list[str], cwd: Path) -> None:
    """Run a subprocess; raise AssertionError on non-zero exit."""
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


def _fingerprint(repo: Path) -> dict[str, str]:
    """Capture index/refs/unmerged/worktree digests for mutation assertions."""
    def _sha(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    index = subprocess.run(
        ["git", "ls-files", "-s"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    unmerged = subprocess.run(
        ["git", "ls-files", "-u"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    refs = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname) %(objectname)"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {
        "index": _sha(index),
        "unmerged": _sha(unmerged),
        "refs": _sha(refs + head),
        "a": _sha((repo / "a.py").read_text(encoding="utf-8"))
        if (repo / "a.py").is_file()
        else "",
        "b": _sha((repo / "b.py").read_text(encoding="utf-8"))
        if (repo / "b.py").is_file()
        else "",
        "conflict": _sha((repo / "conflict.py").read_text(encoding="utf-8"))
        if (repo / "conflict.py").is_file()
        else "",
    }


def _make_single_merge_conflict(repo: Path) -> None:
    """Create one-file merge conflict (conflict.py)."""
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
    proc = subprocess.run(
        ["git", "merge", "feature", "--no-edit"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def _make_two_path_merge_conflict(repo: Path) -> tuple[str, str]:
    """Create two-file merge conflict; return sorted (path_a, path_b)."""
    _run(["git", "config", "user.email", "preview@example.invalid"], repo)
    _run(["git", "config", "user.name", "Preview Fixture"], repo)
    (repo / "a.py").write_text("A = 1\n", encoding="utf-8")
    (repo / "b.py").write_text("B = 1\n", encoding="utf-8")
    _run(["git", "add", "a.py", "b.py"], repo)
    _run(["git", "commit", "-m", "base"], repo)
    _run(["git", "checkout", "-b", "feature"], repo)
    (repo / "a.py").write_text("A = 1\nfeature_a = True\n", encoding="utf-8")
    (repo / "b.py").write_text("B = 1\nfeature_b = True\n", encoding="utf-8")
    _run(["git", "add", "a.py", "b.py"], repo)
    _run(["git", "commit", "-m", "feature"], repo)
    _run(["git", "checkout", "main"], repo)
    (repo / "a.py").write_text("A = 1\nmain_a = True\n", encoding="utf-8")
    (repo / "b.py").write_text("B = 1\nmain_b = True\n", encoding="utf-8")
    _run(["git", "add", "a.py", "b.py"], repo)
    _run(["git", "commit", "-m", "main"], repo)
    proc = subprocess.run(
        ["git", "merge", "feature", "--no-edit"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    return ("a.py", "b.py")


def _analyzed_surfaces(report: dict) -> str:
    """Concatenate surfaces that must bind only to the selected path."""
    chunks: list[str] = []
    chunks.append(str(report.get("CURRENT_CONFLICT", {}).get("path") or ""))
    chunks.append(json.dumps(report.get("CONTEXT", {}).get("paths_analyzed") or []))
    chunks.append(json.dumps(report.get("FACTS") or [], ensure_ascii=False))
    chunks.append(json.dumps(report.get("RECOMMENDATION") or {}, ensure_ascii=False))
    chunks.append(str(report.get("DISAGREEMENT_RU") or ""))
    chunks.append(str(report.get("SHORT_RU") or ""))
    for key in ("OURS", "THEIRS"):
        side = report.get(key) or {}
        if isinstance(side, dict):
            chunks.append(str(side.get("summary_ru") or ""))
    return "\n".join(chunks)


def test_zero_unmerged_paths_stop(git_repo: Path) -> None:
    """Clean repo → typed STOP (no PREVIEW_READY)."""
    (git_repo / "ok.py").write_text("x = 1\n", encoding="utf-8")
    _run(["git", "add", "ok.py"], git_repo)
    _run(["git", "commit", "-m", "ok"], git_repo)
    with pytest.raises(StopRequired) as exc:
        run_preview_advisory(git_repo)
    assert exc.value.reason in {
        "PREVIEW_NO_ACTIVE_CONFLICT_OPERATION",
        "PREVIEW_NO_UNMERGED_PATHS",
    }


def test_one_unmerged_path_no_flag_preview_ready(git_repo: Path) -> None:
    """Exactly one unmerged path and --path omitted → PREVIEW_READY."""
    _make_single_merge_conflict(git_repo)
    before = _fingerprint(git_repo)
    report = run_preview_advisory(git_repo)
    after = _fingerprint(git_repo)
    assert report["status"] == "PREVIEW_READY"
    assert report["go_capability"] is False
    assert report["CURRENT_CONFLICT"]["path"] == "conflict.py"
    assert report["CONTEXT"]["paths_analyzed"] == ["conflict.py"]
    assert report["CURRENT_CONFLICT"]["all_unmerged_paths_role"] == (
        "inventory_not_analyzed"
    )
    assert before == after
    assert report["MUTATION_ASSERTION"]["worktree_unchanged"] is True
    assert report["MUTATION_ASSERTION"]["index_unchanged"] is True
    assert report["MUTATION_ASSERTION"]["refs_unchanged"] is True


def test_two_unmerged_paths_no_flag_stop(git_repo: Path) -> None:
    """Two unmerged paths without --path → PREVIEW_PATH_REQUIRED_MULTIPLE_CONFLICTS."""
    path_a, path_b = _make_two_path_merge_conflict(git_repo)
    before = _fingerprint(git_repo)
    with pytest.raises(StopRequired) as exc:
        run_preview_advisory(git_repo)
    after = _fingerprint(git_repo)
    assert before == after
    assert exc.value.reason == "PREVIEW_PATH_REQUIRED_MULTIPLE_CONFLICTS"
    listed = exc.value.details.get("unmerged_paths")
    assert listed == sorted([path_a, path_b])
    assert listed == ["a.py", "b.py"]


def test_two_paths_explicit_a_covers_only_a(git_repo: Path) -> None:
    """--path=a.py with two conflicts → report covers only a.py."""
    path_a, path_b = _make_two_path_merge_conflict(git_repo)
    before = _fingerprint(git_repo)
    report = run_preview_advisory(git_repo, path=path_a)
    after = _fingerprint(git_repo)
    assert before == after
    assert report["status"] == "PREVIEW_READY"
    assert report["CURRENT_CONFLICT"]["path"] == path_a
    assert report["CONTEXT"]["paths_analyzed"] == [path_a]
    assert path_b in report["CURRENT_CONFLICT"]["unmerged_paths_inventory"]
    assert path_b not in report["CONTEXT"]["paths_analyzed"]
    surface = _analyzed_surfaces(report)
    assert path_a in surface
    # Other conflict must not appear as analyzed target in reasoning surfaces.
    assert f'"paths_analyzed": ["{path_b}"]' not in json.dumps(report)
    assert report["CONTEXT"]["paths_analyzed"] != [path_b]
    assert report["CURRENT_CONFLICT"]["path"] != path_b


def test_two_paths_explicit_b_covers_only_b(git_repo: Path) -> None:
    """--path=b.py with two conflicts → report covers only b.py."""
    path_a, path_b = _make_two_path_merge_conflict(git_repo)
    report = run_preview_advisory(git_repo, path=path_b)
    assert report["status"] == "PREVIEW_READY"
    assert report["CURRENT_CONFLICT"]["path"] == path_b
    assert report["CONTEXT"]["paths_analyzed"] == [path_b]
    assert path_a in report["CURRENT_CONFLICT"]["unmerged_paths_inventory"]
    assert path_a not in report["CONTEXT"]["paths_analyzed"]
    assert report["CURRENT_CONFLICT"]["path"] != path_a


def test_cli_multiple_conflicts_stop_envelope(
    git_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """CLI preview without --path emits sorted unmerged_paths in STOP envelope."""
    _make_two_path_merge_conflict(git_repo)
    code = run_cli(["preview", "--repo", str(git_repo), "--format", "json"])
    assert code == 78
    data = json.loads(capsys.readouterr().out)
    assert data["reason"] == "PREVIEW_PATH_REQUIRED_MULTIPLE_CONFLICTS"
    assert data["details"]["unmerged_paths"] == ["a.py", "b.py"]
    assert data["package_version"] == PACKAGE_VERSION


def test_r34_readonly_git_boundary_byte_identical() -> None:
    """R39/R40 must not alter the sealed read-only Git boundary."""
    data = (
        PACKAGE_ROOT / "runtime" / "opsx_conflict" / "preview_readonly_git.py"
    ).read_bytes()
    assert hashlib.sha256(data).hexdigest() == R34_PREVIEW_READONLY_GIT_SHA256


def test_go_capability_remains_false(git_repo: Path) -> None:
    """Successful PREVIEW keeps go_capability false."""
    _make_single_merge_conflict(git_repo)
    report = run_preview_advisory(git_repo)
    assert report["go_capability"] is False
    assert report["safe_usage_scope"] == "PREVIEW_ONLY"
