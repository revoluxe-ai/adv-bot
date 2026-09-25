"""Снимок суммарного расхода РК за всё время для UI активности и Excel.

Семантика совпадает с гейтом абсолютного лимита (``get_total_spend_by_advs``):
отдельно Авто и Аукцион, общий — сумма при известных обеих ногах.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TotalSpendSnapshot:
    """Расход за всю историю по ногам РК."""

    auto: float | None
    search: float | None

    @property
    def common(self) -> float | None:
        """Сумма Авто и Аукциона; ``None``, если хотя бы одна нога недоступна."""
        if self.auto is None or self.search is None:
            return None
        return self.auto + self.search


def format_spend_rubles_display(spend: float | None) -> str:
    """Текст расхода: целые рубли вверх; ``None`` — «н/д»."""
    if spend is None:
        return "н/д"
    return str(math.ceil(spend))


def spend_excel_cell_value(spend: float | None) -> int | str:
    """Значение RO-ячейки Excel: ``math.ceil`` или пустая строка."""
    if spend is None:
        return ""
    return math.ceil(spend)


async def _fetch_leg_spend(adv_id: int) -> float | None:
    """Один запрос суммарного расхода; при ошибке ClickHouse — ``None``."""
    try:
        return await full_wb_adv_stat.get_total_spend_by_advs([adv_id])
    except Exception:
        logger.exception(
            "Ошибка получения суммарного расхода из ClickHouse adv_id=%s", adv_id
        )
        return None


async def load_total_spend_snapshot(adv_setting: AdvSetting) -> TotalSpendSnapshot:
    """Загрузить расход Авто и Аукциона за всё время для ``AdvSetting``.

    Args:
        adv_setting: настройки РК с ``adv_id`` и опциональным ``search_adv_id``.

    Returns:
        Снимок: ``search`` = ``0.0`` без запроса, если нога аукциона отсутствует.
    """
    auto = await _fetch_leg_spend(adv_setting.adv_id)
    if adv_setting.search_adv_id:
        search = await _fetch_leg_spend(adv_setting.search_adv_id)
    else:
        search = 0.0
    return TotalSpendSnapshot(auto=auto, search=search)
