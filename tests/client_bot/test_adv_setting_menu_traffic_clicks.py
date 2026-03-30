from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.client_bot.user_interface.views.messages.main_adv_setting_menu.adv_setting_menu import (
    AdvSettingMenu,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    TrafficClicksDTO,
)


@pytest.mark.asyncio
async def test_get_today_traffic_clicks_dto_returns_none_when_rec_mode_disabled() -> None:
    menu = AdvSettingMenu.__new__(AdvSettingMenu)
    menu.adv = SimpleNamespace(rec_system_mode=False)

    result = await menu._get_today_traffic_clicks_dto()
    assert result is None


@pytest.mark.asyncio
async def test_get_today_traffic_clicks_dto_returns_values_when_rec_mode_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    menu = AdvSettingMenu.__new__(AdvSettingMenu)
    menu.adv = SimpleNamespace(
        rec_system_mode=True,
        adv_id=123,
        nmids=[1, 2],
        search_adv_id=None,
        plan_for_sales_for_day=1,
        target_price_for_order=100,
        max_price_for_order=200,
    )

    from app.modules.shop_runner.service_manager.services.traffic_clicks_manager import (
        TrafficClicksManager,
    )

    async def _enrich(adv) -> None:
        adv.traffic_clicks_dto = TrafficClicksDTO(
            organic_clicks=70,
            shelf_clicks=70,
            keyword_clicks=30,
        )

    monkeypatch.setattr(TrafficClicksManager, "enrich", AsyncMock(side_effect=_enrich))

    dto = await menu._get_today_traffic_clicks_dto()

    assert dto is not None
    assert dto.keyword_clicks == 30
    assert dto.shelf_clicks == 70
    assert dto.organic_clicks == 70


def test_adv_setting_cashback_compact_line_is_short_and_informative() -> None:
    line = AdvSettingMenu._build_cashback_compact_line(  # type: ignore[attr-defined]
        {
            "cashbacks_total": 143497,
            "cashbacks_best_percent": 50,
            "cashbacks_earliest_expiration": "2026-04-03T21:00:00Z",
        }
    )

    assert line is not None
    assert line.startswith("КБ:")
    assert "143497" in line
    assert "50%" in line
    assert len(line) < 40
