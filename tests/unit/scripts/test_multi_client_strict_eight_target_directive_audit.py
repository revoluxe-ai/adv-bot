"""Unit tests for the generic eight-target directive audit collector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from scripts.multi_client_strict_eight_target_directive_audit import (
    Identity,
    Target,
    _aggregate_store,
    _build_audit,
    _parse_target,
)


def test_target_parser_keeps_explicit_mapping() -> None:
    """Target syntax must preserve Auto/Search mapping IDs."""
    assert _parse_target("1256595631") == Target(1256595631)
    assert _parse_target("1285392243:1151722170:40252178:40252183:40235423") == Target(
        1285392243, 1151722170, 40252178, 40252183, 40235423
    )


def test_store_window_is_closed_only_and_unclamped() -> None:
    """DRR headroom uses factual GMV and does not clamp negative values."""
    rows = [
        {
            "day_state": "CLOSED",
            "factual_order_value": "1000",
            "gross_ad_spend": "150",
        }
        for _ in range(3)
    ]
    result = _aggregate_store(rows, 3)
    assert result["status"] == "AVAILABLE"
    assert result["store_drr_percent"] == 15.0
    assert result["unclamped_headroom_to_8_percent_rub"] == -210.0


def test_missing_metrics_are_not_zero(tmp_path: Path) -> None:
    """Missing source rows remain GAP and never become factual zero."""
    package = tmp_path / "package"
    package.mkdir()
    (package / "01_STORE.csv").write_text(
        "day_state,sales,gross_ad_spend\nCLOSED,,\n", encoding="utf-8"
    )
    (package / "02_CAMPAIGNS_CURRENT.csv").write_text(
        "nm_id,campaign_type\n1285392243,Auto\n", encoding="utf-8"
    )
    result = _build_audit(
        package,
        Identity("shop", 573, "Europe/Moscow"),
        [Target(index) for index in range(1, 9)],
    )
    assert result["closed_only_windows"]["3d"]["status"] == "GAP"
    assert result["stock"]["missing_is_not_zero"] is True
    json.dumps(result)
