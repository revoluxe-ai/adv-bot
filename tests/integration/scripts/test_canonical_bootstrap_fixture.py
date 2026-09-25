"""Apply-stage Git fixture tests for canonical scripts invocation.

Фикстура намеренно создаёт отдельный repository и worktrees: реальный
canonical `scripts` runtime до merge не считается обновлённым.
"""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.integration


def _git(root: Path, *args: str) -> str:
    """Выполнить Git fixture command без shell и вернуть stdout."""
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _request(path: Path, mode: str = "PLAN_RUN") -> None:
    """Записать valid request для canonical resolver fixture."""
    payload: dict[str, Any] = {
        "schema_version": "scripts-resolver-request.v1",
        "mode": mode,
        "request_id": "req-fixture",
        "run_id": "run-fixture",
        "change_name_hint": "fixture-run",
        "capabilities": ["strict-read-only-contract"],
        "sources": ["POSTGRES", "WB_API"],
        "required_fields": ["campaign_state"],
        "output_schema_version": "a1-strict-read-only-v1",
        "primary_artifact_pattern": "A1-STRICT-READ-ONLY-CONTRACT.zip",
        "required_args": {
            "shop_id": "fixture-shop",
            "wb_cabinet_id": 401,
            "target_nmids": "1",
            "output_dir": str(path.parent / "outputs"),
        },
        "optional_args": {},
        "zero_write_required": True,
        "explicit_script": None,
        "owning_change_id": None,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Создать repository с feature и exact scripts worktrees."""
    source = Path(__file__).resolve().parents[3]
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "fixture@example.test")
    _git(repo, "config", "user.name", "Fixture")
    (repo / "scripts").mkdir()
    (repo / "tools/scripts").mkdir(parents=True)
    for relative in (
        "scripts/REGISTRY.yaml",
        "scripts/REGISTRY.md",
        "tools/scripts/__init__.py",
        "tools/scripts/registry.py",
        "tools/scripts/resolver.py",
        "tools/scripts/bootstrap.py",
    ):
        target = repo / relative
        target.write_text((source / relative).read_text(encoding="utf-8"), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture")
    _git(repo, "branch", "scripts")
    caller = tmp_path / "caller"
    canonical = tmp_path / "canonical"
    _git(repo, "worktree", "add", "-b", "feature", str(caller), "HEAD")
    _git(repo, "worktree", "add", str(canonical), "scripts")
    return repo, caller, canonical


def _run_resolver(caller: Path, canonical: Path, request: Path) -> subprocess.CompletedProcess[str]:
    """Запустить именно абсолютный canonical resolver path."""
    return subprocess.run(
        [
            sys.executable,
            str(canonical / "tools/scripts/resolver.py"),
            "PLAN_RUN",
            "--request-file",
            str(request.resolve()),
            "--caller-root",
            str(caller.resolve()),
            "--canonical-root",
            str(canonical.resolve()),
        ],
        cwd=canonical,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_bootstrap(
    caller: Path, canonical: Path, request: Path, mode: str = "PLAN_RUN"
) -> subprocess.CompletedProcess[str]:
    """Запустить thin bootstrap из canonical worktree с caller provenance."""
    return subprocess.run(
        [
            sys.executable,
            str(canonical / "tools/scripts/bootstrap.py"),
            mode,
            "--request-file",
            str(request.resolve()),
            "--caller-root",
            str(caller.resolve()),
            "--canonical-root",
            str(canonical.resolve()),
        ],
        cwd=canonical,
        capture_output=True,
        text=True,
        check=False,
    )


def test_canonical_resolver_runs_when_caller_lacks_resolver(tmp_path: Path) -> None:
    """Bootstrap contract uses canonical executable and leaves caller unmodified."""
    _, caller, canonical = _fixture_repo(tmp_path)
    request = tmp_path / "request.json"
    _request(request)
    caller_resolver = caller / "tools/scripts/resolver.py"
    caller_registry = caller / "scripts/REGISTRY.yaml"
    caller_resolver.unlink()
    caller_registry.unlink()
    _git(caller, "add", "-u")
    _git(caller, "commit", "-m", "caller lacks canonical implementation")
    before_head = _git(caller, "rev-parse", "HEAD")
    before_tracked = _git(caller, "ls-files", "-s")
    completed = _run_bootstrap(caller, canonical, request)
    after_head = _git(caller, "rev-parse", "HEAD")
    after_tracked = _git(caller, "ls-files", "-s")
    assert completed.returncode == 0
    result = json.loads(completed.stdout)
    assert result["outcome"] == "REUSE"
    assert result["caller"]["branch"] == "refs/heads/feature"
    assert result["canonical_worktree"]["branch"] == "refs/heads/scripts"
    assert result["registry_sha"] == _git(
        canonical,
        "log",
        "-1",
        "--format=%H",
        "HEAD",
        "--",
        "scripts/REGISTRY.yaml",
    )
    assert after_head == before_head
    assert after_tracked == before_tracked
    assert not caller_resolver.exists()
    assert not caller_registry.exists()


def test_registry_sha_is_git_commit_not_registry_content_digest(tmp_path: Path) -> None:
    """Resolver provenance names the Registry commit, never its content digest."""
    _, caller, canonical = _fixture_repo(tmp_path)
    request = tmp_path / "request.json"
    _request(request)

    completed = _run_resolver(caller, canonical, request)

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    expected_commit = _git(
        canonical,
        "log",
        "-1",
        "--format=%H",
        "HEAD",
        "--",
        "scripts/REGISTRY.yaml",
    )
    content_digest = hashlib.sha256(
        (canonical / "scripts/REGISTRY.yaml").read_bytes()
    ).hexdigest()
    assert payload["registry_sha"] == expected_commit
    assert payload["registry_sha"] != content_digest
    assert len(payload["registry_sha"]) == 40


@pytest.mark.parametrize("mode", ["PLAN_RUN", "RUN"])
def test_command_surface_routes_both_modes_through_bootstrap(
    tmp_path: Path, mode: str
) -> None:
    """Both user modes use the documented canonical bootstrap routing."""
    command_surface = (
        Path(__file__).resolve().parents[3] / ".cursor/commands/opsx-scripts.md"
    ).read_text(encoding="utf-8")
    assert "PLAN_RUN|RUN" in command_surface
    assert "tools/scripts/bootstrap.py" in command_surface
    assert "tools/scripts/resolver.py" in command_surface

    _, caller, canonical = _fixture_repo(tmp_path)
    request = tmp_path / f"{mode.lower()}-request.json"
    _request(request, mode)
    completed = _run_bootstrap(caller, canonical, request, mode)

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["mode"] == mode
    assert payload["canonical_worktree"]["branch"] == "refs/heads/scripts"


def test_thin_bootstrap_launches_only_canonical_resolver(tmp_path: Path) -> None:
    """Bootstrap starts canonical executable even when caller copy is absent."""
    _, caller, canonical = _fixture_repo(tmp_path)
    request = tmp_path / "request.json"
    _request(request)
    (caller / "tools/scripts/resolver.py").unlink()
    before = _git(caller, "status", "--porcelain=v1")
    completed = _run_bootstrap(caller, canonical, request)
    assert completed.returncode == 0
    result = json.loads(completed.stdout)
    assert result["outcome"] == "REUSE"
    assert result["caller"]["root"] == str(caller.resolve())
    assert result["canonical_worktree"]["root"] == str(canonical.resolve())
    assert _git(caller, "status", "--porcelain=v1") == before


def test_stale_caller_resolver_is_not_used(tmp_path: Path) -> None:
    """Absolute canonical invocation cannot execute a stale caller resolver."""
    _, caller, canonical = _fixture_repo(tmp_path)
    request = tmp_path / "request.json"
    _request(request)
    stale = caller / "tools/scripts/resolver.py"
    stale.write_text(
        "raise SystemExit('STALE_CALLER_RESOLVER')\n",
        encoding="utf-8",
    )
    _git(caller, "add", "tools/scripts/resolver.py")
    _git(caller, "commit", "-m", "stale caller copy")
    completed = _run_bootstrap(caller, canonical, request)
    assert completed.returncode == 0
    assert "STALE_CALLER_RESOLVER" not in completed.stdout
    assert "STALE_CALLER_RESOLVER" not in completed.stderr


def test_formal_change_and_explicit_cabinet_outcomes_are_machine_gated(
    tmp_path: Path,
) -> None:
    """Resolver emits formal handoff or explicit REUSE without CREATED."""
    _, caller, canonical = _fixture_repo(tmp_path)
    request = tmp_path / "request.json"
    _request(request)
    formal = json.loads(request.read_text(encoding="utf-8"))
    formal["capabilities"] = ["missing-capability"]
    formal["required_fields"] = ["missing-field"]
    formal["output_schema_version"] = "missing-v1"
    request.write_text(json.dumps(formal), encoding="utf-8")
    formal_result = _run_resolver(caller, canonical, request)
    assert formal_result.returncode == 10
    formal_payload = json.loads(formal_result.stdout)
    assert formal_payload["outcome"] == "FORMAL_CHANGE_REQUIRED"
    assert formal_payload["formal_change"]["command"] == "/opsx-ff fixture-run"

    explicit = json.loads(request.read_text(encoding="utf-8"))
    explicit["explicit_script"] = "a1-cabinet401-run-go-contract"
    explicit["output_schema_version"] = "a1-cabinet401-v1"
    explicit["primary_artifact_pattern"] = "A1-CABINET401-RUN-GO-CONTRACT.zip"
    explicit["required_args"] = {"output_dir": str(tmp_path / "outputs")}
    explicit["required_fields"] = ["campaign_state"]
    explicit["capabilities"] = []
    explicit["sources"] = []
    request.write_text(json.dumps(explicit), encoding="utf-8")
    explicit_result = _run_resolver(caller, canonical, request)
    assert explicit_result.returncode == 0
    explicit_payload = json.loads(explicit_result.stdout)
    assert explicit_payload["outcome"] == "REUSE"
    assert explicit_payload["selection_mode"] == "EXPLICIT"


def test_formal_handoff_stops_before_apply_or_job_creation(tmp_path: Path) -> None:
    """Formal resolution is evidence only and cannot launch operational apply."""
    _, caller, canonical = _fixture_repo(tmp_path)
    request = tmp_path / "request.json"
    _request(request)
    formal = json.loads(request.read_text(encoding="utf-8"))
    formal["capabilities"] = ["missing-capability"]
    formal["required_fields"] = ["missing-field"]
    formal["output_schema_version"] = "missing-v1"
    request.write_text(json.dumps(formal), encoding="utf-8")
    before = _git(caller, "ls-files", "-s")

    completed = _run_bootstrap(caller, canonical, request)

    assert completed.returncode == 10
    payload = json.loads(completed.stdout)
    handoff = payload["formal_change"]
    assert payload["operational_write_path"] is False
    assert "/opsx-apply" not in handoff["pasteable_prompt"]
    assert "apply=PROHIBITED" in handoff["pasteable_prompt"]
    assert _git(caller, "ls-files", "-s") == before
    assert not (caller / ".tmp" / "opsx-scripts").exists()


def test_tracked_dirty_canonical_is_blocked(tmp_path: Path) -> None:
    """Tracked canonical changes fail closed before Registry resolution."""
    _, caller, canonical = _fixture_repo(tmp_path)
    request = tmp_path / "request.json"
    _request(request)
    registry_path = canonical / "scripts/REGISTRY.yaml"
    registry_path.write_text(registry_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    completed = _run_bootstrap(caller, canonical, request)
    assert completed.returncode == 20
    assert json.loads(completed.stdout)["outcome"] == "BLOCKED"


def test_wrong_branch_and_different_common_directory_are_blocked(tmp_path: Path) -> None:
    """Canonical candidate must be exact scripts branch in caller common dir."""
    _, caller, canonical = _fixture_repo(tmp_path / "same")
    request = tmp_path / "same-request.json"
    _request(request)
    wrong_branch = _run_bootstrap(caller, caller, request)
    assert wrong_branch.returncode == 20
    assert json.loads(wrong_branch.stdout)["outcome"] == "BLOCKED"

    _, _, foreign_canonical = _fixture_repo(tmp_path / "foreign")
    different = _run_bootstrap(
        caller, tmp_path / "foreign" / "canonical", request
    )
    assert different.returncode == 20
    assert json.loads(different.stdout)["outcome"] == "BLOCKED"
