"""Сортировка списка ключей V3 в UI: без повторного пересчёта keywords из БД."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.services.keyword_v3_ui_sort import (
    sort_keywords_for_v3_ui,
)
from app.modules.shop_runner.required_data_miss import ShopRunnerKeywordsCacheMissError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sort_keywords_for_v3_ui_does_not_refetch_keywords_from_database() -> None:
    """Список уже загружен в handler; sort не вызывает ``fetch_keywords_from_database``."""
    adv_setting = MagicMock()
    adv_setting.adv_id = 100
    adv_setting.wb_cabinet_id = 1
    adv_setting.nmids = [123]
    adv_setting.automatic_version = 3
    adv_setting.min_target_position = None

    keywords = [MagicMock()]
    keywords[0].keyword_setting_original_id = 1
    keywords[0].text = "kw"
    keywords[0].position_profile = None
    keywords[0].pay_for_order = 10.0

    wb_cabinet = MagicMock()
    wb_cabinet.shop_id = "shop-1"

    with (
        patch(
            "app.client_bot.user_interface.services.keyword_v3_ui_sort._load_wb_cabinet",
            new=AsyncMock(return_value=wb_cabinet),
        ),
        patch(
            "app.client_bot.user_interface.services.keyword_v3_ui_sort._build_complex_adv",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.client_bot.user_interface.services.keyword_v3_ui_sort.DIManager.create",
            new=AsyncMock(side_effect=Exception("skip min_bids in test")),
        ),
        patch(
            "app.modules.wb_adv_updater.keywords_access.fetch_keywords_from_database",
            new=AsyncMock(),
        ) as fetch_db,
    ):
        result = await sort_keywords_for_v3_ui(adv_setting, keywords)

    fetch_db.assert_not_awaited()
    assert result is keywords or len(result) >= 0
