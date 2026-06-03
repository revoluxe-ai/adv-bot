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
def test_plan_mode_cap_down_only_inside_normal_branch() -> None:
    """``plan_mode_cap_down`` не вызывается до ветки ``CampaignMode.NORMAL``."""
    source = _ORCHESTRATOR.read_text(encoding="utf-8")
    cap_call = "plan_mode_cap_down("
    normal_marker = "elif campaign_mode == CampaignMode.NORMAL"
    no_data_marker = "if campaign_mode == CampaignMode.NO_DATA"
    sync_marker = "contexts, all_contexts, preamble_hard_status_sync_count = ("
    filter_marker = "operable_before = len(filter_operable_v3_contexts(all_contexts))"

    assert cap_call in source
    assert normal_marker in source
    assert no_data_marker in source
    assert sync_marker in source
    assert filter_marker in source

    normal_idx = source.index(normal_marker)
    no_data_idx = source.index(no_data_marker)
    cap_idx = source.index(cap_call)
    sync_idx = source.index(sync_marker)
    filter_idx = source.index(filter_marker)

    assert filter_idx < sync_idx < no_data_idx < normal_idx < cap_idx
    assert cap_call not in source[:normal_idx]


@pytest.mark.unit
def test_hard_status_sync_before_mode_cap_down_in_normal() -> None:
    """Filter/sync preamble общий для NO_DATA/NORMAL; cap_down — только NORMAL."""
    source = _ORCHESTRATOR.read_text(encoding="utf-8")
    sync_idx = source.index("contexts, all_contexts, preamble_hard_status_sync_count = (")
    cap_idx = source.index("plan_mode_cap_down(")
    assert sync_idx < cap_idx
