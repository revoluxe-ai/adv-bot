import asyncio
import logging
from typing import TypeVar

from app.core.redis_manager_v2.redis_client import RedisClient
from .modules.wb_api import WBApi

import typing


if typing.TYPE_CHECKING:
    from .service_manager.services.plan_fact_controller.plan_fact_reader import PlanFactReader

from .shop_run_worker.redis_manager import RedisShopManager
from .service_manager import CoroutinesManager
from .tasks_manager.tasks_manager import TasksManager

logger = logging.getLogger(__name__)
T = TypeVar("T")


class WBShop:
    def __init__(
        self,
        wb_api: WBApi,
        redis_manager: RedisShopManager,
        redis_client_wrapper: RedisClient,
        tasks_manager: TasksManager,
        plan_fact_reader: "PlanFactReader",
    ):
        self._wb_api = wb_api
        self._redis_manager = redis_manager
        self._redis_client_wrapper = redis_client_wrapper
        self._tasks_manager = tasks_manager
        self._plan_fact_reader = plan_fact_reader

    async def run(self) -> None:
        from .service_manager.exc import StopShopUpdateException
        wb_api = self._wb_api
        coroutines_manager = CoroutinesManager(
            wb_api,
            self._redis_client_wrapper,
            tasks_manager=self._tasks_manager,
            plan_fact_reader=self._plan_fact_reader,
        )
        # TODO: Записи статистики идут в базу не одним батчем, это про общую или рекламную, исправить
        # TODO: !!! Надо еще добавить проверку на что отключено что включено из автоматизации в новой верссии  и добавить кнопку управления
        #  автоэкспонентой, и именить тарификацию за автоматизацию, т.к. теперь управляющих сущности три
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._alive_worker_run())
                tg.create_task(coroutines_manager.update_advs_data_from_wb_to_pg())
                tg.create_task(coroutines_manager.update_cards_data_from_wb_to_pg())
                tg.create_task(coroutines_manager.update_cpm_bid())
                tg.create_task(coroutines_manager.update_common_sale_stat())
                tg.create_task(coroutines_manager.update_full_adv_stat())
                tg.create_task(coroutines_manager.adv_settings_auto_update())
                tg.create_task(
                    coroutines_manager.delete_keywords_from_wl_by_mean_auto_ctr()
                )
                tg.create_task(coroutines_manager.update_minus_phrases_in_advs())
                tg.create_task(coroutines_manager.update_clusters_adv_stats_today())
                tg.create_task(
                    coroutines_manager.update_clusters_adv_stats_history()
                )
                tg.create_task(coroutines_manager.update_cluster_bids())
                tg.create_task(coroutines_manager.update_plan_fact_stats())
                tg.create_task(coroutines_manager.auto_budget_watchdog())
                tg.create_task(coroutines_manager.auto_adv_active_control())
                tg.create_task(coroutines_manager.update_top_key_in_advs())
                tg.create_task(coroutines_manager.update_common_bid_in_search_adv())
                tg.create_task(coroutines_manager.auto_reset_bid_for_auto_adv())
        except* StopShopUpdateException as stop_exc:
            # Проглатываем StopShopUpdateException
            # (все StopShopUpdateException из группы соберутся сюда)
            for single in stop_exc.exceptions:
                logger.info(f"Shop update stopped: {single!r}")
            # ничего не поднимаем дальше
        except* Exception:
            # Остальные ошибки — поднимаем наружу
            # (если хочется — можно логировать детали)
            logger.error("Критические ошибки в TaskGroup (не StopShopUpdateException).")
            raise

        # TODO: Перенести PV кликхаус на более маленький диск

    async def _alive_worker_run(self) -> None:
        redis_manager: RedisShopManager = self._redis_manager
        ping_timeout = redis_manager.DEFAULT_TTL / 2
        while True:
            await redis_manager.renew_shop_ttl(self._wb_api.shop_id)
            await asyncio.sleep(ping_timeout)

    # TODO: Сделать, чтобы run-shop-update-worker равномерно распределяли между собою нагрузки
