"""Redis-снимок суммы показов РК для gate RESOLVE_CALIBRATION_TRIM.

Сравнивается сумма ``views`` по ``ComplexAdv.all_adv_ids`` (авто + поиск) за окно
``max_last_period`` — тот же источник, что fact V3 (``full_adv_wb_stat``).
Отдельный prefix от ``ChangePlanFact`` (backward compat).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from app.core.redis_cache.mixins.main_objects_mixins.adv_setting_redis_cache import (
    AdvSettingRedisCache,
)
from app.core.redis_cache.redis_cache_base import RedisCacheBase
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat

logger = logging.getLogger(__name__)


class ChangePlanFactViews(AdvSettingRedisCache, RedisCacheBase, prefix="ChangePlanFactViews"):
    """Последняя обработанная сумма показов complex_adv для calibration gate."""

    async def get_cached_views(self) -> int | None:
        """Вернуть сохранённые views или ``None``, если ключа нет / значение битое."""
        value_bytes: bytes | str | None = await self._client.get(self._key)
        if not value_bytes:
            return None
        if isinstance(value_bytes, bytes):
            raw = value_bytes.decode()
        else:
            raw = value_bytes
        try:
            return int(raw)
        except ValueError:
            logger.warning(
                "ChangePlanFactViews: invalid cached value adv_id=%s raw=%r",
                self._unique_id,
                raw,
            )
            return None

    async def set_views(self, views: int) -> None:
        """Записать сумму показов после успешного NORMAL-тика."""
        await self._client.set(self._key, str(int(views)))


async def resolve_complex_adv_total_views(
    complex_adv: ComplexAdv,
    *,
    max_last_period: int = 2,
) -> int:
    """SUM(views) по ``all_adv_ids`` за окно fact из ``full_adv_wb_stat``.

    Args:
        complex_adv: РК с авто и поисковым adv_id.
        max_last_period: Дней окна (как ``process_adv_v3`` / ``PlanFactProvider``).

    Returns:
        Суммарные показы за период; 0 если adv_ids пуст.

    Raises:
        Exception: ошибка ClickHouse (caller может трактовать как fail-closed gate).
    """
    adv_ids = list(complex_adv.all_adv_ids)
    if not adv_ids:
        return 0
    pass_days = max_last_period - 1
    end_date = datetime.now()
    start_date = end_date - timedelta(days=pass_days)
    stats = await full_wb_adv_stat.get_stats_by_last_days(
        adv_ids, start_date, end_date
    )
    return int(stats.views)
