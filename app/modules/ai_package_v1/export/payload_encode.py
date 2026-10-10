"""Сериализация dataset rows в CSV bytes (детерминированный порядок)."""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence

from app.modules.ai_package_v1.domain.campaign_stat import (
    CampaignStatRow,
    campaign_stat_sort_key,
)
from app.modules.ai_package_v1.domain.funnel_stat import (
    FunnelStatRow,
    funnel_stat_sort_key,
)
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv


def encode_campaign_stat_csv(rows: list[CampaignStatRow]) -> bytes:
    """
    CSV campaign_full_stat: shop_id, campaign_id, date, views, clicks.

    Args:
        rows: Строки CH (уже отфильтрованные по shop/adv).

    Returns:
        UTF-8 bytes с заголовком.
    """
    ordered = sorted(rows, key=campaign_stat_sort_key)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["shop_id", "campaign_id", "date", "views", "clicks"])
    for row in ordered:
        writer.writerow(
            [
                row.shop_id,
                row.campaign_id,
                row.date.isoformat(),
                row.views,
                row.clicks,
            ]
        )
    return buffer.getvalue().encode("utf-8")


def encode_funnel_stat_csv(rows: list[FunnelStatRow]) -> bytes:
    """
    CSV complex_adv_funnel: shop_id, nmid, date, метрики common stat.

    Args:
        rows: Только scoped main_nmid.

    Returns:
        UTF-8 bytes с заголовком.
    """
    ordered = sorted(rows, key=funnel_stat_sort_key)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "shop_id",
            "nmid",
            "date",
            "open_card",
            "add_to_cart",
            "orders",
            "orders_sum",
            "buy_outs",
        ]
    )
    for row in ordered:
        writer.writerow(
            [
                row.shop_id,
                row.nmid,
                row.date.isoformat(),
                row.open_card,
                row.add_to_cart,
                row.orders,
                row.orders_sum,
                row.buy_outs,
            ]
        )
    return buffer.getvalue().encode("utf-8")


def encode_pg_inventory_csv(
    rows: Sequence[ExportScopeAdv],
    *,
    manifest_shop_id: str,
) -> bytes:
    """
    CSV campaign_settings_snapshot: allowlisted inventory/relations only.

    Args:
        rows: Inventory DTO (без bids/budgets/detailed settings).
        manifest_shop_id: Authoritative shop id, та же строка, что в manifest.

    Returns:
        UTF-8 bytes с заголовком (возможен только header при пустом scope).
    """
    ordered = sorted(rows, key=lambda row: row.auto_adv_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "shop_id",
            "auto_adv_id",
            "search_adv_id",
            "main_nmid",
            "name",
            "active_status",
            "bot_active",
        ]
    )
    for row in ordered:
        writer.writerow(
            [
                manifest_shop_id,
                row.auto_adv_id,
                row.search_adv_id if row.search_adv_id is not None else "",
                row.main_nmid if row.main_nmid is not None else "",
                row.name,
                row.active_status,
                1 if row.bot_active else 0,
            ]
        )
    return buffer.getvalue().encode("utf-8")
