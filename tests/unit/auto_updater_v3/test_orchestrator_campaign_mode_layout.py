"""Unit: статическая проверка взаимоисключающих campaign-веток в orchestrator."""

from __future__ import annotations

from pathlib import Path

import pytest

_ORCHESTRATOR = (
    Path(__file__).resolve().parents[3]
    / "app"
    / "modules"
    / "shop_runner"
    / "service_manager"
    / "services"
    / "auto_updater_v3"
    / "orchestrator.py"
)


@pytest.mark.unit
def test_plan_data_bootstrap_v3_only_inside_normal_branch() -> None:
    """``plan_data_bootstrap_v3`` не вызывается до ветки ``CampaignMode.NORMAL``."""
    source = _ORCHESTRATOR.read_text(encoding="utf-8")
    bootstrap_call = "plan_data_bootstrap_v3("
    campaign_opc_kw = "campaign_orders_per_cart_7d=campaign_orders_per_cart_7d"
    normal_marker = "elif campaign_mode == CampaignMode.NORMAL"
    no_data_marker = "if campaign_mode == CampaignMode.NO_DATA"

    assert bootstrap_call in source
    assert campaign_opc_kw in source
    assert normal_marker in source
    assert no_data_marker in source

    normal_idx = source.index(normal_marker)
    no_data_idx = source.index(no_data_marker)
    bootstrap_idx = source.index(bootstrap_call)

    assert no_data_idx < normal_idx < bootstrap_idx
    assert bootstrap_call not in source[:normal_idx]
    bootstrap_snippet = source[bootstrap_idx : bootstrap_idx + 200]
    assert campaign_opc_kw in bootstrap_snippet
