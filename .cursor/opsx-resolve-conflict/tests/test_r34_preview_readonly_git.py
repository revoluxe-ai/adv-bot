"""R34 PREVIEW read-only Git boundary — exact operation grammar + sealed env."""

from __future__ import annotations

import hashlib
import inspect
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from opsx_conflict.errors import StopRequired
from opsx_conflict.preview_advisory import run_preview_advisory
from opsx_conflict.preview_readonly_git import (
    SEALED_ENV_POLICY_VERSION,
    PreviewReadonlyGit,
    compile_operation_argv,
    normalize_blob_oid,
)

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows PREVIEW_ONLY")


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
    proc = subprocess.run(
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
    proc = subprocess.run(
        ["git", "rebase", "main"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def _digest_path(path: Path) -> dict[str, str | None]:
    """Capture worktree/index/refs fingerprints for mutation checks."""
    git_dir = Path(
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(path),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    if not git_dir.is_absolute():
        git_dir = path / git_dir
    index = git_dir / "index"
    return {
        "index": hashlib.sha256(index.read_bytes()).hexdigest() if index.is_file() else None,
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(path),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip(),
        "show_ref": subprocess.run(
            ["git", "show-ref"],
            cwd=str(path),
            capture_output=True,
            text=True,
            check=False,
        ).stdout,
    }


OPERATION_ARGV_MATRIX = {
    "resolve_git_dir": ["rev-parse", "--git-dir"],
    "resolve_head": ["rev-parse", "HEAD"],
    "read_refs": ["show-ref"],
    "read_unmerged_index": ["ls-files", "--unmerged", "-z"],
}


def test_exact_operation_to_argv_matrix() -> None:
    """Closed operations compile to exact argv only."""
    for op_id, argv in OPERATION_ARGV_MATRIX.items():
        assert compile_operation_argv(op_id) == argv
    oid = "a" * 40
    assert compile_operation_argv("read_stage_blob", blob_oid=oid) == [
        "cat-file",
        "blob",
        oid,
    ]
    oid_upper = "B" * 40
    assert compile_operation_argv("read_stage_blob", blob_oid=oid_upper) == [
        "cat-file",
        "blob",
        "b" * 40,
    ]


def test_arbitrary_argv_api_absence() -> None:
    """No public method accepts caller-controlled git_args."""
    sigs = {
        name: inspect.signature(method)
        for name, method in inspect.getmembers(
            PreviewReadonlyGit, predicate=inspect.isfunction
        )
        if not name.startswith("_")
    }
    for name, sig in sigs.items():
        params = list(sig.parameters)
        assert "git_args" not in params, name
        assert "args" not in params or name in {"ledger_as_dicts"}, name
    assert "run" not in sigs


@pytest.mark.parametrize(
    "op_id",
    [
        "config",
        "symbolic-ref",
        "diff",
        "show",
        "merge-base",
        "status",
        "add",
        "commit",
        "checkout",
        "reset",
        "update-index",
        "continue",
        "abort",
        "push",
    ],
)
def test_removed_and_mutating_verbs_rejected(op_id: str) -> None:
    """Unknown/mutating verbs cannot be compiled."""
    with pytest.raises(StopRequired) as exc:
        compile_operation_argv(op_id)
    assert exc.value.reason == "PREVIEW_UNKNOWN_OPERATION"


def test_unknown_operation_typed_stop() -> None:
    with pytest.raises(StopRequired) as exc:
        compile_operation_argv("not_a_real_op")
    assert exc.value.reason == "PREVIEW_UNKNOWN_OPERATION"


@pytest.mark.parametrize(
    "oid",
    [
        "abc",
        "HEAD",
        "main:conflict.py",
        "abcdef^",
        "deadbeef~1",
        "a" * 39,
        "g" * 40,
        "a" * 41,
        "--batch",
        "",
    ],
)
def test_invalid_and_revision_oid_rejected(oid: str) -> None:
    with pytest.raises(StopRequired) as exc:
        normalize_blob_oid(oid)
    assert exc.value.reason == "PREVIEW_INVALID_BLOB_OID"


def test_config_and_symbolic_ref_cannot_execute(git_repo: Path) -> None:
    """Config / symbolic-ref write forms cannot be represented or spawned."""
    git = PreviewReadonlyGit(git_repo)
    for bad in ("config", "symbolic-ref"):
        with pytest.raises(StopRequired):
            compile_operation_argv(bad)
    assert not hasattr(git, "run")


def test_env_redirect_injection_blocked(
    git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ambient GIT_DIR / WORK_TREE / INDEX_FILE cannot redirect preview."""
    other = tmp_path / "other_repo"
    other.mkdir()
    _run(["git", "init", "-b", "main"], other)
    _run(["git", "config", "user.email", "o@example.invalid"], other)
    _run(["git", "config", "user.name", "Other"], other)
    (other / "only_other.txt").write_text("secret\n", encoding="utf-8")
    _run(["git", "add", "only_other.txt"], other)
    _run(["git", "commit", "-m", "other"], other)
    other_git = (
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(other),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    other_git_abs = str((other / other_git).resolve())

    _make_merge_conflict(git_repo)
    before = _digest_path(git_repo)

    # Inject ambient redirects only for the preview runner (not fixture setup).
    monkeypatch.setenv("GIT_DIR", other_git_abs)
    monkeypatch.setenv("GIT_WORK_TREE", str(other.resolve()))
    monkeypatch.setenv("GIT_INDEX_FILE", str(Path(other_git_abs) / "index"))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "user.name")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "MutatedAmbient")
    monkeypatch.setenv("GIT_EXTERNAL_DIFF", "evil.exe")
    monkeypatch.setenv("GIT_PAGER", "evil-pager")

    git = PreviewReadonlyGit(git_repo)
    head = git.resolve_head()
    git_dir = git.resolve_git_dir()
    # Must resolve against requested repo, not ambient GIT_DIR other repo.
    assert "only_other" not in (git.read_refs() or "")
    gd = Path(git_dir)
    if not gd.is_absolute():
        gd = git_repo / gd
    assert str(gd.resolve()).lower().startswith(str(git_repo.resolve()).lower())
    assert head == before["head"]
    sealed = git._sealed_env()
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_EXTERNAL_DIFF",
    ):
        assert key not in sealed
    # Clear ambient redirects before host-git fingerprint (fixture helper inherits env).
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_VALUE_0",
        "GIT_EXTERNAL_DIFF",
        "GIT_PAGER",
    ):
        monkeypatch.delenv(key, raising=False)
    after = _digest_path(git_repo)
    assert before == after
    assert all(
        e.sealed_environment_policy_version == SEALED_ENV_POLICY_VERSION
        for e in git.ledger
    )


def test_malicious_path_git_not_selected(
    git_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fake git earlier on PATH is not used when trust digest pins the real binary."""
    fake_dir = tmp_path / "evil_bin"
    fake_dir.mkdir()
    fake_git = fake_dir / "git.exe"
    fake_git.write_bytes(b"MZ-not-a-real-git-binary-for-path-injection\n")
    monkeypatch.setenv("PATH", str(fake_dir) + os.pathsep + os.environ.get("PATH", ""))
    # Digest still pinned to real host git from conftest — resolve must STOP
    # or bind the digest-matched binary, never execute the fake without match.
    with pytest.raises(StopRequired) as exc:
        PreviewReadonlyGit(git_repo)
    assert exc.value.reason in {
        "GIT_TRUST_DIGEST_MISMATCH",
        "GIT_EXECUTABLE_NOT_FILE",
        "GIT_TRUST_BIND_FAILED",
        "PREVIEW_GIT_EXECUTABLE_DIGEST_MISMATCH",
    }


def test_executable_digest_mismatch_stops(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-exec digest mismatch → typed STOP (no atomicity claim)."""
    git = PreviewReadonlyGit(git_repo)
    object.__setattr__(git, "_expected_digest", "0" * 64)
    with pytest.raises(StopRequired) as exc:
        git.resolve_head()
    assert exc.value.reason == "PREVIEW_GIT_EXECUTABLE_DIGEST_MISMATCH"
    assert "R25-MEDIUM-002" in str(exc.value.details)


def test_merge_preview_regression(git_repo: Path) -> None:
    _make_merge_conflict(git_repo)
    before = _digest_path(git_repo)
    report = run_preview_advisory(git_repo)
    after = _digest_path(git_repo)
    assert before == after
    assert report["status"] == "PREVIEW_READY"
    assert report["go_capability"] is False
    ledger = report["command_ledger"]
    assert ledger
    assert all(e.get("atomicity_claim") is False for e in ledger)
    assert all(e.get("r25_medium_002_open") is True for e in ledger)
    ops = {e["operation_id"] for e in ledger}
    assert "resolve_git_dir" in ops
    assert "read_unmerged_index" in ops
    assert "read_stage_blob" in ops
    forbidden = {
        "config",
        "symbolic-ref",
        "diff",
        "show",
        "status",
        "add",
        "commit",
    }
    for entry in ledger:
        assert entry["operation_id"] not in forbidden
        for token in forbidden:
            assert token not in entry["argv"]


def test_rebase_preview_regression(git_repo: Path) -> None:
    _make_rebase_conflict(git_repo)
    before = _digest_path(git_repo)
    report = run_preview_advisory(git_repo)
    after = _digest_path(git_repo)
    assert before == after
    assert report["CURRENT_CONFLICT"]["operation"] == "rebase"
    assert report["go_capability"] is False


def test_fault_injection_no_arbitrary_argv_reaches_subprocess(
    git_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Monkeypatched spawn must only ever see exact compiled argv."""
    _run(["git", "config", "user.email", "preview@example.invalid"], git_repo)
    _run(["git", "config", "user.name", "Preview Fixture"], git_repo)
    (git_repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _run(["git", "add", "seed.txt"], git_repo)
    _run(["git", "commit", "-m", "seed"], git_repo)

    seen: list[list[str]] = []
    real_run = subprocess.run

    def spy(*args, **kwargs):  # type: ignore[no-untyped-def]
        cmd = list(args[0]) if args else list(kwargs.get("args", []))
        # Only record preview-bound spawns (cwd == repo), not trust probes.
        cwd = kwargs.get("cwd")
        if cwd is not None and Path(str(cwd)).resolve() == git_repo.resolve():
            seen.append(cmd[1:])  # drop executable
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", spy)
    git = PreviewReadonlyGit(git_repo)
    git.resolve_git_dir()
    git.resolve_head()
    git.read_refs()
    git.read_unmerged_index()
    assert seen
    for argv in seen:
        assert argv in (
            ["rev-parse", "--git-dir"],
            ["rev-parse", "HEAD"],
            ["show-ref"],
            ["ls-files", "--unmerged", "-z"],
        )
        assert "config" not in argv
        assert "symbolic-ref" not in argv
