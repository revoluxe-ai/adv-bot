import asyncio
import logging
from typing import (
    TypeVar,
)

from .modules.wb_api import WBApi
from .shop_run_worker.redis_manager import RedisShopManager

logger = logging.getLogger(__name__)
from .service_manager import CoroutinesManager

T = TypeVar("T")


class WBShop:
    def __init__(self, wb_api: WBApi, redis_manager: RedisShopManager):
        self._wb_api = wb_api
        self._redis_manager = redis_manager

    async def run(self) -> None:
        wb_api = self._wb_api
        coroutines_manager = CoroutinesManager(wb_api)

        # TODO: !!! Надо еще добавить проверку на что отключено что включено из автоматизации в новой верссии  и добавить кнопку управления
        #  автоэкспонентой, и именить тарификацию за автоматизацию, т.к. теперь управляющих сущности три

        await asyncio.gather(
            self._alive_worker_run(),
            coroutines_manager.update_advs_data_from_wb_to_pg(),
            coroutines_manager.update_cards_data_from_wb_to_pg(),
            coroutines_manager.update_cpm_bid(),
            coroutines_manager.update_common_sale_stat(),
            coroutines_manager.update_full_adv_stat(),
            coroutines_manager.adv_settings_auto_update(),
            coroutines_manager.update_top_key_in_advs(),
            # TODO: Отключил обновление Джема, т.к. выкидывает ошибку и мешает работе тем юзерам, у которых джема нет
            # coroutines_manager.update_keywords_stamp(),
            # coroutines_manager.update_keywords_positions_history(),
            coroutines_manager.delete_keywords_from_wl_by_mean_auto_ctr(),
            coroutines_manager.update_minus_phrases_in_advs(),
            coroutines_manager.update_clusters_adv_stats_today(),
            coroutines_manager.update_clusters_adv_stats_history()
        )

        # TODO: Перенести PV кликхаус на более маленький диск

    async def _alive_worker_run(self) -> None:
        redis_manager: RedisShopManager = self._redis_manager
        ping_timeout = redis_manager.DEFAULT_TTL / 2
        while True:
            await redis_manager.renew_shop_ttl(self._wb_api.shop_id)
            await asyncio.sleep(ping_timeout)

    # TODO: Сделать, чтобы run-shop-update-worker равномерно распределяли между собою нагрузки
