"""R29 exact-match replay terminal acceptance and negative fault injection."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

from opsx_conflict.errors import CLI_STOP_ENVELOPE_SCHEMA, CLI_STOP_EXIT_CODE, StopRequired
from opsx_conflict.runtime import build_cli_stop_envelope, emit_cli_stop, run_cli

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PACKAGE_ROOT / "scripts"


def _load_replay_module():
    """Load build_replay_evidence.py as a module."""
    path = SCRIPTS / "build_replay_evidence.py"
    spec = importlib.util.spec_from_file_location("build_replay_evidence_r29", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _base_git_state(**overrides: str) -> dict[str, str]:
    """Minimal git snapshot for assertion tests."""
    base = {
        "head": "a" * 40,
        "status_porcelain_v2": "",
        "ls_files_unmerged": "100644 " + ("b" * 40) + " 1\tconflict.py\n",
        "refs": "refs/heads/master " + ("a" * 40) + "\n",
        "diff_cached_name_status": "",
        "conflict_worktree_sha256": "c" * 64,
    }
    base.update(overrides)
    return base


def _state_stdout(*, operation: str, operation_head: str) -> str:
    """Synthetic state command JSON."""
    payload = {
        "fingerprint": "f" * 64,
        "state": {
            "operation": operation,
            "operation_head": operation_head,
            "unmerged": [
                {"stage": 1, "oid": "1" * 40, "path": "conflict.py", "mode": "100644"},
                {"stage": 2, "oid": "2" * 40, "path": "conflict.py", "mode": "100644"},
                {"stage": 3, "oid": "3" * 40, "path": "conflict.py", "mode": "100644"},
            ],
        },
        "stage_matrix": {},
    }
    return json.dumps(payload, indent=2)


def _stop_stdout(*, reason: str, gate: str) -> str:
    """Synthetic CLI STOP envelope."""
    return json.dumps(
        {
            "schema": CLI_STOP_ENVELOPE_SCHEMA,
            "schema_version": "1",
            "status": "STOP",
            "reason": reason,
            "details": {"go_capability": False},
            "command": "go",
            "package_version": "0.39.0",
            "reached_gate": gate,
        },
        indent=2,
    )


def test_merge_state_exact_detection() -> None:
    """Merge state case passes only with operation=merge and real stage OIDs."""
    replay = _load_replay_module()
    head = "d" * 40
    expectation = replay.make_expectation(
        case_id="merge_state_detection",
        command_kind="state",
        expected_exit_code=0,
        expected_status="OK",
        expected_stop_reason=None,
        expected_operation="merge",
        expected_gate="operation_state_detection",
        expected_state={
            "require_unmerged_nonempty": True,
            "require_stage_oids": True,
            "require_operation_head": True,
            "refs_immutable": True,
            "index_immutable": True,
            "worktree_conflict_immutable": True,
            "process_delta_empty": True,
            "forbid_traceback": True,
            "forbid_scope_file_required_as_pass": True,
        },
    )
    git = _base_git_state()
    result = replay.evaluate_replay_case(
        expectation=expectation,
        returncode=0,
        stdout=_state_stdout(operation="merge", operation_head=head),
        stderr="",
        before_state=git,
        after_state=git,
        process_delta=[],
        fixture_meta={"expected_operation_head": head, "ls_files_unmerged": "x"},
    )
    assert result["passed"] is True
    assert result["actual"]["operation"] == "merge"


def test_rebase_state_exact_detection() -> None:
    """Rebase state case passes only with operation=rebase and stage OIDs."""
    replay = _load_replay_module()
    head = "e" * 40
    expectation = replay.make_expectation(
        case_id="rebase_state_detection",
        command_kind="state",
        expected_exit_code=0,
        expected_status="OK",
        expected_stop_reason=None,
        expected_operation="rebase",
        expected_gate="operation_state_detection",
        expected_state={
            "require_unmerged_nonempty": True,
            "require_stage_oids": True,
            "require_operation_head": True,
            "refs_immutable": True,
            "index_immutable": True,
            "worktree_conflict_immutable": True,
            "process_delta_empty": True,
            "forbid_traceback": True,
            "forbid_scope_file_required_as_pass": True,
        },
    )
    git = _base_git_state()
    result = replay.evaluate_replay_case(
        expectation=expectation,
        returncode=0,
        stdout=_state_stdout(operation="rebase", operation_head=head),
        stderr="",
        before_state=git,
        after_state=git,
        process_delta=[],
        fixture_meta={"expected_operation_head": head},
    )
    assert result["passed"] is True
    assert result["actual"]["operation"] == "rebase"


def test_valid_scope_go_exact_package_disabled_stop() -> None:
    """Scoped GO PASS requires exact PACKAGE_GO_CAPABILITY_DISABLED envelope."""
    replay = _load_replay_module()
    expectation = replay.make_expectation(
        case_id="merge_go_package_capability_disabled",
        command_kind="go",
        expected_exit_code=CLI_STOP_EXIT_CODE,
        expected_status="STOP",
        expected_stop_reason="PACKAGE_GO_CAPABILITY_DISABLED",
        expected_operation=None,
        expected_gate="package_compatibility_gate",
        expected_state={
            "refs_immutable": True,
            "index_immutable": True,
            "worktree_conflict_immutable": True,
            "process_delta_empty": True,
            "forbid_traceback": True,
            "forbid_scope_file_required_as_pass": True,
            "go_capability": False,
        },
    )
    git = _base_git_state()
    result = replay.evaluate_replay_case(
        expectation=expectation,
        returncode=CLI_STOP_EXIT_CODE,
        stdout=_stop_stdout(
            reason="PACKAGE_GO_CAPABILITY_DISABLED",
            gate="package_compatibility_gate",
        ),
        stderr="",
        before_state=git,
        after_state=git,
        process_delta=[],
    )
    assert result["passed"] is True
    assert result["reached_gate"] == "package_compatibility_gate"


@pytest.mark.parametrize(
    "name,kwargs",
    [
        (
            "arbitrary_nonzero",
            {
                "returncode": 1,
                "stdout": _stop_stdout(
                    reason="PACKAGE_GO_CAPABILITY_DISABLED",
                    gate="package_compatibility_gate",
                ),
                "stderr": "",
            },
        ),
        (
            "scope_file_required",
            {
                "returncode": CLI_STOP_EXIT_CODE,
                "stdout": _stop_stdout(
                    reason="SCOPE_FILE_REQUIRED", gate="cli_argument_gate"
                ),
                "stderr": "",
            },
        ),
        (
            "wrong_reason",
            {
                "returncode": CLI_STOP_EXIT_CODE,
                "stdout": _stop_stdout(
                    reason="EXTERNAL_TRUST_ROOT_MISSING",
                    gate="package_compatibility_gate",
                ),
                "stderr": "",
            },
        ),
        (
            "malformed_json",
            {
                "returncode": CLI_STOP_EXIT_CODE,
                "stdout": "not-json",
                "stderr": "",
            },
        ),
        (
            "traceback",
            {
                "returncode": CLI_STOP_EXIT_CODE,
                "stdout": _stop_stdout(
                    reason="PACKAGE_GO_CAPABILITY_DISABLED",
                    gate="package_compatibility_gate",
                ),
                "stderr": 'Traceback (most recent call last):\n  File "x.py", line 1\n',
            },
        ),
        (
            "operation_mismatch",
            {
                "returncode": 0,
                "stdout": _state_stdout(operation="cherry-pick", operation_head="f" * 40),
                "stderr": "",
                "command_kind": "state",
            },
        ),
        (
            "state_mutation",
            {
                "returncode": CLI_STOP_EXIT_CODE,
                "stdout": _stop_stdout(
                    reason="PACKAGE_GO_CAPABILITY_DISABLED",
                    gate="package_compatibility_gate",
                ),
                "stderr": "",
                "mutate": True,
            },
        ),
        (
            "missing_stage_oid",
            {
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "state": {
                            "operation": "merge",
                            "operation_head": "a" * 40,
                            "unmerged": [{"stage": 1, "oid": "", "path": "conflict.py"}],
                        }
                    }
                ),
                "stderr": "",
                "command_kind": "state",
            },
        ),
        (
            "gate_not_reached",
            {
                "returncode": CLI_STOP_EXIT_CODE,
                "stdout": _stop_stdout(
                    reason="PACKAGE_GO_CAPABILITY_DISABLED",
                    gate="wrong_gate",
                ),
                "stderr": "",
            },
        ),
    ],
)
def test_negative_fault_injection(name: str, kwargs: dict[str, Any]) -> None:
    """Fault injections must fail exact-match PASS."""
    replay = _load_replay_module()
    command_kind = kwargs.pop("command_kind", "go")
    mutate = kwargs.pop("mutate", False)
    if command_kind == "state":
        expectation = replay.make_expectation(
            case_id="neg_state",
            command_kind="state",
            expected_exit_code=0,
            expected_status="OK",
            expected_stop_reason=None,
            expected_operation="merge",
            expected_gate="operation_state_detection",
            expected_state={
                "require_unmerged_nonempty": True,
                "require_stage_oids": True,
                "require_operation_head": True,
                "refs_immutable": True,
                "index_immutable": True,
                "worktree_conflict_immutable": True,
                "process_delta_empty": True,
                "forbid_traceback": True,
                "forbid_scope_file_required_as_pass": True,
            },
        )
        fixture_meta = {"expected_operation_head": "a" * 40}
    else:
        expectation = replay.make_expectation(
            case_id="neg_go",
            command_kind="go",
            expected_exit_code=CLI_STOP_EXIT_CODE,
            expected_status="STOP",
            expected_stop_reason="PACKAGE_GO_CAPABILITY_DISABLED",
            expected_operation=None,
            expected_gate="package_compatibility_gate",
            expected_state={
                "refs_immutable": True,
                "index_immutable": True,
                "worktree_conflict_immutable": True,
                "process_delta_empty": True,
                "forbid_traceback": True,
                "forbid_scope_file_required_as_pass": True,
                "go_capability": False,
            },
        )
        fixture_meta = None
    before = _base_git_state()
    after = dict(before)
    if mutate:
        after["refs"] = "refs/heads/master " + ("9" * 40) + "\n"
    result = replay.evaluate_replay_case(
        expectation=expectation,
        before_state=before,
        after_state=after,
        process_delta=[],
        fixture_meta=fixture_meta,
        **kwargs,
    )
    assert result["passed"] is False, name


def test_missing_scope_rejected_as_target_pass() -> None:
    """SCOPE_FILE_REQUIRED must never PASS a capability-gate expectation."""
    replay = _load_replay_module()
    expectation = replay.make_expectation(
        case_id="missing_scope",
        command_kind="go",
        expected_exit_code=CLI_STOP_EXIT_CODE,
        expected_status="STOP",
        expected_stop_reason="PACKAGE_GO_CAPABILITY_DISABLED",
        expected_operation=None,
        expected_gate="package_compatibility_gate",
        expected_state={
            "forbid_scope_file_required_as_pass": True,
            "forbid_traceback": True,
            "refs_immutable": True,
            "index_immutable": True,
            "worktree_conflict_immutable": True,
            "process_delta_empty": True,
            "go_capability": False,
        },
    )
    git = _base_git_state()
    result = replay.evaluate_replay_case(
        expectation=expectation,
        returncode=CLI_STOP_EXIT_CODE,
        stdout=_stop_stdout(reason="SCOPE_FILE_REQUIRED", gate="cli_argument_gate"),
        stderr="",
        before_state=git,
        after_state=git,
        process_delta=[],
    )
    assert result["passed"] is False
    names = {a["name"]: a["passed"] for a in result["assertions"]}
    assert names["scope_file_required_not_accepted_as_target"] is False


def test_exact_structured_stop_envelope() -> None:
    """CLI StopRequired envelope contains required stable fields."""
    envelope = build_cli_stop_envelope(
        reason="PACKAGE_GO_CAPABILITY_DISABLED",
        details={"go_capability": False},
        command="go",
    )
    assert envelope["schema"] == CLI_STOP_ENVELOPE_SCHEMA
    assert envelope["status"] == "STOP"
    assert envelope["reason"] == "PACKAGE_GO_CAPABILITY_DISABLED"
    assert envelope["command"] == "go"
    assert "package_version" in envelope
    assert envelope["reached_gate"] == "package_compatibility_gate"
    assert isinstance(envelope["details"], dict)


def test_emit_cli_stop_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    """emit_cli_stop returns the stable nonzero STOP exit code."""
    code = emit_cli_stop(
        reason="SCOPE_FILE_REQUIRED",
        details={},
        command="go",
    )
    assert code == CLI_STOP_EXIT_CODE
    out = json.loads(capsys.readouterr().out)
    assert out["reason"] == "SCOPE_FILE_REQUIRED"
    assert out["status"] == "STOP"


def test_unexpected_exception_remains_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected exceptions are not masked as typed STOP envelopes."""

    def _boom() -> int:
        raise RuntimeError("unexpected_internal_failure")

    monkeypatch.setattr("opsx_conflict.runtime._cli", _boom)
    with pytest.raises(RuntimeError, match="unexpected_internal_failure"):
        run_cli(["state", "--repo", "."])


def test_run_cli_maps_stop_required(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """run_cli converts StopRequired into the structured envelope."""

    def _stop() -> int:
        raise StopRequired("SCOPE_FILE_REQUIRED")

    monkeypatch.setattr("opsx_conflict.runtime._cli", _stop)
    code = run_cli(["go", "--repo", ".", "--scope", "missing.json"])
    assert code == CLI_STOP_EXIT_CODE
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "STOP"
    assert out["reason"] == "SCOPE_FILE_REQUIRED"
    assert "Traceback" not in capsys.readouterr().err
