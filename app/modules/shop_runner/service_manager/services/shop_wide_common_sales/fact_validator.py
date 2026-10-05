"""Валидация фактов funnel API перед вставкой в wb_common_stat."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
    CommonSaleStatRow,
)

from .collect_types import CollectContext

logger = logging.getLogger(__name__)

_MAX_NMID = 10**15
_MAX_ABS_METRIC = 10**18


@dataclass(frozen=True, slots=True)
class ValidatedFacts:
    """Строки, прошедшие валидацию, и счётчик отклонённых пар."""

    rows: tuple[CommonSaleStatRow, ...]
    rejected_count: int
    returned_pairs: frozenset[tuple[int, date]]


def validate_and_deduplicate_rows(
    raw_rows: list[CommonSaleStatRow],
    *,
    context: CollectContext,
    source_index_offset: int = 0,
) -> ValidatedFacts:
    """
    Отфilterовать invalid/conflicting факты; dedup идентичных дубликатов.

    Строгие exact-типы: ``int``/``date``/``float`` без coercion из str/bool.
    Принятые строки нормализуются в ``CommonSaleStatRow`` с валидными полями.

    Args:
        raw_rows: сырые строки из одного batch API.
        context: контекст текущего chunk (exact request nmIDs + окно MSK).
        source_index_offset: смещение индекса для stable sort dedup.

    Returns:
        ValidatedFacts с безопасными строками для CH insert.
    """
    indexed: list[tuple[int, CommonSaleStatRow]] = list(
        enumerate(raw_rows, start=source_index_offset)
    )
    indexed.sort(key=lambda item: item[0])

    accepted: dict[tuple[int, date], CommonSaleStatRow] = {}
    rejected_keys: set[tuple[int, date]] = set()
    rejected = 0
    returned_pairs: set[tuple[int, date]] = set()

    for _idx, row in indexed:
        normalized = _normalize_row(row)
        if normalized is None:
            rejected += 1
            continue

        key = (normalized.nmid, normalized.day)
        nmid, day = key

        if key in rejected_keys:
            rejected += 1
            logger.debug(
                "reject tombstoned key nmid=%s date=%s",
                nmid,
                day,
            )
            continue

        if nmid not in context.attempted_nmids:
            rejected += 1
            logger.debug(
                "reject unexpected nmid=%s date=%s",
                nmid,
                day,
            )
            continue
        if day < context.window_start or day > context.window_end:
            rejected += 1
            logger.debug(
                "reject out-of-window nmid=%s date=%s",
                nmid,
                day,
            )
            continue

        existing = accepted.get(key)
        if existing is None:
            accepted[key] = normalized
            returned_pairs.add(key)
            continue

        if _rows_metrics_equal(existing, normalized):
            continue

        rejected += 1
        rejected_keys.add(key)
        accepted.pop(key, None)
        returned_pairs.discard(key)
        logger.debug(
            "reject conflicting duplicate nmid=%s date=%s",
            nmid,
            day,
        )

    safe_rows = tuple(accepted.values())
    return ValidatedFacts(
        rows=safe_rows,
        rejected_count=rejected,
        returned_pairs=frozenset(returned_pairs),
    )


def _normalize_row(row: CommonSaleStatRow) -> CommonSaleStatRow | None:
    """Проверить exact-типы и вернуть нормализованную строку или None."""
    nmid = _strict_positive_nmid(getattr(row, "nmid", None))
    day = _strict_date(getattr(row, "day", None))
    if nmid is None or day is None:
        return None

    open_card = _strict_int_metric(getattr(row, "open_card", None))
    add_to_cart = _strict_int_metric(getattr(row, "add_to_cart", None))
    orders = _strict_int_metric(getattr(row, "orders", None))
    buy_outs = _strict_int_metric(getattr(row, "buy_outs", None))
    orders_sum = _strict_finite_float(getattr(row, "orders_sum", None))
    buyouts_sum_rub = _strict_finite_float(getattr(row, "buyouts_sum_rub", None))

    if any(
        v is None
        for v in (
            open_card,
            add_to_cart,
            orders,
            buy_outs,
            orders_sum,
            buyouts_sum_rub,
        )
    ):
        return None

    assert open_card is not None
    assert add_to_cart is not None
    assert orders is not None
    assert buy_outs is not None
    assert orders_sum is not None
    assert buyouts_sum_rub is not None

    return CommonSaleStatRow(
        nmid=nmid,
        day=day,
        open_card=open_card,
        add_to_cart=add_to_cart,
        orders=orders,
        orders_sum=orders_sum,
        buy_outs=buy_outs,
        buyouts_sum_rub=buyouts_sum_rub,
    )


def _strict_positive_nmid(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value <= 0 or value > _MAX_NMID:
        return None
    return value


def _strict_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return None
    if not isinstance(value, date):
        return None
    return value


def _strict_int_metric(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if abs(value) > _MAX_ABS_METRIC:
        return None
    return value


def _strict_finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        fv = float(value)
    elif isinstance(value, float):
        fv = value
    else:
        return None
    if not math.isfinite(fv) or abs(fv) > _MAX_ABS_METRIC:
        return None
    return fv


def _rows_metrics_equal(a: CommonSaleStatRow, b: CommonSaleStatRow) -> bool:
    return (
        a.open_card == b.open_card
        and a.add_to_cart == b.add_to_cart
        and a.orders == b.orders
        and a.orders_sum == b.orders_sum
        and a.buy_outs == b.buy_outs
        and a.buyouts_sum_rub == b.buyouts_sum_rub
    )
