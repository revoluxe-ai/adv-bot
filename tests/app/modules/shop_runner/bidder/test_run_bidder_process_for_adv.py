import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from dependency_injector import providers

from app.core.di import DIManager
from app.core.di.app_container import AppContainer
from app.core.wb_api.data_classes.advs.auction_adv import AuctionAdv
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models.bidder_mode import BidderMode
from app.modules.common_slaves.wildberries.models.models import WBItemPosition
from app.modules.shop_runner.bidder import bidder_func
from app.modules.shop_runner.bidder.bidder_func import run_bidder_process_for_adv


def make_keyword() -> CalculatedKeyword:
    """Создает тестовый CalculatedKeyword с позицией."""
    keyword = CalculatedKeyword(
        text="пример",
        clicks=10,
        views=200,
        spend=5.0,
        hard_status=2,
        keyword_setting_original_id=777,
    )
    keyword.position = WBItemPosition(
        position=5,
        timestamp=datetime.datetime(2025, 1, 1, 12, 0, 0),
        total_views=150,
    )
    return keyword


def make_auction_adv(bid: int, advert_id: int, nmid: int) -> AuctionAdv:
    """Создает тестовый AuctionAdv с заданными параметрами."""
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


@pytest.mark.asyncio
async def test_run_bidder_process_for_adv_injects_auto_max_manager(monkeypatch):
    """Проверяет что auto_max_bid_manager инжектится в режиме BY_AUTO_MAX_CPM."""
    di_manager = await DIManager.create(AppContainer)
    async with di_manager as app_container:
        # Override базовых зависимостей
        app_container.settings.override(providers.Object(Mock()))
        app_container.redis_client.override(providers.Object(Mock()))
        app_container.redis_client_wrapper.override(providers.Object(Mock()))

        # Override auto_max_bid_manager
        auto_max_manager = SimpleNamespace(get_max_cpm=AsyncMock(return_value=80))
        auto_max_provider = (
            app_container.module_resources.auto_max_cpm_manager.auto_max_cpm_bid_manager
        )
        auto_max_provider.override(providers.Object(auto_max_manager))

        # Override redis кэшей
        redis_last_views = SimpleNamespace(get=AsyncMock(return_value=None), set=AsyncMock())
        redis_last_views_provider = (
            app_container.module_resources.bidder_container.redis_last_total_views
        )
        redis_last_views_provider.override(providers.Object(redis_last_views))

        stamp_cache = SimpleNamespace(get=AsyncMock(return_value=None), set=AsyncMock())
        stamp_cache_provider = (
            app_container.module_resources.bidder_container.last_keyword_stamp_timestamp_cache
        )
        stamp_cache_provider.override(providers.Object(stamp_cache))

        try:
            # Подготовка тестовых данных
            auction_adv = make_auction_adv(100, 222, 501)
            best_keyword = make_keyword()

            # Мокирование зависимостей функции
            monkeypatch.setattr(
                bidder_func,
                "_update_and_get_advs_from_wb",
                AsyncMock(return_value=[auction_adv]),
            )
            monkeypatch.setattr(
                bidder_func.data_manager,
                "get_best_keyword",
                Mock(return_value=best_keyword),
            )

            adv_setting = SimpleNamespace(
                adv_id=222,
                bidder_for_auto=True,
                search_adv_id=None,
                max_cpm=150,
                bidder_mode=BidderMode.BY_AUTO_MAX_CPM,
                auto_max_cpm_mode=True,
                nmids=[501],
                bidder_step=None,
                max_place=10,
                reset_place=False,
                id=1,
            )

            wb_api = SimpleNamespace(
                shop_id=99,
                access=SimpleNamespace(wb_cabinet=SimpleNamespace(id=1000)),
                update_cpm=AsyncMock(),
            )

            # Вызов функции
            await run_bidder_process_for_adv(adv_setting, wb_api, [best_keyword])

            # Проверка что auto_max_bid_manager был вызван
            auto_max_manager.get_max_cpm.assert_awaited_once_with(
                adv_setting, [best_keyword], adv_setting.max_cpm
            )
            # Проверка что ставка была обновлена
            wb_api.update_cpm.assert_awaited_once_with(
                adv_setting.adv_id, adv_setting.nmids[0], 80
            )
        finally:
            # Сброс overrides
            stamp_cache_provider.reset_override()
            redis_last_views_provider.reset_override()
            auto_max_provider.reset_override()
            app_container.redis_client_wrapper.reset_override()
            app_container.redis_client.reset_override()
            app_container.settings.reset_override()


