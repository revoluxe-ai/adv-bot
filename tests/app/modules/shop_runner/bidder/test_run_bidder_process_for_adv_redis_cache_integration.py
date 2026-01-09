import datetime
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

from tests.factories.keyword_pipeline import make_calculated_keyword, HardStatus

sys.modules.setdefault("matplotlib", MagicMock())

import pytest
from dependency_injector import providers
from fakeredis.aioredis import FakeRedis

from app.core.di import DIManager
from app.core.di.app_container import AppContainer
from app.core.redis_manager_v2.redis_client import RedisClient
from app.core.wb_api.data_classes.advs.auction_adv import AuctionAdv
from app.modules.shop_runner.bidder import bidder_func
from app.modules.shop_runner.bidder.bidder_func import run_bidder_process_for_adv
import logging

logger = logging.getLogger(__name__)



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


@pytest.mark.asyncio
async def test_run_bidder_process_for_adv_stores_redis_values(
    fake_redis: FakeRedis, monkeypatch
) -> None:
    """Проверяет что bidder сохраняет значения в Redis через RedisClient."""
    
    # Создаём DIManager для правильной инициализации контейнера
    di_manager = await DIManager.create(AppContainer)
    async with di_manager as app_container:
        # Создаём RedisClient обёртку над fake_redis
        fake_redis_client = RedisClient(redis_client=fake_redis)
        
        # Override базовых зависимостей
        app_container.settings.override(providers.Object(Mock()))
        app_container.redis_client.override(providers.Object(fake_redis))
        app_container.redis_client_wrapper.override(providers.Object(fake_redis_client))

        try:
            # Получаем redis кэши (они теперь будут использовать fake_redis_client)
            redis_last_views_cache = (
                app_container.module_resources.bidder_container.redis_last_total_views()
            )
            stamp_cache = (
                app_container.module_resources.bidder_container.last_keyword_stamp_timestamp_cache()
            )

            # Создаём keywords с явными значениями для теста
            # hard_status=2 (WHITELIST) нужен для попадания в white_list
            # total_views=150 - значение которое будет сохранено в Redis
            expected_timestamp = datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
            best_keyword = make_calculated_keyword(
                hard_status=HardStatus.WHITELIST,
                total_views=150,
                final_rating=100.0,
                last_keyword_stat_updated=expected_timestamp,
            )
            keywords = [
                best_keyword,
                make_calculated_keyword(hard_status=HardStatus.WHITELIST, total_views=100, final_rating=50.0),
                make_calculated_keyword(hard_status=HardStatus.WHITELIST, total_views=50, final_rating=25.0),
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
                shop_id='89798uksljhkhk',
                access=SimpleNamespace(wb_cabinet=SimpleNamespace(id=1000)),
                update_cpm=AsyncMock(),
            )

            await run_bidder_process_for_adv(adv_setting, wb_api, keywords)

            # Проверяем что значения сохранены в кэшах
            assert await redis_last_views_cache.get(best_keyword) == 150
            stamp = await stamp_cache.get(best_keyword)
            assert stamp == expected_timestamp

            # Проверяем что ключи существуют в Redis (формат не важен, главное что сохранено)
            assert await fake_redis.exists(_last_views_key(best_keyword.keyword_setting_original_id))
            assert await fake_redis.exists(_stamp_key(best_keyword.keyword_setting_original_id))
        except Exception:
            logger.error('', exc_info=True)
            raise
        finally:
            # Сброс overrides
            app_container.redis_client_wrapper.reset_override()
            app_container.redis_client.reset_override()
            app_container.settings.reset_override()


