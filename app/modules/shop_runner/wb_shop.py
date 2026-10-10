import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar

from app.core.di.wb_manager_hub import WBManagerHub
from app.core.redis_manager_v2.redis_client import RedisClient
from .modules.wb_api import WBApi

import typing


if typing.TYPE_CHECKING:
    from .service_manager.services.plan_fact_controller.plan_fact_reader import PlanFactReader

from .shop_run_worker.redis_manager import RedisShopManager
from .service_manager import CoroutinesManager
from .service_manager.services.shop_wide_common_sales.taskgroup_no_ad_supervisor import (
    SUPERVISOR_COROUTINE_NAMES,
    taskgroup_no_ad_supervisor,
)
from .shop_wide_collection.feature_flag import (
    ShopWideCollectionMode,
    apply_shop_wide_collection_gate,
)
from .shop_wide_collection.managed_record_contract import (
    SHOP_WIDE_UNMANAGED_COROUTINE_NAME,
)
from .tasks_manager.tasks_manager import TasksManager

logger = logging.getLogger(__name__)
T = TypeVar("T")


def _taskgroup_coro(
    coroutine_name: str,
    coro_factory: typing.Callable[[], Coroutine[Any, Any, None]],
) -> Coroutine[Any, Any, None]:
    """Обёрнуть factory в no-ad supervisor если coroutine в registry."""
    if coroutine_name in SUPERVISOR_COROUTINE_NAMES:
        return taskgroup_no_ad_supervisor(coro_factory, coroutine_name=coroutine_name)
    return coro_factory()


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
        """Долгий tick магазина: managed RECORD и dual-path shop-wide orchestration.

        Spec ``connected-shop-campaign-ad-data-collection``, design Migration
        Plan. Per-shop флаг читается один раз на старте процесса. OFF и
        rollback не добавляют unmanaged task и не удаляют историю ClickHouse.
        ON ставит ``collect_shop_wide_campaign_advertising`` в shop-runner;
        scripts/Job MUST NOT быть primary executor (decision §Forbidden).
        """
        from .service_manager.exc import StopShopUpdateException

        decision = apply_shop_wide_collection_gate(self.shop_id)
        shop_wide_dual_path = decision.mode is ShopWideCollectionMode.DUAL_PATH_ACTIVE
        if shop_wide_dual_path:
            logger.info(
                "shop-wide dual-path active shop_id=%s coroutine=%s",
                self.shop_id,
                SHOP_WIDE_UNMANAGED_COROUTINE_NAME,
            )
        wb_api = self._wb_api
        coroutines_manager = CoroutinesManager(
            wb_api,
            self._redis_client_wrapper,
            tasks_manager=self._tasks_manager,
            plan_fact_reader=self._plan_fact_reader,
            wb_manager_hub=self._wb_manager_hub
        )
        cm = coroutines_manager
        # TODO: Записи статистики идут в базу не одним батчем, это про общую или рекламную, исправить
        # TODO: !!! Надо еще добавить проверку на что отключено что включено из автоматизации в новой верссии  и добавить кнопку управления
        #  автоэкспонентой, и именить тарификацию за автоматизацию, т.к. теперь управляющих сущности три
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._alive_worker_run())

                tg.create_task(
                    _taskgroup_coro(
                        "update_advs_data_from_wb_to_pg",
                        lambda: cm.update_advs_data_from_wb_to_pg(),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "update_cards_data_from_wb_to_pg",
                        lambda: cm.update_cards_data_from_wb_to_pg(),
                    )
                )
                tg.create_task(cm.update_common_sale_stat(only_bot_active=False))
                tg.create_task(
                    _taskgroup_coro(
                        "update_full_adv_stat",
                        lambda: cm.update_full_adv_stat(only_bot_active=False),
                    )
                )
                if shop_wide_dual_path:
                    tg.create_task(cm.collect_shop_wide_campaign_advertising())
                tg.create_task(
                    _taskgroup_coro(
                        "update_clusters_adv_stats_today",
                        lambda: cm.update_clusters_adv_stats_today(only_bot_active=False),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "update_clusters_adv_stats_history",
                        lambda: cm.update_clusters_adv_stats_history(only_bot_active=False),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "refresh_stats_freshness_cache",
                        lambda: cm.refresh_stats_freshness_cache(only_bot_active=False),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "adv_settings_auto_update",
                        lambda: cm.adv_settings_auto_update(only_bot_active=True),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "hierarchical_ad_control_diagnostics",
                        lambda: cm.hierarchical_ad_control_diagnostics(),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "update_minus_phrases_in_advs",
                        lambda: cm.update_minus_phrases_in_advs(only_bot_active=False),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "update_cluster_bids",
                        lambda: cm.update_cluster_bids(only_bot_active=True),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "cache_current_cluster_bids",
                        lambda: cm.cache_current_cluster_bids(only_bot_active=False),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "preload_min_bids_cache_miss",
                        lambda: cm.preload_min_bids_cache_miss(only_bot_active=False),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "preload_min_bids_cache_old",
                        lambda: cm.preload_min_bids_cache_old(only_bot_active=False),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "handle_stats_stale_emergency",
                        lambda: cm.handle_stats_stale_emergency(only_bot_active=True),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "update_plan_fact_stats",
                        lambda: cm.update_plan_fact_stats(only_bot_active=False),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "auto_budget_watchdog",
                        lambda: cm.auto_budget_watchdog(only_bot_active=False),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "update_top_key_in_advs",
                        lambda: cm.update_top_key_in_advs(only_bot_active=True),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "update_common_bid_in_search_adv",
                        lambda: cm.update_common_bid_in_search_adv(only_bot_active=True),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "increment_fact_data_stats",
                        lambda: cm.increment_fact_data_stats(only_bot_active=False),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "auto_shelf_bid_increment_stats",
                        lambda: cm.auto_shelf_bid_increment_stats(only_bot_active=False),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "auto_shelf_bid_control",
                        lambda: cm.auto_shelf_bid_control(only_bot_active=True),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "white_list_tail_trimmer",
                        lambda: cm.white_list_tail_trimmer(only_bot_active=True),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "auto_reset_bid_for_auto_adv",
                        lambda: cm.auto_reset_bid_for_auto_adv(only_bot_active=True),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "update_individual_keyword_target_places",
                        lambda: cm.update_individual_keyword_target_places(only_bot_active=True),
                    )
                )
                tg.create_task(
                    _taskgroup_coro(
                        "change_adv_strategy",
                        lambda: cm.change_adv_strategy(only_bot_active=True),
                    )
                )
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
