"""Read-only CPO каждой рекламной ноги для spec leg-cpo-economics.

Модуль не владеет plan/fact и ничего не пишет. Он строит согласованный снимок
Auto/Search из full_adv_wb_stat по structural leg ids и запрещает скрытое
смешивание ног через aggregate fact_pay_for_order.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
        ComplexAdv,
    )


LEG_CPO_CONTROL_DAYS = 2


@dataclass(frozen=True, slots=True)
class LegCpoSnapshot:
    """Согласованный read-model CPO Auto/Search за один observation window."""

    auto_adv_id: int
    search_adv_id: int | None
    auto_cpo: float | None
    search_cpo: float | None
    start_date: datetime
    end_date: datetime


def compute_leg_cpo(stat: SmallFullAdvStat | None) -> float | None:
    """Посчитать CPO одной ноги без fallback на соседнюю или aggregate-метрику."""
    if stat is None:
        return None
    return float(stat.spend) / max(int(stat.orders), 1)


def build_leg_cpo_snapshot(
    *,
    auto_adv_id: int,
    search_adv_id: int | None,
    stats_by_adv_id: dict[int, SmallFullAdvStat],
    start_date: datetime,
    end_date: datetime,
) -> LegCpoSnapshot:
    """Собрать immutable leg snapshot из exact-adv статистики одного окна."""
    auto_stat = stats_by_adv_id.get(int(auto_adv_id))
    search_stat = (
        stats_by_adv_id.get(int(search_adv_id))
        if search_adv_id is not None
        else None
    )
    return LegCpoSnapshot(
        auto_adv_id=int(auto_adv_id),
        search_adv_id=(int(search_adv_id) if search_adv_id is not None else None),
        auto_cpo=compute_leg_cpo(auto_stat),
        search_cpo=compute_leg_cpo(search_stat),
        start_date=start_date,
        end_date=end_date,
    )


def resolve_leg_cpo_window(
    *,
    now: datetime | None = None,
    days: int = LEG_CPO_CONTROL_DAYS,
) -> tuple[datetime, datetime]:
    """Разрешить явное inclusive calendar-day окно для обеих рекламных ног."""
    if days <= 0:
        raise ValueError("days must be > 0")
    end_date = now or datetime.now()
    return end_date - timedelta(days=days - 1), end_date


async def load_leg_cpo_snapshot(
    *,
    auto_adv_id: int,
    search_adv_id: int | None,
    now: datetime | None = None,
    days: int = LEG_CPO_CONTROL_DAYS,
) -> LegCpoSnapshot:
    """Загрузить leg CPO одной structural пары одним read-only CH запросом."""
    start_date, end_date = resolve_leg_cpo_window(now=now, days=days)
    adv_ids = [int(auto_adv_id)]
    if search_adv_id is not None:
        adv_ids.append(int(search_adv_id))
    stats_by_adv_id = await full_wb_adv_stat.get_stats_by_adv_ids_last_days(
        adv_ids,
        start_date,
        end_date,
    )
    return build_leg_cpo_snapshot(
        auto_adv_id=int(auto_adv_id),
        search_adv_id=search_adv_id,
        stats_by_adv_id=stats_by_adv_id,
        start_date=start_date,
        end_date=end_date,
    )


async def load_leg_cpo_snapshots(
    complex_advs: list["ComplexAdv"],
    *,
    now: datetime | None = None,
    days: int = LEG_CPO_CONTROL_DAYS,
) -> dict[int, LegCpoSnapshot]:
    """Одним CH-read загрузить leg CPO для списка ComplexAdv без N+1."""
    if not complex_advs:
        return {}
    start_date, end_date = resolve_leg_cpo_window(now=now, days=days)
    adv_ids: set[int] = set()
    for adv in complex_advs:
        adv_ids.add(int(adv.adv_id))
        if adv.search_adv_id is not None:
            adv_ids.add(int(adv.search_adv_id))
    stats_by_adv_id = await full_wb_adv_stat.get_stats_by_adv_ids_last_days(
        sorted(adv_ids),
        start_date,
        end_date,
    )

    snapshots: dict[int, LegCpoSnapshot] = {}
    for adv in complex_advs:
        snapshots[int(adv.adv_id)] = build_leg_cpo_snapshot(
            auto_adv_id=int(adv.adv_id),
            search_adv_id=adv.search_adv_id,
            stats_by_adv_id=stats_by_adv_id,
            start_date=start_date,
            end_date=end_date,
        )
    return snapshots
