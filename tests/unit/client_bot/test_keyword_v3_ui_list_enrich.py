"""Enrich CH-профиля для буквы режима в списке V3 (без ladder-sort)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.services.keyword_v3_ui_sort import (
    enrich_keywords_v3_list_profiles,
)
from app.client_bot.user_interface.views.keyword_strategy_ui import (
    keyword_strategy_letter,
)
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enrich_keywords_v3_list_profiles_sets_letter_o() -> None:
    """После enrich ключ с CH-матрицей получает букву режима, не tier ``N``."""
    adv_setting = MagicMock()
    adv_setting.adv_id = 100
    adv_setting.wb_cabinet_id = 1
    adv_setting.nmids = [123]
    adv_setting.min_target_position = None

    keyword = MagicMock()
    keyword.keyword_setting_original_id = 5
    keyword.text = "крем"
    keyword.position_profile = None
    keyword.pay_for_order = 10.0
    keyword.strategy_mode = KeywordStrategyMode.OFF

    profile = [MagicMock()]
    enriched_kw = MagicMock()
    enriched_kw.strategy_mode = KeywordStrategyMode.OFF
    enriched_kw.position_profile = profile

    wb_cabinet = MagicMock()
    wb_cabinet.shop_id = "shop-1"

    min_bids = MagicMock()
    min_bids.search = {123: 50}
    hub = MagicMock()
    hub.wb_manager.get_min_bids_cache_only = AsyncMock(return_value=min_bids)
    factory = MagicMock()
    factory.get_wb_manager_hub.return_value = hub
    container = MagicMock()
    container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory.return_value = (
        factory
    )
    di_cm = AsyncMock()
    di_cm.__aenter__ = AsyncMock(return_value=container)
    di_cm.__aexit__ = AsyncMock(return_value=None)
    predictor = MagicMock()
    predictor.load_bid_profiles_for_nmid = AsyncMock(return_value={"крем": []})

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
            new=AsyncMock(return_value=di_cm),
        ),
        patch(
            "app.client_bot.user_interface.services.keyword_v3_ui_sort.build_predict_keywords_target_place",
            return_value=predictor,
        ),
        patch(
            "app.client_bot.user_interface.services.keyword_v3_ui_sort.merge_position_profiles_from_contexts",
            return_value=[enriched_kw],
        ) as merge_mock,
        patch(
            "app.client_bot.user_interface.services.keyword_v3_ui_sort.build_keyword_v3_contexts",
            return_value=[MagicMock()],
        ),
        patch(
            "app.modules.wb_adv_updater.keywords_access.fetch_keywords_from_database",
            new=AsyncMock(),
        ) as fetch_db,
    ):
        result = await enrich_keywords_v3_list_profiles(adv_setting, [keyword])

    fetch_db.assert_not_awaited()
    merge_mock.assert_called_once()
    assert keyword_strategy_letter(result[0]) == "o"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enrich_keywords_v3_list_profiles_returns_unchanged_on_min_bids_fail() -> (
    None
):
    """При недоступности min_bids список не ломается — без enrich."""
    adv_setting = MagicMock()
    adv_setting.adv_id = 1
    adv_setting.wb_cabinet_id = 1
    adv_setting.nmids = [1]
    adv_setting.min_target_position = None

    keyword = MagicMock()
    keyword.position_profile = None
    keyword.pay_for_order = 5.0
    keywords = [keyword]

    wb_cabinet = MagicMock()
    wb_cabinet.shop_id = "s"

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
            new=AsyncMock(side_effect=RuntimeError("no hub")),
        ),
    ):
        result = await enrich_keywords_v3_list_profiles(adv_setting, keywords)

    assert result is keywords
