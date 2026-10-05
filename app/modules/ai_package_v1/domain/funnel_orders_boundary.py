"""Граница: funnel orders не являются shop product orders/sales (exporter spec)."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.ai_package_v1.domain.dataset_card import DatasetCard
from app.modules.ai_package_v1.domain.enums import DatasetId, PrimarySource


@dataclass(frozen=True, slots=True)
class FunnelOrdersMetric:
    """Минимальная форма funnel-строки с метрикой orders (CH ``wb_common_stat`` grain)."""

    nmid: int
    orders: int


def assert_funnel_orders_do_not_populate_shop_product_orders(
    funnel_rows: list[FunnelOrdersMetric],
    shop_orders_card: DatasetCard,
) -> None:
    """
    Контракт §2.1h / exporter spec: funnel ``orders`` не подменяют shop product orders.

    Raises:
        AssertionError: если карточка shop orders выглядит заполненной из funnel.
    """
    if shop_orders_card.dataset_id != DatasetId.SHOP_PRODUCT_ORDERS_SALES:
        raise AssertionError("expected shop_product_orders_sales dataset card")
    if shop_orders_card.provenance.primary_source != PrimarySource.SOURCE_NOT_ASSIGNED:
        raise AssertionError(
            "funnel orders must not assign a primary source on shop product orders"
        )
    if shop_orders_card.row_count not in (0, None):
        raise AssertionError("funnel orders must not populate shop product order rows")
    total_funnel_orders = sum(row.orders for row in funnel_rows)
    if total_funnel_orders > 0 and shop_orders_card.row_count:
        raise AssertionError("funnel orders leaked into shop product orders row_count")
