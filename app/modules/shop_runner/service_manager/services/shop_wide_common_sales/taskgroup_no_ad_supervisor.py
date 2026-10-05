"""Bounded no-ad supervisor для TaskGroup coroutines в WBShop.run."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable, Coroutine
from typing import Any

from app.modules.shop_runner.service_manager.exc import StopShopUpdateException
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany

logger = logging.getLogger(__name__)

SHOP_RUNNER_NO_ADV_RETRY_SEC_ENV = "SHOP_RUNNER_NO_ADV_RETRY_SEC"
DEFAULT_NO_ADV_RETRY_SEC = 300.0

# Registry из design.md §No-Campaign TaskGroup Survival (HEAD 62c8d48…).
SUPERVISOR_COROUTINE_NAMES: frozenset[str] = frozenset(
    {
        "update_full_adv_stat",
        "update_clusters_adv_stats_today",
        "update_clusters_adv_stats_history",
        "refresh_stats_freshness_cache",
        "adv_settings_auto_update",
        "update_minus_phrases_in_advs",
        "update_cluster_bids",
        "cache_current_cluster_bids",
        "preload_min_bids_cache_miss",
        "preload_min_bids_cache_old",
        "handle_stats_stale_emergency",
        "update_plan_fact_stats",
        "auto_budget_watchdog",
        "update_common_bid_in_search_adv",
        "increment_fact_data_stats",
        "auto_shelf_bid_increment_stats",
        "auto_shelf_bid_control",
        "auto_reset_bid_for_auto_adv",
        "change_adv_strategy",
    }
)


def no_adv_retry_sec() -> float:
    """Интервал bounded retry при NotFoundActiveAdvCompany (env, default 300s)."""
    raw = os.environ.get(SHOP_RUNNER_NO_ADV_RETRY_SEC_ENV)
    if raw is None or not str(raw).strip():
        return DEFAULT_NO_ADV_RETRY_SEC
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_NO_ADV_RETRY_SEC


def taskgroup_no_ad_supervisor(
    coro_factory: Callable[[], Coroutine[Any, Any, None]],
    *,
    coroutine_name: str | None = None,
    retry_sec: float | None = None,
) -> Coroutine[Any, Any, None]:
    """
    Обёртка factory для tg.create_task: ловит только StopShop→NotFound.

    Прочие StopShopUpdateException, auth и cancellation пробрасываются без изменений.
    """

    async def _supervised() -> None:
        pause = retry_sec if retry_sec is not None else no_adv_retry_sec()
        label = coroutine_name or getattr(coro_factory, "__name__", "coroutine")
        while True:
            try:
                await coro_factory()
                return
            except StopShopUpdateException as exc:
                if not isinstance(exc.__cause__, NotFoundActiveAdvCompany):
                    raise
                logger.info(
                    "taskgroup_no_ad_supervisor: %s no active campaigns, retry in %ss",
                    label,
                    pause,
                )
                await asyncio.sleep(pause)

    return _supervised()


def wrap_if_supervised(
    coroutine_name: str,
    coro_factory: Callable[[], Coroutine[Any, Any, None]],
) -> Callable[[], Coroutine[Any, Any, None]]:
    """Вернуть supervised factory если coroutine в registry."""
    if coroutine_name not in SUPERVISOR_COROUTINE_NAMES:
        return coro_factory

    def _factory() -> Coroutine[Any, Any, None]:
        return taskgroup_no_ad_supervisor(
            coro_factory,
            coroutine_name=coroutine_name,
        )

    return _factory
