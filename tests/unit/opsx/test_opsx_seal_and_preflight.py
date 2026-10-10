"""Unit: sealed provider block carries non-consuming preflight; preflight hygiene (без Docker)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.unit

_TOOLS = Path(__file__).resolve().parents[3] / ".opsx" / "tools"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"{name}__seal_test", _TOOLS / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


guard = _load("opsx_provider_run_guard")
_prior_guard = sys.modules.get("opsx_provider_run_guard")
seal = _load("opsx_seal_provider_packet")
if _prior_guard is not None:
    # seal tool re-registers the guard module; keep the sibling test's class identity.
    sys.modules["opsx_provider_run_guard"] = _prior_guard
else:
    _ = sys.modules.pop("opsx_provider_run_guard", None)
preflight = _load("opsx_provider_preflight")


def _git(repo: Path, *args: str) -> None:
    _ = subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def test_sealed_block_runs_preflight_before_guard_run(repo: Path) -> None:
    packet = seal.build_packet(
        repo, change_id="c", live_token="tok", packet_id="PROVIDER-PACKET-v8"
    )
    block = str(packet["allowed_run_block_text"])
    lines = block.splitlines()
    preflight_idx = next(i for i, ln in enumerate(lines) if "opsx_provider_preflight" in ln)
    run_idx = next(i for i, ln in enumerate(lines) if "run_guard.py run" in ln)
    assert preflight_idx < run_idx
    assert "--require-docker-daemon" in lines[preflight_idx]
    assert "--fix-integrity" in lines[preflight_idx]
    assert not guard.block_has_unguarded_pytest_invocation(block)
    assert packet["packet_evidence_id"] == "PROVIDER-PACKET-v8"
    _ = guard.ProviderRunPacket.from_mapping(packet)


def test_hygiene_ok_on_clean_tree(repo: Path) -> None:
    assert preflight.check_worktree_hygiene(repo)["status"] == "OK"


def test_hygiene_flags_assume_unchanged_and_stray_tests_dir(repo: Path) -> None:
    _git(repo, "update-index", "--assume-unchanged", "a.txt")
    (repo / "tests" / "tests").mkdir(parents=True)
    result = preflight.check_worktree_hygiene(repo)
    assert result["status"] == "FAIL"
    assert any("hidden_index_flag" in p for p in result["problems"])
    assert "stray_tests_tests_dir" in result["problems"]


def test_hygiene_flags_dirty_tree(repo: Path) -> None:
    (repo / "a.txt").write_text("changed", encoding="utf-8")
    assert "dirty_worktree" in preflight.check_worktree_hygiene(repo)["problems"]
