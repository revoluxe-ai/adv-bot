from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.shop_runner.service_manager.services.traffic_clicks_manager import (
    TrafficClicksManager,
)


@pytest.mark.asyncio
async def test_enrich_sets_none_when_rec_mode_disabled() -> None:
    adv = SimpleNamespace(
        rec_system_promotion_mode_active=False,
        traffic_clicks_dto="placeholder",
    )
    manager = TrafficClicksManager()
    await manager.enrich(adv)
    assert adv.traffic_clicks_dto is None


@pytest.mark.asyncio
async def test_enrich_fills_clicks_dto(monkeypatch: pytest.MonkeyPatch) -> None:
    adv = SimpleNamespace(
        rec_system_promotion_mode_active=True,
        adv_id=123,
        all_adv_ids={123, 456},
        nmids=[111, 222],
        traffic_clicks_dto=None,
    )
    from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
    from app.modules.shop_runner.wb_statistic_manager.backend import common_stat_manager

    monkeypatch.setattr(
        full_wb_adv_stat, "get_auto_total_clicks_today", AsyncMock(return_value=100)
    )
    monkeypatch.setattr(
        full_wb_adv_stat,
        "get_keywords_clicks_and_views",
        AsyncMock(return_value=(30, 999)),
    )
    monkeypatch.setattr(
        full_wb_adv_stat,
        "get_stats_by_last_days",
        AsyncMock(return_value=SimpleNamespace(clicks=130)),
    )
    monkeypatch.setattr(
        common_stat_manager, "get_today_funnel_clicks", AsyncMock(return_value=210)
    )

    manager = TrafficClicksManager()
    await manager.enrich(adv)

    assert adv.traffic_clicks_dto is not None
    assert adv.traffic_clicks_dto.keyword_clicks == 30
    assert adv.traffic_clicks_dto.shelf_clicks == 70
    assert adv.traffic_clicks_dto.organic_clicks == 80


@pytest.mark.asyncio
async def test_enrich_clamps_negative_values(monkeypatch: pytest.MonkeyPatch) -> None:
    adv = SimpleNamespace(
        rec_system_promotion_mode_active=True,
        adv_id=123,
        all_adv_ids={123},
        nmids=[111],
        traffic_clicks_dto=None,
    )
    from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
    from app.modules.shop_runner.wb_statistic_manager.backend import common_stat_manager

    monkeypatch.setattr(
        full_wb_adv_stat, "get_auto_total_clicks_today", AsyncMock(return_value=10)
    )
    monkeypatch.setattr(
        full_wb_adv_stat,
        "get_keywords_clicks_and_views",
        AsyncMock(return_value=(20, 0)),
    )
    monkeypatch.setattr(
        full_wb_adv_stat,
        "get_stats_by_last_days",
        AsyncMock(return_value=SimpleNamespace(clicks=50)),
    )
    monkeypatch.setattr(
        common_stat_manager, "get_today_funnel_clicks", AsyncMock(return_value=30)
    )

    manager = TrafficClicksManager()
    await manager.enrich(adv)

    assert adv.traffic_clicks_dto is not None
    assert adv.traffic_clicks_dto.shelf_clicks == 0
    assert adv.traffic_clicks_dto.organic_clicks == 0
