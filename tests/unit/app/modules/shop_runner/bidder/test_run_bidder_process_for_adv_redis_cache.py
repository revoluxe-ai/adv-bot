"""Юнит-тесты: bidder пишет last_views и stamp в Redis (fakeredis + DI)."""

from __future__ import annotations

import datetime
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from dependency_injector import providers
from fakeredis.aioredis import FakeRedis

from app.core.di import DIManager
from app.core.di.app_container import AppContainer
from app.core.redis_manager_v2.redis_client import RedisClient
from app.core.wb_api.data_classes.advs.auction_adv import AuctionAdv
from app.modules.shop_runner.bidder import bidder_func
from app.modules.shop_runner.bidder.bidder_func import run_bidder_process_for_adv
from tests.factories.keyword_pipeline import HardStatus, make_calculated_keyword

if "matplotlib" not in sys.modules:
    try:
        import matplotlib  # noqa: F401
    except ModuleNotFoundError:
        sys.modules["matplotlib"] = MagicMock()


def make_auction_adv(bid: int, advert_id: int, nmid: int) -> AuctionAdv:
    adv_data = {
        "auction_multibids": [{"bid": bid}],
        "status": 9,
        "advertId": advert_id,
        "type": 9,
        "autoParams": {
            "active": {"booster": False, "carousel": False, "recom": False},
            "subject": {"id": 1, "name": "subject"},
            "nms": [nmid],
        },
        "unitedParams": [
            {
                "searchCPM": bid,
                "subject": {"id": 1, "name": "subject"},
                "nms": [nmid],
            }
        ],
        "name": "test",
        "dailyBudget": 1000,
        "startTime": "2025-01-01T00:00:00",
        "endTime": "2025-01-02T00:00:00",
        "createTime": "2025-01-01T00:00:00",
        "changeTime": "2025-01-01T00:00:00",
    }
    return AuctionAdv(adv_data)


def _last_views_key(keyword_id: int) -> str:
    return f"last_views_on_bidder:{keyword_id}"


def _stamp_key(keyword_id: int) -> str:
    return f"last_keyword_stamp_timestamp_cache:{keyword_id}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_bidder_process_for_adv_stores_redis_values(
    fake_redis: FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bidder сохраняет total_views и timestamp ключевого слова в Redis-кэши."""
    monkeypatch.setattr(
        "app.core.di.databases.redis.RedisLifecycle.init",
        AsyncMock(return_value=None),
    )

    di_manager = await DIManager.create(AppContainer)
    async with di_manager as app_container:
        fake_redis_client = RedisClient(redis_client=fake_redis)

        app_container.settings.override(providers.Object(Mock()))
        app_container.redis_client.override(providers.Object(fake_redis))
        app_container.redis_client_wrapper.override(providers.Object(fake_redis_client))

        try:
            redis_last_views_cache = (
                app_container.module_resources.bidder_container.redis_last_total_views()
            )
            stamp_cache = (
                app_container.module_resources.bidder_container.last_keyword_stamp_timestamp_cache()
            )

            expected_timestamp = datetime.datetime(
                2025, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
            )
            best_keyword = make_calculated_keyword(
                hard_status=HardStatus.WHITELIST,
                total_views=150,
                final_rating=100.0,
                last_keyword_stat_updated=expected_timestamp,
            )
            keywords = [
                best_keyword,
                make_calculated_keyword(
                    hard_status=HardStatus.WHITELIST,
                    total_views=100,
                    final_rating=50.0,
                ),
                make_calculated_keyword(
                    hard_status=HardStatus.WHITELIST,
                    total_views=50,
                    final_rating=25.0,
                ),
            ]

            monkeypatch.setattr(
                bidder_func,
                "_update_and_get_advs_from_wb",
                AsyncMock(return_value=[make_auction_adv(100, 111, 555)]),
            )
            monkeypatch.setattr(
                bidder_func.data_manager,
                "get_best_keyword",
                Mock(return_value=best_keyword),
            )

            adv_setting = SimpleNamespace(
                adv_id=111,
                bidder_for_auto=True,
                search_adv_id=None,
                max_cpm=150,
                nmids=[555],
                bidder_step=5,
                max_place=10,
                reset_place=False,
                id=1,
            )

            wb_api = SimpleNamespace(
                shop_id="89798uksljhkhk",
                access=SimpleNamespace(wb_cabinet=SimpleNamespace(id=1000)),
                update_cpm=AsyncMock(),
            )

            await run_bidder_process_for_adv(adv_setting, wb_api, keywords)

            assert await redis_last_views_cache.get(best_keyword) == 150
            stamp = await stamp_cache.get(best_keyword)
            assert stamp == expected_timestamp

            assert await fake_redis.exists(
                _last_views_key(best_keyword.keyword_setting_original_id)
            )
            assert await fake_redis.exists(
                _stamp_key(best_keyword.keyword_setting_original_id)
            )
        finally:
            app_container.redis_client_wrapper.reset_override()
            app_container.redis_client.reset_override()
            app_container.settings.reset_override()
