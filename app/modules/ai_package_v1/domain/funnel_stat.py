"""Зерно funnel/common stat: nmid + date (только main_nmid из scope)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class FunnelStatRow(BaseModel):
    """Строка ``default_db.wb_common_stat`` на зерне nmid + date."""

    shop_id: int
    nmid: int
    date: date
    open_card: int = 0
    add_to_cart: int = 0
    orders: int = 0
    orders_sum: int = 0
    buy_outs: int = 0


def funnel_stat_sort_key(row: FunnelStatRow) -> tuple[str, int, str]:
    """Стабильный ключ сортировки для детерминизма."""
    return ("complex_adv_funnel", row.nmid, row.date.isoformat())
