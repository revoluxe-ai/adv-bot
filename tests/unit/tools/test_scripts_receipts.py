"""Unit tests for formal-change and SCRIPTS_REPORT receipt contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.scripts import receipts

pytestmark = pytest.mark.unit


def _formal(run_id: str = "run-1") -> dict[str, Any]:
    """Создать exact formal handoff fixture."""
    return {
        "schema_version": receipts.FORMAL_SCHEMA,
        "outcome": "FORMAL_CHANGE_REQUIRED",
        "run_id": run_id,
        "request_id": "req-1",
        "formal_type": "CREATE",
        "command": "/opsx-ff test-capability",
        "change_name": "test-capability",
        "owner_change_id": None,
        "reason": "missing",
        "evidence": [],
        "request_contract": {},
        "constraints": ["no writes"],
        "pasteable_prompt": "/opsx-ff test-capability",
        "created_at": "2026-09-18T12:00:00Z",
    }


def test_formal_change_is_persisted_under_run_receipt_path(tmp_path: Path) -> None:
    """Formal handoff is one machine-readable invocation artifact."""
    destination = receipts.persist_formal_change(tmp_path, "run-1", _formal())
    assert destination.name == "FORMAL_CHANGE_REQUIRED.json"
    assert json.loads(destination.read_text(encoding="utf-8"))["outcome"] == (
        "FORMAL_CHANGE_REQUIRED"
    )


def test_formal_receipt_redacts_credential_sentinel(tmp_path: Path) -> None:
    """Persisted formal evidence cannot contain original credential material."""
    secret = "Bearer UNIQUE-RECEIPT-SECRET-SENTINEL"
    formal = _formal()
    formal["request_contract"] = {"authorization": secret}
    formal["pasteable_prompt"] = secret
    destination = receipts.persist_formal_change(tmp_path, "run-1", formal)
    content = destination.read_text(encoding="utf-8")
    assert secret not in content
    assert "<redacted>" in content


@pytest.mark.parametrize(
    "run_id",
    ["", "../escape", "nested/run", "/absolute", "bad space", ".."],
)
def test_invocation_run_id_allowlist_rejects_traversal(run_id: str) -> None:
    """Run IDs cannot introduce separators, absolute paths, or traversal."""
    with pytest.raises(ValueError):
        receipts.validate_run_id(run_id)


def test_invocation_output_path_is_computed_inside_owned_root(tmp_path: Path) -> None:
    """Output paths are derived below the caller-owned run root."""
    output = receipts.invocation_output_path(tmp_path, "run-1", "collector")
    assert output == tmp_path / ".tmp" / "opsx-scripts" / "run-1" / "collector"


def test_invocation_output_collision_preserves_existing_directory(tmp_path: Path) -> None:
    """Existing output is blocked and never removed."""
    output = receipts.invocation_output_path(tmp_path, "run-1", "collector")
    output.mkdir(parents=True)
    sentinel = output / "keep.txt"
    sentinel.write_text("preserve", encoding="utf-8")
    with pytest.raises(ValueError, match="collision"):
        receipts.prepare_invocation_output_dir(output)
    assert sentinel.read_text(encoding="utf-8") == "preserve"


def test_symlink_escape_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run root symlink cannot redirect writes outside invocation ownership."""
    external = tmp_path / "external"
    external.mkdir()
    run_root = tmp_path / ".tmp" / "opsx-scripts"
    run_root.mkdir(parents=True)
    link = run_root / "run-1"
    try:
        link.symlink_to(external, target_is_directory=True)
    except OSError:
        monkeypatch.setattr(
            receipts,
            "_is_link_or_reparse",
            lambda path: path == link,
        )
    with pytest.raises(ValueError, match="symlink"):
        receipts.invocation_output_path(tmp_path, "run-1", "collector")


def test_report_provenance_is_additive_and_separate() -> None:
    """Caller and canonical execution identities remain separate report fields."""
    fields = receipts.scripts_report_provenance(
        {
            "caller": {"root": "caller", "branch": "refs/heads/feature", "sha": "a"},
            "canonical_worktree": {"root": "scripts"},
            "execution_sha": "b",
            "registry_sha": "c",
            "outcome": "REUSE",
            "selection": [{"registry_id": "one"}],
        }
    )
    assert fields["CALLER_BRANCH"] == "refs/heads/feature"
    assert fields["CANONICAL_WORKTREE"] == "scripts"
    assert fields["EXECUTION_SHA"] == "b"
    assert fields["REGISTRY_SHA"] == "c"
