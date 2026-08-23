"""Pytest fixtures: isolated git repos для conflict acceptance tests."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))


def _git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )
    return (result.stdout or "").strip()


def _merge_with_conflicts(repo: Path, branch: str) -> None:
    """Merge expecting conflicts — exit 1 is success for conflict fixtures."""

    result = subprocess.run(
        ["git", "merge", branch, "--no-commit", "--no-ff"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )


def _current_branch(repo: Path) -> str:
    return _git(repo, "branch", "--show-current")


def init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@test.com")
    _git(repo, "config", "user.name", "test")
    return repo


def seed_sources_yaml(repo: Path) -> None:
    opsx = repo / ".opsx"
    opsx.mkdir(parents=True)
    (opsx / "sources.yaml").write_text(
        """
schema_version: 1
allowlist:
  - .cursor/commands/**
  - .opsx/**
hard_exclude:
  - app/**
  - "**/__pycache__/**"
""",
        encoding="utf-8",
    )


def commit_all(repo: Path, msg: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", msg)


def seed_trusted_boot(repo: Path) -> None:
    tools = repo / ".opsx" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    src = WORKSPACE_ROOT / ".opsx" / "tools" / "trusted_resolver_boot.py"
    shutil.copy2(src, tools / "trusted_resolver_boot.py")


def seed_launcher(repo: Path) -> None:
    dest = repo / ".cursor" / "opsx_resolve_conflict_launcher.py"
    src = WORKSPACE_ROOT / ".cursor" / "opsx_resolve_conflict_launcher.py"
    shutil.copy2(src, dest)


def seed_resolver_runtime(repo: Path, boot_override: str | None = None) -> str:
    """Materialize resolver package in repo and commit trusted HEAD snapshot."""

    src = WORKSPACE_ROOT / ".cursor" / "opsx-resolve-conflict"
    dest = repo / ".cursor" / "opsx-resolve-conflict"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )
    if boot_override is not None:
        boot = dest / "runtime" / "boot_opsx_conflict.py"
        boot.write_text(boot_override, encoding="utf-8")
    seed_trusted_boot(repo)
    seed_launcher(repo)
    commit_all(repo, "seed resolver runtime")
    return _git(repo, "rev-parse", "HEAD")


def seed_resolver_runtime_without_bootstrap(repo: Path) -> str:
    """Commit resolver runtime without trusted bootstrap at HEAD."""

    src = WORKSPACE_ROOT / ".cursor" / "opsx-resolve-conflict"
    dest = repo / ".cursor" / "opsx-resolve-conflict"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )
    seed_launcher(repo)
    commit_all(repo, "seed resolver runtime without bootstrap")
    return _git(repo, "rev-parse", "HEAD")


def run_trusted_cli(repo: Path, mode: str, extra: list[str] | None = None) -> tuple[int, dict]:
    """Invoke stdlib launcher (HEAD bootstrap materialization) and parse JSON report."""

    launcher = WORKSPACE_ROOT / ".cursor" / "opsx_resolve_conflict_launcher.py"
    cmd = [sys.executable, str(launcher), mode, "--repo", str(repo), "--json"]
    if extra:
        cmd.extend(extra)
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    report: dict = {}
    if proc.stdout.strip():
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError:
            report = {"STATUS": "FAILED", "STOP_REASON": proc.stdout}
    elif proc.stderr.strip():
        report = {"STATUS": "FAILED", "STOP_REASON": proc.stderr.strip()}
    return proc.returncode, report


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    repo = init_repo(tmp_path)
    seed_sources_yaml(repo)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    commit_all(repo, "init")
    return repo


@pytest.fixture
def mixed_scope_conflict_repo(empty_repo: Path) -> Path:
    """Process + product conflicts in one merge."""

    repo = empty_repo
    main = _current_branch(repo)
    _git(repo, "checkout", "-b", "feature")

    cmd_dir = repo / ".cursor" / "commands"
    cmd_dir.mkdir(parents=True, exist_ok=True)
    (cmd_dir / "test-cmd.md").write_text(
        "line1\nfeature change\n",
        encoding="utf-8",
    )
    app_dir = repo / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "module.py").write_text("def foo(): return 1\n", encoding="utf-8")
    commit_all(repo, "feature changes")

    _git(repo, "checkout", main)
    cmd_dir.mkdir(parents=True, exist_ok=True)
    (cmd_dir / "test-cmd.md").write_text(
        "line1\nmain change\n",
        encoding="utf-8",
    )
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "module.py").write_text("def foo(): return 2\n", encoding="utf-8")
    commit_all(repo, "main changes")

    _merge_with_conflicts(repo, "feature")
    return repo


@pytest.fixture
def multi_path_preview_repo(empty_repo: Path) -> Path:
    """Q: several unmerged paths across lanes and conflict kinds."""

    repo = empty_repo
    main = _current_branch(repo)
    app = repo / "app"
    app.mkdir(parents=True, exist_ok=True)
    (app / "service.py").write_text("def run(): return 1\n", encoding="utf-8")
    (repo / ".opsx" / "proc_a.txt").write_text("proc base\n", encoding="utf-8")
    (repo / ".opsx" / "proc_b.txt").write_text("proc base b\n", encoding="utf-8")
    commit_all(repo, "multi base")

    _git(repo, "checkout", "-b", "feature")
    (app / "service.py").write_text("def run(): return 2\n", encoding="utf-8")
    (repo / ".opsx" / "proc_a.txt").write_text("proc feature\n", encoding="utf-8")
    (repo / ".opsx" / "proc_b.txt").write_text("proc feature b\n", encoding="utf-8")
    commit_all(repo, "feature multi")

    _git(repo, "checkout", main)
    (app / "service.py").write_text("def run(): return 3\n", encoding="utf-8")
    (repo / ".opsx" / "proc_a.txt").write_text("proc main\n", encoding="utf-8")
    (repo / ".opsx" / "proc_b.txt").write_text("proc main b\n", encoding="utf-8")
    commit_all(repo, "main multi")

    _merge_with_conflicts(repo, "feature")
    return repo


@pytest.fixture
def self_conflict_boot_repo(empty_repo: Path) -> Path:
    """R: resolver boot conflicted in worktree; HEAD keeps trusted bytes."""

    repo = empty_repo
    seed_resolver_runtime(repo)
    main = _current_branch(repo)
    boot = repo / ".cursor" / "opsx-resolve-conflict" / "runtime" / "boot_opsx_conflict.py"
    trusted_boot = boot.read_text(encoding="utf-8")

    _git(repo, "checkout", "-b", "feature")
    boot.write_text(trusted_boot + "# feature boot marker\n", encoding="utf-8")
    commit_all(repo, "feature boot")

    _git(repo, "checkout", main)
    boot.write_text(trusted_boot + "# main boot marker\n", encoding="utf-8")
    commit_all(repo, "main boot")

    _merge_with_conflicts(repo, "feature")
    assert "<<<<<<<" in boot.read_text(encoding="utf-8")
    return repo


@pytest.fixture
def combined_qr_repo(empty_repo: Path) -> Path:
    """Q+R: multi-path merge plus resolver package self-conflict."""

    repo = empty_repo
    seed_resolver_runtime(repo)
    main = _current_branch(repo)
    boot = repo / ".cursor" / "opsx-resolve-conflict" / "runtime" / "boot_opsx_conflict.py"
    trusted_boot = boot.read_text(encoding="utf-8")
    app = repo / "app"
    app.mkdir(parents=True, exist_ok=True)
    (app / "module.py").write_text("value = 1\n", encoding="utf-8")
    (repo / ".opsx" / "note.txt").write_text("note base\n", encoding="utf-8")
    commit_all(repo, "combined base")

    _git(repo, "checkout", "-b", "feature")
    boot.write_text(trusted_boot + "# feature boot\n", encoding="utf-8")
    (app / "module.py").write_text("value = 2\n", encoding="utf-8")
    (repo / ".opsx" / "note.txt").write_text("note feature\n", encoding="utf-8")
    commit_all(repo, "feature combined")

    _git(repo, "checkout", main)
    boot.write_text(trusted_boot + "# main boot\n", encoding="utf-8")
    (app / "module.py").write_text("value = 3\n", encoding="utf-8")
    (repo / ".opsx" / "note.txt").write_text("note main\n", encoding="utf-8")
    commit_all(repo, "main combined")

    _merge_with_conflicts(repo, "feature")
    assert "<<<<<<<" in boot.read_text(encoding="utf-8")
    return repo


@pytest.fixture
def auto_safe_repo(empty_repo: Path) -> Path:
    repo = empty_repo
    main = _current_branch(repo)
    _git(repo, "checkout", "-b", "a")
    p = repo / ".opsx" / "note.txt"
    p.write_text("shared\na-only\n", encoding="utf-8")
    commit_all(repo, "a")
    _git(repo, "checkout", main)
    p.write_text("shared\nb-only\n", encoding="utf-8")
    commit_all(repo, "b")
    _merge_with_conflicts(repo, "a")
    p.write_text(
        "shared\n<<<<<<< HEAD\nb-only\n=======\na-only\n>>>>>>> a\n",
        encoding="utf-8",
    )
    return repo


@pytest.fixture
def delete_modify_repo(empty_repo: Path) -> Path:
    repo = empty_repo
    main = _current_branch(repo)
    p = repo / ".opsx" / "to_delete.txt"
    p.write_text("on main\n", encoding="utf-8")
    commit_all(repo, "main has file")
    _git(repo, "checkout", "-b", "del")
    p.write_text("on del branch\n", encoding="utf-8")
    commit_all(repo, "del modifies")
    _git(repo, "checkout", main)
    p.unlink()
    commit_all(repo, "main deletes")
    _merge_with_conflicts(repo, "del")
    return repo


@pytest.fixture
def logical_conflict_repo(empty_repo: Path) -> Path:
    """F: producer lost old_api (UU), consumer auto-merged still calls old_api."""

    repo = empty_repo
    main = _current_branch(repo)
    app = repo / "app"
    app.mkdir(parents=True, exist_ok=True)
    (app / "producer.py").write_text("def old_api(): return 1\n", encoding="utf-8")
    (app / "consumer.py").write_text("def run(): return old_api()\n", encoding="utf-8")
    commit_all(repo, "base api")

    _git(repo, "checkout", "-b", "feature")
    (app / "producer.py").write_text("def new_api(): return 2\n", encoding="utf-8")
    commit_all(repo, "feature new api variant")

    _git(repo, "checkout", main)
    (app / "producer.py").write_text("def new_api(): return 3\n", encoding="utf-8")
    # consumer unchanged — still calls old_api
    commit_all(repo, "main removed old_api")
    _merge_with_conflicts(repo, "feature")
    return repo


@pytest.fixture
def dual_write_repo(empty_repo: Path) -> Path:
    """G: two process files for mid-write fault injection."""

    repo = empty_repo
    main = _current_branch(repo)
    _git(repo, "checkout", "-b", "branch")
    (repo / ".opsx" / "file_a.txt").write_text("a-side\n", encoding="utf-8")
    (repo / ".opsx" / "file_b.txt").write_text("b-side\n", encoding="utf-8")
    commit_all(repo, "branch")
    _git(repo, "checkout", main)
    (repo / ".opsx" / "file_a.txt").write_text("a-main\n", encoding="utf-8")
    (repo / ".opsx" / "file_b.txt").write_text("b-main\n", encoding="utf-8")
    commit_all(repo, "main")
    _merge_with_conflicts(repo, "branch")
    return repo


@pytest.fixture
def conflict_plus_auto_merge_repo(empty_repo: Path) -> Path:
    """O: one conflicted process path + one clean auto-merged product path."""

    repo = empty_repo
    main = _current_branch(repo)
    app = repo / "app"
    app.mkdir(parents=True, exist_ok=True)
    (app / "auto_merged.py").write_text(
        "line1\nline2\nline3\n",
        encoding="utf-8",
    )
    (repo / ".opsx" / "conflict.txt").write_text("base conflict\n", encoding="utf-8")
    commit_all(repo, "base")

    _git(repo, "checkout", "-b", "feature")
    (app / "auto_merged.py").write_text(
        "line1\nline2\nline3\nline4 feature\n",
        encoding="utf-8",
    )
    (repo / ".opsx" / "conflict.txt").write_text("feature conflict\n", encoding="utf-8")
    commit_all(repo, "feature")

    _git(repo, "checkout", main)
    (app / "auto_merged.py").write_text(
        "line1\nline2 main\nline3\n",
        encoding="utf-8",
    )
    (repo / ".opsx" / "conflict.txt").write_text("main conflict\n", encoding="utf-8")
    commit_all(repo, "main changes")

    _merge_with_conflicts(repo, "feature")
    return repo


@pytest.fixture
def r3_full_self_conflict_repo(empty_repo: Path) -> Path:
    """R3: conflicted bootstrap + runtime + product path."""

    repo = empty_repo
    seed_resolver_runtime(repo)
    main = _current_branch(repo)
    boot = repo / ".cursor" / "opsx-resolve-conflict" / "runtime" / "boot_opsx_conflict.py"
    trusted_boot = repo / ".opsx" / "tools" / "trusted_resolver_boot.py"
    pipeline = (
        repo / ".cursor" / "opsx-resolve-conflict" / "runtime" / "opsx_conflict" / "pipeline.py"
    )
    trusted_boot_text = trusted_boot.read_text(encoding="utf-8")
    boot_text = boot.read_text(encoding="utf-8")
    pipeline_text = pipeline.read_text(encoding="utf-8")
    app = repo / "app"
    app.mkdir(parents=True, exist_ok=True)
    (app / "example.py").write_text("value = 1\n", encoding="utf-8")
    commit_all(repo, "r3 base files")

    _git(repo, "checkout", "-b", "feature")
    trusted_boot.write_text(trusted_boot_text + "# feature trusted boot\n", encoding="utf-8")
    boot.write_text(boot_text + "# feature boot\n", encoding="utf-8")
    pipeline.write_text(pipeline_text + "# feature pipeline\n", encoding="utf-8")
    (app / "example.py").write_text("value = 2\n", encoding="utf-8")
    commit_all(repo, "feature r3")

    _git(repo, "checkout", main)
    trusted_boot.write_text(trusted_boot_text + "# main trusted boot\n", encoding="utf-8")
    boot.write_text(boot_text + "# main boot\n", encoding="utf-8")
    pipeline.write_text(pipeline_text + "# main pipeline\n", encoding="utf-8")
    (app / "example.py").write_text("value = 3\n", encoding="utf-8")
    commit_all(repo, "main r3")

    _merge_with_conflicts(repo, "feature")
    assert "<<<<<<<" in trusted_boot.read_text(encoding="utf-8")
    assert "<<<<<<<" in boot.read_text(encoding="utf-8")
    return repo


@pytest.fixture
def missing_bootstrap_repo(empty_repo: Path) -> Path:
    """Negative: HEAD lacks trusted bootstrap package."""

    repo = empty_repo
    seed_resolver_runtime_without_bootstrap(repo)
    return repo
