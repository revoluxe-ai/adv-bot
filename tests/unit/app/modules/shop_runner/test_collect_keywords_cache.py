"""Поведение _collect_keywords: только Redis, miss → ошибка."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.modules.shop_runner.required_data_miss import (
    ShopRunnerKeywordsCacheMissError,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_keywords_raises_on_cache_miss() -> None:
    adv = MagicMock()
    adv.shop_id = "shop-1"
    adv.adv_id = 99
    adv.get_keywords = AsyncMock(
        side_effect=ShopRunnerKeywordsCacheMissError(
            "calculated_keywords cache miss shop_id=shop-1 adv_id=99",
            shop_id="shop-1",
            adv_id=99,
        )
    )

    with pytest.raises(ShopRunnerKeywordsCacheMissError, match="cache miss"):
        await WBShopDataManager._collect_keywords(adv)

    adv.get_keywords.assert_awaited_once_with()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_keywords_returns_redis_hit() -> None:
    kw = MagicMock()
    adv = MagicMock()
    adv.shop_id = "shop-1"
    adv.adv_id = 99
    adv.get_keywords = AsyncMock(return_value=[kw])

    mock_adapter = MagicMock()
    mock_adapter.shadow_log_keywords_delta = AsyncMock()

    with patch(
        "app.snapshot_data_updater.adapters.wb_adv_dto_adapter.WBAdvDtoSnapshotAdapter",
        return_value=mock_adapter,
    ):
        result = await WBShopDataManager._collect_keywords(adv)

    assert result == [kw]
    adv.get_keywords.assert_awaited_once_with()
    mock_adapter.shadow_log_keywords_delta.assert_awaited_once_with(
        "shop-1", 99, legacy_count=1
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_collect_keywords_returns_keywords_when_shadow_fails() -> None:
    """Успешный get_keywords не теряется при падении shadow_log."""
    from app.snapshot_data_updater.adapters.wb_adv_dto_adapter import (
        WBAdvDtoSnapshotAdapter,
    )
    from app.snapshot_data_updater.config import SnapshotUpdaterConfig

    kw = MagicMock()
    adv = MagicMock()
    adv.shop_id = "shop-1"
    adv.adv_id = 99
    adv.get_keywords = AsyncMock(return_value=[kw])

    reader = MagicMock()
    reader.get_adv_snapshot = AsyncMock(side_effect=RuntimeError("shadow broken"))
    adapter = WBAdvDtoSnapshotAdapter(
        reader=reader,
        config=SnapshotUpdaterConfig(wb_adv_dto_shadow_compare=True),
    )

    with patch(
        "app.snapshot_data_updater.adapters.wb_adv_dto_adapter.WBAdvDtoSnapshotAdapter",
        return_value=adapter,
    ):
        result = await WBShopDataManager._collect_keywords(adv)

    assert result == [kw]

