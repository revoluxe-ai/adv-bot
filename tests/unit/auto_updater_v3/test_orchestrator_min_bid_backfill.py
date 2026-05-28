"""Unit: при cache miss min_bid — backfill и повторная загрузка WBAdvDTO."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
    _load_v3_wb_context,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_v3_wb_context_retries_dto_after_min_bid_backfill() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 10749810
    complex_adv.shelf_promotion_active = False

    dto_without_bid = MagicMock()
    dto_without_bid.main_nmid = 10749810
    dto_without_bid.min_target_position = 5
    dto_without_bid.search_adv_min_bids = {}

    dto_with_bid = MagicMock()
    dto_with_bid.main_nmid = 10749810
    dto_with_bid.min_target_position = 5
    dto_with_bid.search_adv_min_bids = {10749810: 120}

    wb_manager = MagicMock()
    wb_manager.get_wb_advs_dto = AsyncMock(
        side_effect=[[dto_without_bid], [dto_with_bid]]
    )
    wb_manager.backfill_min_bids_for_adv = AsyncMock(return_value=True)

    predictor = MagicMock()
    predictor.get_keyword_bid_profiles = AsyncMock(return_value={"kw": []})

    with patch(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_predict_keywords_target_place",
        return_value=predictor,
    ):
        dto, profiles = await _load_v3_wb_context(
            complex_adv, wb_shop_data_manager=wb_manager
        )

    assert dto is dto_with_bid
    assert profiles == {"kw": []}
    wb_manager.backfill_min_bids_for_adv.assert_awaited_once_with(complex_adv)
    assert wb_manager.get_wb_advs_dto.await_count == 2
    predictor.get_keyword_bid_profiles.assert_awaited_once_with(
        dto_with_bid, dto_with_bid.min_target_position
    )
