"""GO path: R11 proof, trust, staged binding, and terminal atomicity."""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest
from conftest import run
from opsx_conflict.runtime import (
    ScopeItem,
    ScopeManifest,
    SealedOrchestrator,
    detect_operation_state,
    sha256_text,
)
import opsx_conflict.orchestrator as orchestrator_module
import opsx_conflict.runtime as runtime_module
import opsx_conflict.validation as validation_module
import opsx_conflict.write_atomic as write_atomic_module
from opsx_conflict.ledger import ExecutionLedger
from opsx_conflict.git_typed import TypedGit
from opsx_conflict.hashutil import sha256_canonical
from opsx_conflict.attestation import resolve_state_root
from opsx_conflict.cancellation import supervisor
from opsx_conflict.proofs import Proof
from validation_registry_helpers import install_actual_registry


def _install_validation_contracts(repo: Path) -> None:
    """Install actual OPSX FULL registry (task_type + pack) into a Git fixture."""
    install_actual_registry(repo)


def _make_merge_conflict(repo: Path) -> None:
    _install_validation_contracts(repo)
    authority = repo / "openspec" / "changes" / "test-conflict" / "proposal.md"
    authority.parent.mkdir(parents=True, exist_ok=True)
    authority.write_text(
        "# Test conflict\n\nPreserve both interaction-free additions in `conflict.py`.\n",
        encoding="utf-8",
    )
    (authority.parent / "conflict-authority.json").write_text(
        json.dumps(
            {
                "schema": "opsx-resolve-conflict/authority-binding/v1",
                "change_id": "test-conflict",
                "precedence": [
                    "accepted_decision",
                    "main_spec",
                    "active_change",
                ],
                "paths": {
                    "conflict.py": {
                        "authority": [
                            "openspec/changes/test-conflict/proposal.md"
                        ],
                        "strategy": "namespace_closed_comment_exact_ast_union",
                        "external_authority": "none_applicable",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    base = 'def base():\n    return "base"\n'
    (repo / "conflict.py").write_text(base, encoding="utf-8")
    unit_dir = repo / "tests" / "unit"
    unit_dir.mkdir(parents=True, exist_ok=True)
    role_files = {
        "test_conflict.py": {
            "roles": ["targeted_symbol"],
            "body": (
                "from conflict import base\n"
                "\n"
                "def test_conflict_smoke():\n"
                "    assert base() == 'base'\n"
            ),
        },
        "test_conflict_interface.py": {
            "roles": ["interface_contract"],
            "body": (
                "from conflict import base\n"
                "\n"
                "def test_conflict_interface():\n"
                "    assert base() == 'base'\n"
            ),
        },
        "test_conflict_contour.py": {
            "roles": ["affected_contour"],
            "body": (
                "from conflict import base\n"
                "\n"
                "def test_conflict_contour():\n"
                "    assert base() == 'base'\n"
            ),
        },
    }
    for name, spec in role_files.items():
        (unit_dir / name).write_text(spec["body"], encoding="utf-8")
        (unit_dir / name.replace(".py", ".opsx-roles.json")).write_text(
            json.dumps(
                {
                    "schema": "opsx-resolve-conflict/test-roles/v1",
                    "roles": spec["roles"],
                    "covers_paths": ["conflict.py"],
                    "covers_symbols": ["base"],
                }
            ),
            encoding="utf-8",
        )
    run(
        [
            "git",
            "add",
            "conflict.py",
            "tests/unit",
            ".cursor/static-check",
            "openspec/changes/test-conflict",
        ],
        repo,
    )
    run(["git", "commit", "-m", "base"], repo)
    run(["git", "checkout", "-b", "feature"], repo)
    (repo / "conflict.py").write_text(
        base + '\ndef feature_write():\n    return "feature"\n',
        encoding="utf-8",
    )
    run(
        [
            "git",
            "commit",
            "-am",
            "feature",
            "-m",
            "OPSX-Change: test-conflict",
        ],
        repo,
    )
    run(["git", "checkout", "main"], repo)
    (repo / "conflict.py").write_text(
        base + '\ndef main_write():\n    return "main"\n',
        encoding="utf-8",
    )
    run(
        [
            "git",
            "commit",
            "-am",
            "main",
            "-m",
            "OPSX-Change: test-conflict",
        ],
        repo,
    )
    assert run(["git", "merge", "feature"], repo, check=False).returncode != 0


def _patch_gate(
    monkeypatch,
    state_dir: Path,
    *,
    bind_change: bool = True,
    stub_authority: bool = True,
) -> None:
    """Stub GO host gates.

    Authority is stubbed by default: production ``none_applicable`` requires an
    external OPSX declaration producer that does not exist in fixtures. Dedicated
    authority tests exercise the real verifier; GO recovery tests must not pretend
    local JSON is authoritative.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    root = str(resolve_state_root(state_dir))
    runner = state_dir / "trusted-sandbox-runner.py"
    runner.write_text(
        "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n",
        encoding="utf-8",
    )
    runner_digest = hashlib.sha256(runner.read_bytes()).hexdigest()

    def _gate(repo_root, *, mode):
        contract_hashes = {
            path.relative_to(repo_root).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(
                (repo_root / ".cursor" / "static-check").rglob("*")
            )
            if path.is_file()
        }
        return {
            "package_version": "0.34.0",
            "contract_schema_version": "opsx-resolve-conflict/v2",
            "hashes": {},
            "package_digest": "0" * 64,
            "host_contract_sha256": contract_hashes,
            "host_contract_set_digest": sha256_canonical(contract_hashes),
            "state_root": root,
            "capabilities": {
                "git": True,
                "poetry": True,
                "process_cancellation": True,
                "acl_enforcement": True,
                "state_root": root,
                "validation_sandbox": {
                    "runner": str(runner.resolve()),
                    "sha256": runner_digest,
                    "trust_digest": runner_digest,
                    "protocol": "opsx-sandbox-path-confinement/v1",
                    "enforcement_level": "OS_VERIFIED",
                    "spawn_argv_prefix": [str(runner.resolve())],
                    "network": "DENY",
                    "filesystem": "SNAPSHOT_ONLY",
                    "child_processes": "RUNNER_POLICY",
                },
            },
            "SAFE_TO_USE_PREVIEW": True,
            "SAFE_TO_USE_GO": True,
        }

    monkeypatch.setattr(orchestrator_module, "package_compatibility_gate", _gate)
    if stub_authority:
        def resolve_stub_authority(*args, **kwargs):
            paths = list(kwargs.get("conflict_paths") or [])
            return Proof.issue(
                "AUTHORITY",
                run_id=str(kwargs.get("run_id") or "fixture"),
                fingerprint=str(kwargs.get("fingerprint") or ("f" * 64)),
                scope_sha256=str(kwargs.get("scope_sha256") or ("s" * 64)),
                payload={
                    "sources": [],
                    "applicability": {path: "GO_FIXTURE_AUTHORITY_STUB" for path in paths},
                    "resolved_change_id": kwargs.get("change_id") or "test-conflict",
                    "rules": {
                        "path_stem_heuristic_forbidden": True,
                        "fixture_stub": True,
                    },
                },
            )

        monkeypatch.setattr(
            orchestrator_module,
            "resolve_authority",
            resolve_stub_authority,
        )
    elif bind_change:
        real_resolve = orchestrator_module.resolve_authority

        def resolve_test_authority(*args, **kwargs):
            kwargs["change_id"] = kwargs.get("change_id") or "test-conflict"
            return real_resolve(*args, **kwargs)

        monkeypatch.setattr(
            orchestrator_module,
            "resolve_authority",
            resolve_test_authority,
        )
    # GO fixtures stub the validation executor. Host poetry must not be required
    # for clean-unpack reproducibility: only the host PATH probe was failing.
    fake_poetry = state_dir / ("fake-poetry.cmd" if os.name == "nt" else "fake-poetry")
    if os.name == "nt":
        fake_poetry.write_text("@echo off\r\n", encoding="utf-8")
    else:
        fake_poetry.write_text("#!/bin/sh\n", encoding="utf-8")
        fake_poetry.chmod(0o755)
    real_which = validation_module.shutil.which

    def _which_stub(cmd: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if cmd == "poetry":
            return str(fake_poetry)
        return real_which(cmd, *args, **kwargs)

    monkeypatch.setattr(validation_module.shutil, "which", _which_stub)
    monkeypatch.setattr(
        validation_module,
        "run_process",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
        ),
    )


def test_go_stages_semantically_proven_merge(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    orch = SealedOrchestrator(git_repo, state_root=state_dir)
    preview = orch.preview()
    assert preview.status == "PREVIEW_READY"

    resolution = (
        'def base():\n    return "base"\n'
        '\ndef main_write():\n    return "main"\n'
        '\ndef feature_write():\n    return "feature"\n'
    )
    result = orch.go(resolutions={"conflict.py": resolution})
    assert result.status == "READY_FOR_OWNER_CONTINUE", result.payload
    assert result.payload.get("RESOLVED_CLAIMED") is False
    assert result.payload.get("FINAL_VALIDATION") == "FULL"
    assert result.payload.get("run_receipt", {}).get("final_validation") == (
        "FULL"
    )
    assert result.payload["run_receipt"]["host_contract_sha256"]
    assert len(result.payload["run_receipt"]["host_contract_set_digest"]) == 64
    assert result.payload["run_receipt"]["selected_check_ids"] == [
        "syntax-parse",
        "git-diff-check",
        "pytest-targeted",
        "pytest-interface",
        "pytest-contour",
        "pyright-strict",
        "mypy",
        "pytest-unit",
        "pytest-full",
    ]
    assert result.payload.get("semantic_proofs")
    assert (git_repo / "conflict.py").read_text(encoding="utf-8") == resolution
    journals = list(
        (state_dir / "write-transactions" / result.run_id).glob("*.json")
    )
    assert len(journals) == 1
    assert json.loads(journals[0].read_text(encoding="utf-8"))["state"] == (
        "RETIRED"
    )
    assert not list(state_dir.rglob("*.original"))
    assert not list(git_repo.glob("conflict.py.opsx-original-*"))
    assert run(["git", "ls-files", "-u"], git_repo).stdout.strip() == ""
    assert (state_dir / f"{result.run_id}.run-receipt.json").is_file()
    assert (state_dir / f"{result.run_id}.terminal.json").is_file()


def test_go_stop_persists_durable_receipt(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    orch = SealedOrchestrator(git_repo, state_root=state_dir)
    result = orch.go(resolutions={"conflict.py": "# stub\npass\n"})
    assert result.status == "STOP_FOR_OWNER"
    stop_path = Path(str(result.payload["STOP_RECEIPT_PATH"]))
    assert stop_path.is_file()
    assert "STRUCTURAL_" in str(result.payload.get("STOP_REASON", "")) or str(
        result.payload.get("STOP_REASON", "")
    ).startswith("SEMANTIC_")


def test_go_rejects_arbitrary_stub_text(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    orch = SealedOrchestrator(git_repo, state_root=state_dir)
    result = orch.go(resolutions={"conflict.py": "# main_write feature_write\npass\n"})
    assert result.status == "STOP_FOR_OWNER"
    assert str(result.payload.get("STOP_REASON", "")).startswith(
        ("STRUCTURAL_", "SEMANTIC_")
    )


def test_go_without_full_validation_registry_does_not_stage(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    (git_repo / ".cursor" / "static-check" / "registry.yaml").unlink()
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={
            "conflict.py": (
                'def base():\n    return "base"\n'
                '\ndef main_write():\n    return "main"\n'
                '\ndef feature_write():\n    return "feature"\n'
            )
        }
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] == "MANDATORY_FULL_VALIDATION_UNAVAILABLE"
    assert run(["git", "ls-files", "-u"], git_repo).stdout.strip()


def test_go_without_applicable_authority_does_not_write(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir, stub_authority=False)
    authority_root = git_repo / "openspec" / "changes" / "test-conflict"
    (authority_root / "proposal.md").unlink()
    resolution = (
        'def base():\n    return "base"\n'
        '\ndef main_write():\n    return "main"\n'
        '\ndef feature_write():\n    return "feature"\n'
    )
    before = (git_repo / "conflict.py").read_text(encoding="utf-8")
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={"conflict.py": resolution}
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] == "APPLICABLE_SEMANTIC_AUTHORITY_MISSING"
    assert (git_repo / "conflict.py").read_text(encoding="utf-8") == before


def test_go_requires_explicit_change_binding(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir, bind_change=False, stub_authority=False)
    before = (git_repo / "conflict.py").read_bytes()
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={
            "conflict.py": (
                'def base():\n    return "base"\n'
                '\ndef main_write():\n    return "main"\n'
                '\ndef feature_write():\n    return "feature"\n'
            )
        }
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] == (
        "APPLICABLE_AUTHORITY_CHANGE_REQUIRED"
    )
    assert (git_repo / "conflict.py").read_bytes() == before


def test_host_contract_drift_before_write_stops_without_mutation(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    real_prove = orchestrator_module.prove_text_resolution
    registry = git_repo / ".cursor" / "static-check" / "registry.yaml"

    def prove_then_drift(*args, **kwargs):
        proof = real_prove(*args, **kwargs)
        registry.write_text(
            registry.read_text(encoding="utf-8") + "\n# external drift\n",
            encoding="utf-8",
        )
        return proof

    monkeypatch.setattr(
        orchestrator_module,
        "prove_text_resolution",
        prove_then_drift,
    )
    before = (git_repo / "conflict.py").read_text(encoding="utf-8")
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={
            "conflict.py": (
                'def base():\n    return "base"\n'
                '\ndef main_write():\n    return "main"\n'
                '\ndef feature_write():\n    return "feature"\n'
            )
        }
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] == "HOST_CONTRACT_DRIFT"
    assert (git_repo / "conflict.py").read_text(encoding="utf-8") == before


def test_auto_merged_path_outside_conflict_scope_stops_before_write(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _install_validation_contracts(git_repo)
    authority = (
        git_repo / "openspec" / "changes" / "test-conflict" / "proposal.md"
    )
    authority.parent.mkdir(parents=True, exist_ok=True)
    authority.write_text("Preserve both additions in `conflict.py`.\n", encoding="utf-8")
    (authority.parent / "conflict-authority.json").write_text(
        json.dumps(
            {
                "schema": "opsx-resolve-conflict/authority-binding/v1",
                "change_id": "test-conflict",
                "precedence": [
                    "accepted_decision",
                    "main_spec",
                    "active_change",
                ],
                "paths": {
                    "conflict.py": {
                        "authority": [
                            "openspec/changes/test-conflict/proposal.md"
                        ],
                        "strategy": "namespace_closed_comment_exact_ast_union",
                        "external_authority": "none_applicable",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    base = 'def base():\n    return "base"\n'
    (git_repo / "conflict.py").write_text(base, encoding="utf-8")
    (git_repo / "caller.py").write_text("VALUE = 1\n", encoding="utf-8")
    run(["git", "add", "."], git_repo)
    run(["git", "commit", "-m", "base"], git_repo)
    run(["git", "checkout", "-b", "feature"], git_repo)
    (git_repo / "conflict.py").write_text(
        base + '\ndef feature_write():\n    return "feature"\n',
        encoding="utf-8",
    )
    (git_repo / "caller.py").write_text("VALUE = 2\n", encoding="utf-8")
    run(
        [
            "git",
            "commit",
            "-am",
            "feature",
            "-m",
            "OPSX-Change: test-conflict",
        ],
        git_repo,
    )
    run(["git", "checkout", "main"], git_repo)
    (git_repo / "conflict.py").write_text(
        base + '\ndef main_write():\n    return "main"\n',
        encoding="utf-8",
    )
    run(
        [
            "git",
            "commit",
            "-am",
            "main",
            "-m",
            "OPSX-Change: test-conflict",
        ],
        git_repo,
    )
    assert run(["git", "merge", "feature"], git_repo, check=False).returncode != 0
    _patch_gate(monkeypatch, state_dir)

    before = (git_repo / "conflict.py").read_text(encoding="utf-8")
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={
            "conflict.py": (
                base
                + '\ndef main_write():\n    return "main"\n'
                + '\ndef feature_write():\n    return "feature"\n'
            )
        }
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] == "OPERATION_GRAPH_OUTSIDE_CONFLICT_SCOPE"
    assert "caller.py" in str(result.payload["EVIDENCE"])
    assert (git_repo / "conflict.py").read_text(encoding="utf-8") == before


def test_go_rejects_obsolete_base_argument(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={"conflict.py": "irrelevant\n"},
        base="main",
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] == "BASE_ARGUMENT_NOT_SUPPORTED"


@pytest.mark.parametrize("crash_event", ["WRITE_DONE", "CHECK_DONE", "STAGE_DONE"])
def test_go_resumes_after_durable_transition_crash(
    crash_event: str,
    git_repo: Path,
    isolated_state: Path,
    monkeypatch,
) -> None:
    """Every durable unit transition must be replay-safe after interruption."""
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    resolution = (
        'def base():\n    return "base"\n'
        '\ndef main_write():\n    return "main"\n'
        '\ndef feature_write():\n    return "feature"\n'
    )
    original_append = ExecutionLedger.append
    crashed = False

    def crash_after_append(self, event, payload=None):
        nonlocal crashed
        digest = original_append(self, event, payload)
        if event == crash_event and not crashed:
            crashed = True
            raise RuntimeError(f"simulated crash after {event}")
        return digest

    monkeypatch.setattr(ExecutionLedger, "append", crash_after_append)
    with pytest.raises(RuntimeError, match="simulated crash"):
        SealedOrchestrator(git_repo, state_root=state_dir)._go_impl(
            resolutions={"conflict.py": resolution},
            scope=None,
            change_id=None,
            store_id=None,
            base=None,
            final="FULL",
            run_meta={},
        )
    monkeypatch.setattr(ExecutionLedger, "append", original_append)

    resumed = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={"conflict.py": resolution}
    )
    assert resumed.status == "READY_FOR_OWNER_CONTINUE", resumed.payload
    assert len(resumed.payload["unit_receipts"]) == 1
    assert run(["git", "ls-files", "-u"], git_repo).stdout.strip() == ""


def test_cancellation_failure_cannot_leave_success_receipt(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    process_supervisor = supervisor()
    real_close = process_supervisor.close_barrier
    failed_once = False

    def fail_terminal_once(*, reason: str):
        nonlocal failed_once
        if reason == "RUN_COMPLETE" and not failed_once:
            failed_once = True
            return {
                "CANCELLATION_BARRIER_CLOSED": False,
                "BACKGROUND_PROCESSES": 1,
            }
        return real_close(reason=reason)

    monkeypatch.setattr(process_supervisor, "close_barrier", fail_terminal_once)
    resolution = (
        'def base():\n    return "base"\n'
        '\ndef main_write():\n    return "main"\n'
        '\ndef feature_write():\n    return "feature"\n'
    )
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={"conflict.py": resolution}
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] == "CANCELLATION_BARRIER_FAILED"
    assert not list(state_dir.glob("*.run-receipt.json"))
    ledger_text = next(state_dir.glob("*.ledger.jsonl")).read_text(encoding="utf-8")
    assert '"event": "STOP"' in ledger_text
    assert '"event": "CANCELLATION_BARRIER_CLOSED"' in ledger_text


def test_terminal_publication_holds_process_admission_barrier(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    real_persist = orchestrator_module.persist_private_json
    observed: list[bool] = []

    def observe_terminal_receipt(path: Path, payload):
        if path.name.endswith(".run-receipt.json"):
            observed.append(supervisor().stopping)
        return real_persist(path, payload)

    monkeypatch.setattr(
        orchestrator_module,
        "persist_private_json",
        observe_terminal_receipt,
    )
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={
            "conflict.py": (
                'def base():\n    return "base"\n'
                '\ndef main_write():\n    return "main"\n'
                '\ndef feature_write():\n    return "feature"\n'
            )
        }
    )
    assert result.status == "READY_FOR_OWNER_CONTINUE"
    assert observed == [True]
    assert supervisor().stopping is False


def test_forged_terminal_bundle_is_rejected(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    """Altered ledger/hashes must not recover as terminal success."""
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    orch = SealedOrchestrator(git_repo, state_root=state_dir)
    resolution = (
        'def base():\n    return "base"\n'
        '\ndef main_write():\n    return "main"\n'
        '\ndef feature_write():\n    return "feature"\n'
    )
    first = orch.go(resolutions={"conflict.py": resolution})
    assert first.status == "READY_FOR_OWNER_CONTINUE"
    terminal = state_dir / f"{first.run_id}.terminal.json"
    payload = json.loads(terminal.read_text(encoding="utf-8"))
    payload["ledger_final_hash"] = "0" * 64
    payload["run_manifest"]["ledger_final_hash"] = "0" * 64
    payload["run_receipt"]["ledger_final_hash"] = "0" * 64
    payload["run_manifest_sha256"] = sha256_canonical(payload["run_manifest"])
    payload["run_receipt_sha256"] = sha256_canonical(payload["run_receipt"])
    terminal.write_text(json.dumps(payload), encoding="utf-8")
    (state_dir / f"{first.run_id}.run.json").unlink(missing_ok=True)
    second = orch.go(resolutions={"conflict.py": resolution})
    assert second.status == "STOP_FOR_OWNER"
    assert second.payload["STOP_REASON"] in {
        "TERMINAL_BUNDLE_LEDGER_FINAL_DRIFT",
        "TERMINAL_BUNDLE_LEDGER_HASH_MISMATCH",
        "TERMINAL_BUNDLE_COMPONENT_HASH_MISMATCH",
    }


def test_terminal_bundle_failure_leaves_no_success_authority(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    real_persist = orchestrator_module.persist_private_json

    def fail_terminal_bundle(path: Path, payload):
        if path.name.endswith(".terminal.json"):
            raise OSError("injected terminal bundle failure")
        return real_persist(path, payload)

    monkeypatch.setattr(
        orchestrator_module,
        "persist_private_json",
        fail_terminal_bundle,
    )
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={
            "conflict.py": (
                'def base():\n    return "base"\n'
                '\ndef main_write():\n    return "main"\n'
                '\ndef feature_write():\n    return "feature"\n'
            )
        }
    )
    assert result.status == "STOP_FOR_OWNER"
    assert not list(state_dir.glob("*.terminal.json"))
    assert not list(state_dir.glob("*.run-receipt.json"))
    ledger_text = (state_dir / f"{result.run_id}.ledger.jsonl").read_text(
        encoding="utf-8"
    )
    assert '"event": "TERMINAL_PREPARED"' in ledger_text
    assert '"event": "RUN_FINALIZED"' not in ledger_text


def test_terminal_bundle_remains_authoritative_when_cache_refresh_fails(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    real_save = runtime_module.save_run_manifest

    def fail_success_manifest(path: Path, manifest):
        if manifest.status == "READY_FOR_OWNER_CONTINUE":
            raise OSError("injected manifest cache failure")
        return real_save(path, manifest)

    monkeypatch.setattr(
        runtime_module,
        "save_run_manifest",
        fail_success_manifest,
    )
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={
            "conflict.py": (
                'def base():\n    return "base"\n'
                '\ndef main_write():\n    return "main"\n'
                '\ndef feature_write():\n    return "feature"\n'
            )
        }
    )
    assert result.status == "READY_FOR_OWNER_CONTINUE"
    assert (state_dir / f"{result.run_id}.terminal.json").is_file()
    assert result.payload["publication_cache_errors"]


def test_go_rejects_validation_executor_kwarg(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    orch = SealedOrchestrator(git_repo, state_root=state_dir)
    result = orch.go(
        resolutions={
            "conflict.py": (
                'def base():\n    return "base"\n'
                '\ndef main_write():\n    return "main"\n'
                '\ndef feature_write():\n    return "feature"\n'
            )
        },
        validation_executor=lambda plan, check_id: None,  # type: ignore[arg-type]
    )
    assert result.status == "STOP_FOR_OWNER"
    blob = str(result.payload)
    assert "validation_executor" in blob or "forbidden go kwargs" in blob


def test_go_rejects_forged_unrelated_scope(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    git = TypedGit(git_repo)
    state = detect_operation_state(git_repo, git)
    forged = ScopeManifest(
        [
            ScopeItem(
                path="unrelated.py",
                unit_id="unit-x",
                reason="forged",
                authority_source="attacker",
                authority_sha256="0" * 64,
                allowed_operation="write",
                expected_semantic_change="tamper",
                initial_stage_oids={},
                initial_worktree_sha256=sha256_text("x = 1\n"),
                required_checks=(("syntax-parse", "unrelated.py"),),
            )
        ],
        run_id="forged",
        frozen_at_fingerprint=state.fingerprint,
    )
    orch = SealedOrchestrator(git_repo, state_root=state_dir)
    result = orch.go(
        scope=forged,
        resolutions={
            "unrelated.py": "x = 2\n",
            "conflict.py": (
                'def base():\n    return "base"\n'
                '\ndef main_write():\n    return "main"\n'
                '\ndef feature_write():\n    return "feature"\n'
            ),
        },
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] in {
        "SCOPE_NOT_BOUND_TO_CONFLICT_INVENTORY",
        "SCOPE_STAGE_OID_MISMATCH",
        "CALLER_SCOPE_REJECTED",
        "SCOPE_FINGERPRINT_MISMATCH",
    }


def test_write_compare_and_swap_preserves_external_edit(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    """External edit after state capture must survive a failed GO write."""
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    real_write = orchestrator_module.write_scoped_file
    external = "# external editor content\n"

    def edit_then_write(*args, **kwargs):
        (git_repo / "conflict.py").write_text(external, encoding="utf-8")
        return real_write(*args, **kwargs)

    monkeypatch.setattr(orchestrator_module, "write_scoped_file", edit_then_write)
    resolution = (
        'def base():\n    return "base"\n'
        '\ndef main_write():\n    return "main"\n'
        '\ndef feature_write():\n    return "feature"\n'
    )
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={"conflict.py": resolution}
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] == "WORKTREE_COMPARE_AND_SWAP_FAILED"
    assert (git_repo / "conflict.py").read_text(encoding="utf-8") == external


def test_conditional_install_does_not_overwrite_racing_path_writer(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    """A writer immediately before install wins; its content remains at target."""
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    real_link_noreplace = write_atomic_module._link_noreplace
    external = "# external writer won the target path\n"
    injected = False

    def inject_before_install(source: Path, target: Path) -> None:
        nonlocal injected
        if not injected:
            injected = True
            target.write_text(external, encoding="utf-8")
        real_link_noreplace(source, target)

    monkeypatch.setattr(
        write_atomic_module,
        "_link_noreplace",
        inject_before_install,
    )
    resolution = (
        'def base():\n    return "base"\n'
        '\ndef main_write():\n    return "main"\n'
        '\ndef feature_write():\n    return "feature"\n'
    )
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={"conflict.py": resolution}
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] == "WORKTREE_CONCURRENT_PATH_WRITE"
    assert (git_repo / "conflict.py").read_text(encoding="utf-8") == external
    backups = list(git_repo.glob("conflict.py.opsx-original-*"))
    assert backups == []
    journals = list(state_dir.rglob("*.json"))
    assert any(
        json.loads(path.read_text(encoding="utf-8")).get("state")
        == "EXTERNAL_WINNER"
        for path in journals
    )


def test_conditional_claim_restores_writer_racing_after_initial_hash(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    """A change immediately before target claim is detected and restored."""
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    real_claim = write_atomic_module._claim_target
    external = "# external change immediately before claim\n"
    injected = False

    def inject_before_claim(target: Path, backup: Path) -> None:
        nonlocal injected
        if not injected:
            injected = True
            target.write_text(external, encoding="utf-8")
        real_claim(target, backup)

    monkeypatch.setattr(write_atomic_module, "_claim_target", inject_before_claim)
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={
            "conflict.py": (
                'def base():\n    return "base"\n'
                '\ndef main_write():\n    return "main"\n'
                '\ndef feature_write():\n    return "feature"\n'
            )
        }
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] == "WORKTREE_COMPARE_AND_SWAP_FAILED"
    assert (git_repo / "conflict.py").read_text(encoding="utf-8") == external


@pytest.mark.parametrize(
    ("attack_point", "stop_reason"),
    [
        ("before_add", "STAGED_BLOB_BYTES_MISMATCH"),
        ("after_add", "COMPLETED_PATH_WORKTREE_DRIFT"),
        ("during_add", "STAGED_BLOB_BYTES_MISMATCH"),
    ],
)
def test_stage_fault_injection_never_publishes_unvalidated_content(
    git_repo: Path,
    isolated_state: Path,
    monkeypatch,
    attack_point: str,
    stop_reason: str,
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    resolution = (
        'def base():\n    return "base"\n'
        '\ndef main_write():\n    return "main"\n'
        '\ndef feature_write():\n    return "feature"\n'
    )
    target = git_repo / "conflict.py"
    hostile = 'def hostile():\n    return "not-validated"\n'
    real_stage = TypedGit.stage_validated_bytes

    def injected_stage(self, *, path, data, mode):
        if attack_point == "before_add":
            return real_stage(
                self,
                path=path,
                data=hostile.encode("utf-8"),
                mode=mode,
            )
        if attack_point == "after_add":
            oid = real_stage(self, path=path, data=data, mode=mode)
            target.write_text(hostile, encoding="utf-8")
            return oid
        oid = real_stage(
            self,
            path=path,
            data=hostile.encode("utf-8"),
            mode=mode,
        )
        target.write_text(resolution, encoding="utf-8")
        return oid

    monkeypatch.setattr(TypedGit, "stage_validated_bytes", injected_stage)
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={"conflict.py": resolution}
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] == stop_reason
    assert not (state_dir / f"{result.run_id}.run-receipt.json").exists()


def test_terminal_recheck_detects_post_stage_worktree_drift(
    git_repo: Path,
    isolated_state: Path,
    monkeypatch,
) -> None:
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    resolution = (
        'def base():\n    return "base"\n'
        '\ndef main_write():\n    return "main"\n'
        '\ndef feature_write():\n    return "feature"\n'
    )
    target = git_repo / "conflict.py"
    real_verify = orchestrator_module._verify_staged_evidence

    def drift_before_terminal(**kwargs):
        target.write_text(
            'def late_writer():\n    return "not-validated"\n',
            encoding="utf-8",
        )
        return real_verify(**kwargs)

    monkeypatch.setattr(
        orchestrator_module,
        "_verify_staged_evidence",
        drift_before_terminal,
    )
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={"conflict.py": resolution}
    )
    assert result.status == "STOP_FOR_OWNER"
    assert result.payload["STOP_REASON"] == "COMPLETED_PATH_WORKTREE_DRIFT"
    assert not (state_dir / f"{result.run_id}.run-receipt.json").exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX executable mode semantics")
def test_conditional_write_preserves_executable_mode(
    git_repo: Path, isolated_state: Path, monkeypatch
) -> None:
    """Replacing conflict content must not silently remove executable mode."""
    state_dir = isolated_state / "state"
    monkeypatch.setenv("OPSX_CONFLICT_STATE", str(state_dir))
    _make_merge_conflict(git_repo)
    _patch_gate(monkeypatch, state_dir)
    target = git_repo / "conflict.py"
    target.chmod(0o755)
    resolution = (
        'def base():\n    return "base"\n'
        '\ndef main_write():\n    return "main"\n'
        '\ndef feature_write():\n    return "feature"\n'
    )
    result = SealedOrchestrator(git_repo, state_root=state_dir).go(
        resolutions={"conflict.py": resolution}
    )
    assert result.status == "READY_FOR_OWNER_CONTINUE", result.payload
    assert stat.S_IMODE(target.stat().st_mode) == 0o755


def test_contradictory_merge_and_rebase_markers_stop(git_repo: Path) -> None:
    _make_merge_conflict(git_repo)
    rebase_merge = git_repo / ".git" / "rebase-merge"
    rebase_merge.mkdir(exist_ok=True)
    (rebase_merge / "head-name").write_text("refs/heads/x\n", encoding="utf-8")
    from opsx_conflict.errors import StopRequired
    from opsx_conflict.operation import detect_operation_state
    with pytest.raises(StopRequired) as exc:
        detect_operation_state(git_repo, TypedGit(git_repo))
    assert exc.value.reason == "CONTRADICTORY_GIT_OPERATION_MARKERS"
