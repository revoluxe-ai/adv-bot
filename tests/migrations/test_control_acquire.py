"""Unit: CONTROL acquire outcomes (без реального registry/DB)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.db import control_acquire


def test_control_acquire_missing_env(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    for key in (
        "RELEASE_ID",
        "RELEASE_PLATFORM_MANIFEST_DIGEST",
        "DATABASE_URL",
        "EXPECTED_TARGET_REVISION",
        "EXPECTED_SOURCE_HISTORY_HASH",
        "WORKFLOW_RUN_ID",
        "DATABASE_IDENTITY",
    ):
        monkeypatch.delenv(key, raising=False)
    code = control_acquire.main()
    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["outcome"] == "PRECONDITION_FAILED"
    assert "RELEASE_ID" in payload["missing_env"]


def test_control_acquire_dry_run_ok(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    dig = "sha256:" + ("a" * 64)
    monkeypatch.setenv("RELEASE_ID", "rel-1")
    monkeypatch.setenv("RELEASE_PLATFORM_MANIFEST_DIGEST", dig)
    monkeypatch.setenv("EXPECTED_PLATFORM_MANIFEST_DIGEST", dig)
    monkeypatch.setenv("PROVENANCE_MODE", "digest_pin")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("EXPECTED_TARGET_REVISION", "f2a3b4c5d6e7")
    monkeypatch.setenv("EXPECTED_SOURCE_HISTORY_HASH", "interim-forensics-20260731T093353Z")
    monkeypatch.setenv("WORKFLOW_RUN_ID", "wf-1")
    monkeypatch.setenv("DATABASE_IDENTITY", "adv_updater@postgres-db")
    monkeypatch.setenv("CONTROL_DRY_RUN", "1")

    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    engine.connect.return_value.__exit__.return_value = None
    conn.execute.return_value.mappings.return_value.first.return_value = {
        "baseline_id": "b1",
        "status": "RECONCILED",
        "source_history_hash": "interim-forensics-20260731T093353Z",
    }

    with patch.object(control_acquire, "create_engine", return_value=engine):
        code = control_acquire.main()
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["outcome"] == "DRY_RUN_OK"
    assert payload["provenance"]["registry_checked"] is False


def test_control_acquire_provenance_failed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("RELEASE_ID", "rel-1")
    monkeypatch.setenv("RELEASE_PLATFORM_MANIFEST_DIGEST", "not-a-digest")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("EXPECTED_TARGET_REVISION", "f2a3b4c5d6e7")
    monkeypatch.setenv("EXPECTED_SOURCE_HISTORY_HASH", "hash")
    monkeypatch.setenv("WORKFLOW_RUN_ID", "wf-1")
    monkeypatch.setenv("DATABASE_IDENTITY", "id")
    code = control_acquire.main()
    assert code == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["outcome"] == "PROVENANCE_FAILED"
