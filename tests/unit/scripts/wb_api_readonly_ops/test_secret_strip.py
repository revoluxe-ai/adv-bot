"""Unit: secret-strip для L0 archive."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from scripts.wb_api_readonly_ops.archive import write_l0_archive
from scripts.wb_api_readonly_ops.models import (
    FamilyName,
    FamilyResult,
    FamilyStatus,
    Mode,
    OverallStatus,
    RunReport,
)
from scripts.wb_api_readonly_ops.secret_strip import strip_secrets


def test_strip_secrets_redacts_token_fields() -> None:
    """token / Authorization / cookie не остаются в plain text."""
    raw = {
        "Authorization": "Bearer super-secret-token",
        "nested": {"api_key": "abc123", "ok": 1},
        "note": "Bearer leaked-value-here",
        "cookie": "session=xyz",
    }
    cleaned = strip_secrets(raw)
    assert cleaned["Authorization"] == "***REDACTED***"
    assert cleaned["nested"]["api_key"] == "***REDACTED***"
    assert cleaned["nested"]["ok"] == 1
    assert "leaked-value-here" not in cleaned["note"]
    assert cleaned["cookie"] == "***REDACTED***"


def test_archive_does_not_contain_secret_plaintext(tmp_path: Path) -> None:
    """Zip/report после secret-strip не содержит Bearer token."""
    report = RunReport(
        mode=Mode.PREFLIGHT,
        shop_id="shop-1",
        overall_status=OverallStatus.PARTIAL,
        families=[
            FamilyResult(
                family=FamilyName.ADS,
                status=FamilyStatus.OK,
                payload={
                    "Authorization": "Bearer SECRETTOKENVALUE",
                    "adv_ids": [1],
                },
            )
        ],
        ceiling_max_seconds=10,
        ceiling_max_calls=4,
        ceiling_calls_used=1,
        ceiling_exhausted=False,
    )
    path, digest = write_l0_archive(report, output_dir=tmp_path)
    assert path.exists()
    assert len(digest) == 64
    blob = path.read_bytes()
    assert b"SECRETTOKENVALUE" not in blob
    report_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    assert "SECRETTOKENVALUE" not in report_text
    assert "***REDACTED***" in report_text
