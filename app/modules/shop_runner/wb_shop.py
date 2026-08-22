import asyncio
import logging
from typing import TypeVar

from app.core.di.wb_manager_hub import WBManagerHub
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
        wb_manager_hub: "WBManagerHub"
    ):
        self._wb_api = wb_api
        self._redis_manager = redis_manager
        self._redis_client_wrapper = redis_client_wrapper
        self._tasks_manager = tasks_manager
        self._plan_fact_reader = plan_fact_reader
        self._wb_manager_hub = wb_manager_hub

    @property
    def shop_id(self) -> str:
        return self._wb_api.shop_id

    async def run(self) -> None:
        from .service_manager.exc import StopShopUpdateException
        wb_api = self._wb_api
        coroutines_manager = CoroutinesManager(
            wb_api,
            self._redis_client_wrapper,
            tasks_manager=self._tasks_manager,
            plan_fact_reader=self._plan_fact_reader,
            wb_manager_hub=self._wb_manager_hub
        )
        # TODO: Записи статистики идут в базу не одним батчем, это про общую или рекламную, исправить
        # TODO: !!! Надо еще добавить проверку на что отключено что включено из автоматизации в новой верссии  и добавить кнопку управления
        #  автоэкспонентой, и именить тарификацию за автоматизацию, т.к. теперь управляющих сущности три
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._alive_worker_run())
                tg.create_task(coroutines_manager.update_advs_data_from_wb_to_pg()) # Адаптировал под free
                tg.create_task(coroutines_manager.update_cards_data_from_wb_to_pg()) #  Тут вроде все и так работает под free
                tg.create_task(coroutines_manager.update_common_sale_stat(only_bot_active=False)) # Здесь поставил загрузку всех
                tg.create_task(coroutines_manager.update_full_adv_stat(only_bot_active=False)) # Здесь поставил загрузку всех
                tg.create_task(coroutines_manager.update_clusters_adv_stats_today(only_bot_active=False)) # Здесь поставил загрузку всех
                tg.create_task(
                    coroutines_manager.update_clusters_adv_stats_history(only_bot_active=False) # Здесь поставил загрузку всех
                )
                tg.create_task(coroutines_manager.refresh_stats_freshness_cache(only_bot_active=False)) # Здесь поставил загрузку всех
                tg.create_task(coroutines_manager.adv_settings_auto_update(only_bot_active=True)) # платка
                tg.create_task(coroutines_manager.update_minus_phrases_in_advs(only_bot_active=False)) # бесплатно (флаг; default off)
                tg.create_task(coroutines_manager.update_cluster_bids(only_bot_active=True)) # платка
                tg.create_task(coroutines_manager.cache_current_cluster_bids(only_bot_active=False)) # в бесплатку
                tg.create_task(coroutines_manager.preload_min_bids_cache_miss(only_bot_active=False)) # в бесплатку
                tg.create_task(coroutines_manager.preload_min_bids_cache_old(only_bot_active=False)) # в бесплатку
                tg.create_task(coroutines_manager.handle_stats_stale_emergency(only_bot_active=True)) # платка
                tg.create_task(coroutines_manager.update_plan_fact_stats(only_bot_active=False)) # в бесплатку
                # Mixed: пополнение бюджета — free (все РК с флагом); start/pause — paid
                # (gate bot_active внутри AutoAdvActiveControlService). См. docstring
                # auto_budget_watchdog и openspec paid-regression design §Coroutine matrix.
                tg.create_task(coroutines_manager.auto_budget_watchdog(only_bot_active=False))
                tg.create_task(coroutines_manager.update_top_key_in_advs(only_bot_active=True)) # платка
                tg.create_task(coroutines_manager.update_common_bid_in_search_adv(only_bot_active=True))  # платка
                tg.create_task(coroutines_manager.increment_fact_data_stats(only_bot_active=False)) # бесплатно
                tg.create_task(coroutines_manager.auto_shelf_bid_increment_stats(only_bot_active=False)) # бесплатка
                tg.create_task(coroutines_manager.auto_shelf_bid_control(only_bot_active=True)) # платка
                tg.create_task(coroutines_manager.white_list_tail_trimmer(only_bot_active=True)) # платка
                tg.create_task(coroutines_manager.auto_reset_bid_for_auto_adv(only_bot_active=True)) # платка
                tg.create_task(coroutines_manager.update_individual_keyword_target_places(only_bot_active=True)) # платка
                tg.create_task(coroutines_manager.change_adv_strategy(only_bot_active=True)) # платка
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
