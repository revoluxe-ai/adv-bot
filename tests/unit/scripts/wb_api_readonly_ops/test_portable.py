"""Regression tests for the CWD-independent read-only collector contract."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from scripts.wb_api_readonly_ops.collect.portable import (
    CollectionContract,
    CredentialsUnavailableError,
    _write_portable_metadata,
    build_legacy_command,
    claim_output_dir,
    classify_days,
    require_credentials,
    validate_integrity,
)
from scripts.wb_api_readonly_ops.mutation_guard import MUTATION_WRITE_OPS


def _contract(tmp_path: Path, run_id: str) -> CollectionContract:
    """Build a deterministic test contract."""
    return CollectionContract(
        client="A1",
        period_start=date(2026, 9, 6),
        period_end=date(2026, 9, 14),
        run_id=run_id,
        output_dir=tmp_path / run_id,
        shop_id="test-shop",
        closed_through=date(2026, 9, 14),
    )


def _args() -> argparse.Namespace:
    """Return the legacy compatibility options used by the wrapper."""
    return argparse.Namespace(max_seconds=1.0, max_api_calls=2)


def _fake_run(contract: CollectionContract) -> dict[str, object]:
    """Write a small fake legacy result and exercise the real metadata gate."""
    claim_output_dir(contract.output_dir)
    raw = contract.output_dir / "raw" / "facts.jsonl"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text('{"value": 1}\n', encoding="utf-8")
    (contract.output_dir / "report.json").write_text(
        json.dumps(
            {
                "coverage": [{"family": "test", "completeness": "FULL_AVAILABLE"}],
                "integrity": {"errors": []},
                "missing_collector_capabilities": ["stocks"],
            }
        ),
        encoding="utf-8",
    )
    return _write_portable_metadata(
        contract,
        command=["python", "run.py", "--mode", "collect"],
        collector_returncode=0,
        collector_stdout="OK\n",
        collector_stderr="",
    )


def test_manifest_and_integrity_gate(tmp_path: Path) -> None:
    """Metadata has provenance, coverage, hashes, and detects tampering."""
    result = _fake_run(_contract(tmp_path, "run-one"))
    assert result["integrity"]["pass"] is True
    root = tmp_path / "run-one"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["client"] == "A1"
    assert manifest["period"] == "2026-09-06..2026-09-14"
    assert manifest["mode"] == "STRICT_READ_ONLY"
    assert manifest["business_writes"] == 0
    assert manifest["db_writes"] == 0
    (root / "raw" / "facts.jsonl").write_text("tampered\n", encoding="utf-8")
    assert validate_integrity(root)["pass"] is False


def test_two_run_ids_have_disjoint_outputs(tmp_path: Path) -> None:
    """Separate run IDs claim separate directories and never merge files."""
    first = _fake_run(_contract(tmp_path, "run-one"))
    second = _fake_run(_contract(tmp_path, "run-two"))
    assert first["manifest"]["run_id"] != second["manifest"]["run_id"]
    first_files = {
        path.relative_to(tmp_path / "run-one")
        for path in (tmp_path / "run-one").rglob("*")
        if path.is_file()
    }
    second_files = {
        path.relative_to(tmp_path / "run-two")
        for path in (tmp_path / "run-two").rglob("*")
        if path.is_file()
    }
    assert first_files == second_files
    assert (tmp_path / "run-one" / "raw" / "facts.jsonl").read_text(
        encoding="utf-8"
    ) == (tmp_path / "run-two" / "raw" / "facts.jsonl").read_text(encoding="utf-8")


def test_closed_open_days_are_explicit() -> None:
    """Open days and closed days are separate states, never zero-filled."""
    rows = classify_days(
        date(2026, 9, 6), date(2026, 9, 14), closed_through=date(2026, 9, 10)
    )
    assert [row["day_state"] for row in rows] == [
        "CLOSED",
        "CLOSED",
        "CLOSED",
        "CLOSED",
        "CLOSED",
        "OPEN",
        "OPEN",
        "OPEN",
        "OPEN",
    ]
    assert all(row["evidence_status"] == "NOT_INFERRED_FROM_ABSENCE" for row in rows)


def test_read_only_legacy_command_cannot_select_mutation_ops() -> None:
    """The compatibility command is fixed to collect mode and has no writes."""
    command = build_legacy_command(_contract(Path("C:/tmp"), "run-one"), _args())
    assert "--mode" in command
    assert command[command.index("--mode") + 1] == "collect"
    rendered = " ".join(command)
    assert not any(operation in rendered for operation in MUTATION_WRITE_OPS)


def test_missing_credentials_fails_closed() -> None:
    """The collector refuses to start when DB credentials are unavailable."""
    with pytest.raises(CredentialsUnavailableError):
        require_credentials({})


def test_direct_entrypoint_works_from_arbitrary_cwd(tmp_path: Path) -> None:
    """The portable file entrypoint resolves imports from itself, not CWD."""
    script = (
        Path(__file__).resolve().parents[4]
        / "scripts"
        / "wb_api_readonly_ops"
        / "collect"
        / "portable.py"
    )
    env = os.environ.copy()
    env["POSTGRES_USER"] = "test-user"
    env["POSTGRES_PASSWORD"] = "test-password"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--client",
            "A1",
            "--period",
            "2026-09-06..2026-09-14",
            "--run-id",
            "preflight-arbitrary-cwd",
            "--output-dir",
            str(tmp_path / "output"),
            "--shop-id",
            "test-shop",
            "--preflight-only",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_second_worktree_entrypoint_works_from_arbitrary_cwd(
    tmp_path: Path,
) -> None:
    """A sibling worktree exposes the same portable contract."""
    repository = Path(__file__).resolve().parents[4]
    sibling = repository.parent / "script-2"
    script = sibling / "scripts" / "wb_api_readonly_ops" / "collect" / "portable.py"
    if not script.is_file():
        pytest.skip("the sibling worktree is not checked out with the collector yet")
    env = os.environ.copy()
    env["POSTGRES_USER"] = "test-user"
    env["POSTGRES_PASSWORD"] = "test-password"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--client",
            "A1",
            "--period",
            "2026-09-06..2026-09-14",
            "--run-id",
            "preflight-second-worktree",
            "--output-dir",
            str(tmp_path / "output"),
            "--shop-id",
            "test-shop",
            "--preflight-only",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_legacy_file_entrypoint_help_works_from_arbitrary_cwd(tmp_path: Path) -> None:
    """The existing direct run.py entrypoint remains CWD-independent."""
    repository = Path(__file__).resolve().parents[4]
    script = repository / "scripts" / "wb_api_readonly_ops" / "run.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--mode" in result.stdout
