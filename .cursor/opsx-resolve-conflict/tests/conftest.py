"""Pytest fixtures: isolated git repos для conflict acceptance tests."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

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


def _git_hash_object(repo: Path, content: str) -> str:
    """Write blob and return oid."""

    result = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=repo,
        input=content,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return (result.stdout or "").strip()


def _register_unmerged_file(
    repo: Path,
    rel_path: str,
    base: str,
    ours: str,
    theirs: str,
    merge_label: str = "feature",
) -> None:
    """Register path in index as unmerged (stages 1/2/3) with conflict markers."""

    norm = rel_path.replace("\\", "/")
    _git(repo, "rm", "--cached", "-f", norm, check=False)
    base_oid = _git_hash_object(repo, base)
    ours_oid = _git_hash_object(repo, ours)
    theirs_oid = _git_hash_object(repo, theirs)
    index_info = (
        f"100644 {base_oid} 1\t{norm}\n"
        f"100644 {ours_oid} 2\t{norm}\n"
        f"100644 {theirs_oid} 3\t{norm}\n"
    )
    subprocess.run(
        ["git", "update-index", "--index-info"],
        cwd=repo,
        input=index_info,
        text=True,
        encoding="utf-8",
        check=True,
    )
    worktree = repo / norm
    worktree.parent.mkdir(parents=True, exist_ok=True)
    worktree.write_text(
        f"<<<<<<< HEAD\n{ours}=======\n{theirs}>>>>>>> {merge_label}\n",
        encoding="utf-8",
    )


def _current_branch(repo: Path) -> str:
    return _git(repo, "branch", "--show-current")


def init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
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

    return run_launcher_cwd(repo, mode, extra)


def run_launcher_cwd(
    cwd: Path,
    mode: str,
    extra: list[str] | None = None,
) -> tuple[int, dict]:
    """Invoke launcher from cwd without explicit --repo."""

    launcher = WORKSPACE_ROOT / ".cursor" / "opsx_resolve_conflict_launcher.py"
    cmd = [sys.executable, str(launcher), mode, "--json"]
    if extra:
        cmd.extend(extra)
    proc = subprocess.run(
        cmd,
        cwd=cwd,
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


@pytest.fixture
def normal_resolver_repo(empty_repo: Path) -> Path:
    """Repository with committed resolver launcher/runtime."""

    seed_resolver_runtime(empty_repo)
    return empty_repo


@pytest.fixture
def linked_worktree_pair(tmp_path: Path) -> tuple[Path, Path]:
    """S1: main repo + linked git worktree with resolver package."""

    main = tmp_path / "main-repo"
    repo = init_repo(main)
    seed_sources_yaml(repo)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    commit_all(repo, "init")
    seed_resolver_runtime(repo)
    linked = tmp_path / "linked-wt"
    _git(repo, "worktree", "add", "-b", "wt-feature", str(linked))
    return repo, linked


@pytest.fixture
def linked_worktree_merge_pair(tmp_path: Path) -> tuple[Path, Path]:
    """S2: active merge inside linked worktree."""

    main = tmp_path / "main-repo"
    repo = init_repo(main)
    seed_sources_yaml(repo)
    (repo / ".opsx" / "merge_note.txt").write_text("base\n", encoding="utf-8")
    commit_all(repo, "base")
    seed_resolver_runtime(repo)
    linked = tmp_path / "linked-wt"
    _git(repo, "worktree", "add", "-b", "wt-feature", str(linked))
    main_branch = _current_branch(repo)

    (linked / ".opsx" / "merge_note.txt").write_text("linked version\n", encoding="utf-8")
    commit_all(linked, "linked side")

    _git(repo, "checkout", main_branch)
    (repo / ".opsx" / "merge_note.txt").write_text("main version\n", encoding="utf-8")
    commit_all(repo, "main side")

    _merge_with_conflicts(linked, main_branch)
    return repo, linked


@pytest.fixture
def billing_mixed_lane_cluster_repo(empty_repo: Path) -> Path:
    """T1: product billing.py + test_billing.py in one semantic cluster."""

    repo = empty_repo
    main = _current_branch(repo)
    billing_dir = repo / "app" / "modules" / "billing"
    billing_dir.mkdir(parents=True)
    test_dir = repo / "tests" / "modules" / "billing"
    test_dir.mkdir(parents=True)
    (billing_dir / "billing.py").write_text("def charge(): return 1\n", encoding="utf-8")
    (test_dir / "test_billing.py").write_text(
        "def test_charge(): assert charge() == 1\n", encoding="utf-8"
    )
    commit_all(repo, "billing base")

    _git(repo, "checkout", "-b", "feature")
    (billing_dir / "billing.py").write_text("def charge(): return 2\n", encoding="utf-8")
    (test_dir / "test_billing.py").write_text(
        "def test_charge(): assert charge() == 2\n", encoding="utf-8"
    )
    commit_all(repo, "feature billing")

    _git(repo, "checkout", main)
    (billing_dir / "billing.py").write_text("def charge(): return 3\n", encoding="utf-8")
    (test_dir / "test_billing.py").write_text(
        "def test_charge(): assert charge() == 3\n", encoding="utf-8"
    )
    commit_all(repo, "main billing")

    _merge_with_conflicts(repo, "feature")
    return repo


@pytest.fixture
def process_authority_policy_repo(empty_repo: Path) -> Path:
    """U: 8+ process conflicts + product path for authority policy synthesis."""

    repo = empty_repo
    main = _current_branch(repo)
    cmd = repo / ".cursor" / "commands"
    cmd.mkdir(parents=True, exist_ok=True)
    names = [
        "opsx-alpha.md",
        "opsx-beta.md",
        "opsx-gamma.md",
        "opsx-delta.md",
        "opsx-epsilon.md",
        "opsx-zeta.md",
        "opsx-eta.md",
        "opsx-theta.md",
        "opsx-residual.md",
    ]
    for name in names:
        (cmd / name).write_text(
            f"# STATUS: DRAFT\n# OWNER: process\nbase {name}\n",
            encoding="utf-8",
        )
    app = repo / "app"
    app.mkdir(parents=True, exist_ok=True)
    (app / "module.py").write_text("def foo(): return 1\n", encoding="utf-8")
    commit_all(repo, "u base")

    _git(repo, "checkout", "-b", "feature")
    for name in names[:-1]:
        (cmd / name).write_text(
            f"# STATUS: DRAFT\n# OWNER: process\nbase {name}\n"
            f"# INCOMING_COMPAT: additive-{name}\n"
            f"# OBSOLETE_CONTRACT: old-{name}\n",
            encoding="utf-8",
        )
    (cmd / "opsx-residual.md").write_text(
        "# STATUS: DRAFT\n# OWNER: process\nbase opsx-residual.md\n"
        "# ARCHITECTURE_CHOICE: incoming-new-arch\n",
        encoding="utf-8",
    )
    (app / "module.py").write_text("def foo(): return 2\n", encoding="utf-8")
    commit_all(repo, "feature u")

    _git(repo, "checkout", main)
    for name in names[:-1]:
        (cmd / name).write_text(
            f"# STATUS: APPROVED\n# OWNER: process\n"
            f"# GATE: target-contract\nbase {name}\n"
            f"# TARGET_CONTRACT: v2-{name}\n",
            encoding="utf-8",
        )
    (cmd / "opsx-residual.md").write_text(
        "# STATUS: APPROVED\n# OWNER: process\n"
        "# GATE: target-contract\nbase opsx-residual.md\n"
        "# ARCHITECTURE_CHOICE: target-stable-arch\n",
        encoding="utf-8",
    )
    (app / "module.py").write_text("def foo(): return 3\n", encoding="utf-8")
    commit_all(repo, "main u")

    _merge_with_conflicts(repo, "feature")
    return repo


def build_process_lane_residual_repo(repo: Path) -> Path:
    """V fixture body — callable without pytest fixture wrapper."""

    main = _current_branch(repo)

    sources = repo / ".opsx" / "sources.yaml"
    sources_data = yaml.safe_load(sources.read_text(encoding="utf-8")) or {}
    allowlist = list(sources_data.get("allowlist") or [])
    for entry in (".cursor/pipeline/**", ".cursor/rules/**"):
        if entry not in allowlist:
            allowlist.append(entry)
    sources_data["allowlist"] = allowlist
    sources.write_text(
        yaml.dump(sources_data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    (repo / ".gitattributes").write_text(
        ".opsx/registry/*.ndjson merge=binary\n",
        encoding="utf-8",
    )

    hop = repo / ".cursor" / "pipeline" / "bug-team" / "runtime"
    hop.mkdir(parents=True)
    (hop / "live_task_hop.py").write_text(
        "# STATUS: APPROVED\n# OWNER: process\ndef hop(): return 1\n",
        encoding="utf-8",
    )
    rules = repo / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / "testing-rules.mdc").write_text(
        "# STATUS: APPROVED\n# GATE: rules\nrules base\n",
        encoding="utf-8",
    )
    adapter = repo / ".opsx" / "adapters" / "poetry-python"
    adapter.mkdir(parents=True)
    (adapter / "README.md").write_text(
        "# STATUS: APPROVED\n# OWNER: adapter\nadapter base\n",
        encoding="utf-8",
    )
    project = repo / ".opsx" / "project"
    project.mkdir(parents=True)
    (project / "manual_review.md").write_text(
        "# STATUS: APPROVED\n# GATE: review\nreview base\n",
        encoding="utf-8",
    )
    shared = repo / ".opsx" / "shared"
    shared.mkdir(parents=True)
    (shared / "bootstrap-profile.md").write_text(
        "# STATUS: APPROVED\n# OWNER: bootstrap\nprofile base\n",
        encoding="utf-8",
    )
    registry = repo / ".opsx" / "registry"
    registry.mkdir(parents=True)
    (registry / "command_activation.ndjson").write_text(
        '{"command":"opsx-alpha","STATUS":"APPROVED"}\n',
        encoding="utf-8",
    )
    (registry / "provenance.ndjson").write_text(
        '{"event":"boot","STATUS":"APPROVED"}\n',
        encoding="utf-8",
    )
    arch = repo / ".cursor" / "commands"
    arch.mkdir(parents=True)
    (arch / "opsx-arch-residual.md").write_text(
        "# STATUS: APPROVED\n# ARCHITECTURE_CHOICE: target-arch\narch base\n",
        encoding="utf-8",
    )
    (repo / "conftest.py").write_text("def pytest_plugin(): pass\n", encoding="utf-8")
    doto = repo / "DOTO"
    doto.mkdir(parents=True)
    (doto / "WORKLOG.md").write_text("worklog base\n", encoding="utf-8")
    app = repo / "app"
    app.mkdir(parents=True)
    (app / "product.py").write_text("def prod(): return 1\n", encoding="utf-8")
    del_path = repo / ".opsx" / "to_delete_process.txt"
    del_path.write_text("on main\n", encoding="utf-8")
    commit_all(repo, "v base")

    _git(repo, "checkout", "-b", "feature")
    (hop / "live_task_hop.py").write_text(
        "# STATUS: DRAFT\n# OWNER: process\n# INCOMING_COMPAT: hop-add\ndef hop(): return 2\n",
        encoding="utf-8",
    )
    (rules / "testing-rules.mdc").write_text(
        "# STATUS: DRAFT\n# GATE: rules\nrules incoming\n# INCOMING_COMPAT: rules-add\n",
        encoding="utf-8",
    )
    (adapter / "README.md").write_text(
        "# STATUS: DRAFT\n# OWNER: adapter\nadapter incoming\n# INCOMING_COMPAT: ad-add\n",
        encoding="utf-8",
    )
    (project / "manual_review.md").write_text(
        "# STATUS: DRAFT\n# GATE: review\nreview incoming\n",
        encoding="utf-8",
    )
    (shared / "bootstrap-profile.md").write_text(
        "# STATUS: DRAFT\n# OWNER: bootstrap\nprofile incoming\n",
        encoding="utf-8",
    )
    (registry / "command_activation.ndjson").write_text(
        '{"command":"opsx-alpha","STATUS":"APPROVED"}\n'
        '{"command":"opsx-beta","STATUS":"INCOMING"}\n',
        encoding="utf-8",
    )
    (registry / "provenance.ndjson").write_text(
        '{"event":"boot","STATUS":"APPROVED"}\n'
        '{"event":"merge","STATUS":"INCOMING"}\n',
        encoding="utf-8",
    )
    (arch / "opsx-arch-residual.md").write_text(
        "# STATUS: DRAFT\n# ARCHITECTURE_CHOICE: incoming-new-arch\narch incoming\n",
        encoding="utf-8",
    )
    (repo / "conftest.py").write_text("def pytest_plugin(): return 2\n", encoding="utf-8")
    (doto / "WORKLOG.md").write_text("worklog incoming\n", encoding="utf-8")
    (app / "product.py").write_text("def prod(): return 2\n", encoding="utf-8")
    del_path.write_text("on feature branch\n", encoding="utf-8")
    commit_all(repo, "feature v")

    _git(repo, "checkout", main)
    (hop / "live_task_hop.py").write_text(
        "# STATUS: APPROVED\n# OWNER: process\n# TARGET_CONTRACT: hop-v2\ndef hop(): return 3\n",
        encoding="utf-8",
    )
    (rules / "testing-rules.mdc").write_text(
        "# STATUS: APPROVED\n# GATE: rules\nrules target\n# TARGET_CONTRACT: rules-v2\n",
        encoding="utf-8",
    )
    (adapter / "README.md").write_text(
        "# STATUS: APPROVED\n# OWNER: adapter\nadapter target\n",
        encoding="utf-8",
    )
    (project / "manual_review.md").write_text(
        "# STATUS: APPROVED\n# GATE: review\nreview target\n",
        encoding="utf-8",
    )
    (shared / "bootstrap-profile.md").write_text(
        "# STATUS: APPROVED\n# OWNER: bootstrap\nprofile target\n",
        encoding="utf-8",
    )
    (registry / "command_activation.ndjson").write_text(
        '{"command":"opsx-alpha","STATUS":"APPROVED"}\n',
        encoding="utf-8",
    )
    (registry / "provenance.ndjson").write_text(
        '{"event":"boot","STATUS":"APPROVED"}\n',
        encoding="utf-8",
    )
    (arch / "opsx-arch-residual.md").write_text(
        "# STATUS: APPROVED\n# ARCHITECTURE_CHOICE: target-arch\narch target\n",
        encoding="utf-8",
    )
    (repo / "conftest.py").write_text("def pytest_plugin(): return 3\n", encoding="utf-8")
    (doto / "WORKLOG.md").write_text("worklog target\n", encoding="utf-8")
    (app / "product.py").write_text("def prod(): return 3\n", encoding="utf-8")
    del_path.unlink()
    commit_all(repo, "main v")

    _merge_with_conflicts(repo, "feature")
    return repo


@pytest.fixture
def process_lane_residual_repo(empty_repo: Path) -> Path:
    """V: process lane residuals — singleton clusters, registry, hard stops."""

    return build_process_lane_residual_repo(empty_repo)
