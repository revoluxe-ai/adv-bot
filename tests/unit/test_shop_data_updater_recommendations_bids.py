"""Unit-тесты извлечения recommendations bid для Redis-кэша auto shelf."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.common_slaves.wildberries.shops_data_updater import ShopDataUpdater

pytestmark = pytest.mark.unit


def _adv(*, adv_type: int, advert_id: int, bids_map: dict[int, int] | None) -> SimpleNamespace:
    data: dict[str, object] = {
        "type": adv_type,
        "advertId": advert_id,
        "autoParams": {"active": {"recom": True, "search": False, "booster": False, "carousel": False}},
    }
    if bids_map is not None:
        data["recommendationsBidsByNmidKopecks"] = bids_map
    return SimpleNamespace(type=adv_type, advertId=advert_id, data=data)


def test_extract_auto_recommendations_bids_type_8() -> None:
    adv = _adv(adv_type=8, advert_id=100, bids_map={10749810: 350})

    result = ShopDataUpdater._extract_auto_recommendations_bids(adv)  # noqa: SLF001

    assert result == {10749810: 350}


def test_extract_auto_recommendations_bids_type_9() -> None:
    """Manual Auto-РК (type=9) тоже должны попадать в кэш ставок полок."""
    adv = _adv(adv_type=9, advert_id=32824944, bids_map={10749810: 420})

    result = ShopDataUpdater._extract_auto_recommendations_bids(adv)  # noqa: SLF001

    assert result == {10749810: 420}


def test_extract_auto_recommendations_bids_skips_unsupported_type() -> None:
    adv = _adv(adv_type=6, advert_id=200, bids_map={111: 100})

    result = ShopDataUpdater._extract_auto_recommendations_bids(adv)  # noqa: SLF001

    assert result == {}


def test_extract_auto_recommendations_bids_skips_non_positive() -> None:
    adv = _adv(adv_type=9, advert_id=32824944, bids_map={10749810: 0, 222: -1})

    result = ShopDataUpdater._extract_auto_recommendations_bids(adv)  # noqa: SLF001

    assert result == {}


@pytest.mark.asyncio
async def test_cache_auto_recommendations_bids_writes_type_9_auto_adv() -> None:
    cache_manager = AsyncMock()
    updater = ShopDataUpdater(
        wb_api=SimpleNamespace(wb_cabinet=SimpleNamespace(shop_id="shop-1")),
        auto_recommendations_bid_cache_manager=cache_manager,
    )
    adv = _adv(adv_type=9, advert_id=32824944, bids_map={10749810: 500})

    await updater._cache_auto_recommendations_bids([adv])  # noqa: SLF001

    cache_manager.set_bids.assert_awaited_once_with(32824944, {10749810: 500})