@pytest.mark.asyncio
async def test_run_bidder_process_for_adv_injects_redis_caches(monkeypatch):
    """Проверяет что redis кэши инжектятся в режиме BY_POSITIONS."""
    di_manager = await DIManager.create(AppContainer)
    async with di_manager as app_container:
        # Override базовых зависимостей
        app_container.settings.override(providers.Object(Mock()))
        app_container.redis_client.override(providers.Object(Mock()))
        app_container.redis_client_wrapper.override(providers.Object(Mock()))

        # Override auto_max_bid_manager (не должен использоваться в BY_POSITIONS)
        auto_max_manager = SimpleNamespace(get_max_cpm=AsyncMock(return_value=120))
        auto_max_provider = (
            app_container.module_resources.auto_max_cpm_manager.auto_max_cpm_bid_manager
        )
        auto_max_provider.override(providers.Object(auto_max_manager))

        # Override redis кэшей (должны использоваться)
        redis_last_views = SimpleNamespace(get=AsyncMock(return_value=None), set=AsyncMock())
        redis_last_views_provider = (
            app_container.module_resources.bidder_container.redis_last_total_views
        )
        redis_last_views_provider.override(providers.Object(redis_last_views))

        stamp_cache = SimpleNamespace(get=AsyncMock(return_value=None), set=AsyncMock())
        stamp_cache_provider = (
            app_container.module_resources.bidder_container.last_keyword_stamp_timestamp_cache
        )
        stamp_cache_provider.override(providers.Object(stamp_cache))

        # Мокирование AdvParameterManager
        class DummyAdvParameterManager:
            async def get_min_cpm(self, _):
                return 1

        monkeypatch.setattr(bidder_func, "AdvParameterManager", DummyAdvParameterManager)

        try:
            # Подготовка тестовых данных
            auction_adv = make_auction_adv(100, 333, 701)
            best_keyword = make_keyword()

            # Мокирование зависимостей функции
            monkeypatch.setattr(
                bidder_func,
                "_update_and_get_advs_from_wb",
                AsyncMock(return_value=[auction_adv]),
            )
            monkeypatch.setattr(
                bidder_func.data_manager,
                "get_best_keyword",
                Mock(return_value=best_keyword),
            )

            adv_setting = SimpleNamespace(
                adv_id=333,
                bidder_for_auto=True,
                search_adv_id=444,
                max_cpm=150,
                bidder_mode=BidderMode.BY_POSITIONS,
                auto_max_cpm_mode=False,
                nmids=[701],
                bidder_step=5,
                max_place=10,
                reset_place=False,
                id=2,
            )

            wb_api = SimpleNamespace(
                shop_id=55,
                access=SimpleNamespace(wb_cabinet=SimpleNamespace(id=2000)),
                update_cpm=AsyncMock(),
            )

            # Вызов функции
            await run_bidder_process_for_adv(adv_setting, wb_api, [best_keyword])

            # Проверка что redis кэши были вызваны
            redis_last_views.get.assert_awaited_once_with(best_keyword)
            stamp_cache.get.assert_awaited_once_with(best_keyword)
            redis_last_views.set.assert_awaited_once_with(best_keyword)
            # Проверка что auto_max_bid_manager НЕ был вызван в режиме BY_POSITIONS
            auto_max_manager.get_max_cpm.assert_not_called()
            # Проверка что ставки были обновлены для обеих РК
            assert wb_api.update_cpm.await_count == 2
        finally:
            # Сброс overrides
            stamp_cache_provider.reset_override()
            redis_last_views_provider.reset_override()
            auto_max_provider.reset_override()
            app_container.redis_client_wrapper.reset_override()
            app_container.redis_client.reset_override()
            app_container.settings.reset_override()




