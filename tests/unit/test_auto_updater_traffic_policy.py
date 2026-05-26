"""Unit-тесты хелперов ``auto_updater_traffic_policy`` (реализация — не в module docstring)."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.auto_updater_traffic_policy import (
    ShelfTrafficInfluenceMode,
    keyword_passes_shelf_conversion_gate,
    resolve_shelf_traffic_influence_mode,
    shelf_conversion_filter_applies,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    TrafficClicksDTO,
)


@pytest.mark.unit
def test_resolve_shelf_traffic_influence_mode() -> None:
    assert resolve_shelf_traffic_influence_mode(None) == ShelfTrafficInfluenceMode.UNKNOWN
    assert (
        resolve_shelf_traffic_influence_mode(
            TrafficClicksDTO(organic_clicks=10, shelf_clicks=5, keyword_clicks=1)
        )
        == ShelfTrafficInfluenceMode.ORGANIC_DOMINANT
    )
    assert (
        resolve_shelf_traffic_influence_mode(
            TrafficClicksDTO(organic_clicks=5, shelf_clicks=10, keyword_clicks=1)
        )
        == ShelfTrafficInfluenceMode.SHELF_DOMINANT
    )
    assert (
        resolve_shelf_traffic_influence_mode(
            TrafficClicksDTO(organic_clicks=7, shelf_clicks=7, keyword_clicks=1)
        )
        == ShelfTrafficInfluenceMode.SHELF_DOMINANT
    )


@pytest.mark.unit
def test_shelf_conversion_filter_applies_only_shelf_dominant() -> None:
    assert shelf_conversion_filter_applies(ShelfTrafficInfluenceMode.SHELF_DOMINANT)
    assert not shelf_conversion_filter_applies(ShelfTrafficInfluenceMode.ORGANIC_DOMINANT)
    assert not shelf_conversion_filter_applies(ShelfTrafficInfluenceMode.UNKNOWN)


@pytest.mark.unit
def test_keyword_passes_shelf_conversion_gate_postulates() -> None:
    """При SHELF_DOMINANT — только True; при ORGANIC_DOMINANT — фильтр не применяется."""
    mode_shelf = ShelfTrafficInfluenceMode.SHELF_DOMINANT
    assert keyword_passes_shelf_conversion_gate(True, mode=mode_shelf)
    assert not keyword_passes_shelf_conversion_gate(False, mode=mode_shelf)
    assert not keyword_passes_shelf_conversion_gate(None, mode=mode_shelf)

    mode_org = ShelfTrafficInfluenceMode.ORGANIC_DOMINANT
    assert keyword_passes_shelf_conversion_gate(True, mode=mode_org)
    assert keyword_passes_shelf_conversion_gate(False, mode=mode_org)
    assert keyword_passes_shelf_conversion_gate(None, mode=mode_org)
