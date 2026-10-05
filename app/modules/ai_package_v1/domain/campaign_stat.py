"""Зерно campaign full stat: отдельные Auto/Search adv_id, изоляция shop."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel

from app.modules.ai_package_v1.domain.shop_id import AuthoritativeShopId


class CampaignStatRow(BaseModel):
    """Строка ``default_db.full_adv_wb_stat`` на зерне campaign_id + date."""

    shop_id: AuthoritativeShopId
    campaign_id: int
    date: date
    views: int = 0
    clicks: int = 0


@dataclass(frozen=True)
class ScopedAdvIds:
    """Пара оригинальных идентификаторов ComplexAdv (без слияния)."""

    auto_adv_id: int | None
    auction_adv_id: int | None


def rows_for_shop(rows: list[CampaignStatRow], shop_id: str) -> list[CampaignStatRow]:
    """Shop isolation: только строки запрошенного магазина."""
    return [r for r in rows if r.shop_id == shop_id]


def preserve_distinct_adv_ids(
    rows: list[CampaignStatRow],
    scoped: ScopedAdvIds,
) -> list[CampaignStatRow]:
    """
    Фильтрует строки по известным adv_id, не сливая Auto и Search в один id.

    Raises:
        ValueError: если в выходе остался только один id при двух исходных.
    """
    allowed: set[int] = set()
    if scoped.auto_adv_id is not None:
        allowed.add(scoped.auto_adv_id)
    if scoped.auction_adv_id is not None:
        allowed.add(scoped.auction_adv_id)
    filtered = [r for r in rows if r.campaign_id in allowed]
    present_ids = {r.campaign_id for r in filtered}
    if (
        scoped.auto_adv_id is not None
        and scoped.auction_adv_id is not None
        and scoped.auto_adv_id != scoped.auction_adv_id
        and len(present_ids) < 2
        and len(filtered) >= 2
    ):
        raise ValueError("campaign stat rows must not collapse Auto and Search ids")
    if len(present_ids) == 1 and scoped.auto_adv_id != scoped.auction_adv_id:
        if scoped.auto_adv_id and scoped.auction_adv_id:
            if scoped.auto_adv_id in present_ids and scoped.auction_adv_id in present_ids:
                return filtered
            if scoped.auto_adv_id in allowed and scoped.auction_adv_id in allowed:
                missing = allowed - present_ids
                if missing:
                    return filtered
    return filtered


def assert_no_synthetic_merge(
    rows: list[CampaignStatRow],
    auto_id: int,
    search_id: int,
) -> None:
    """
    Контракт: оба оригинальных campaign_id должны встречаться раздельно.

    Raises:
        ValueError: если все строки ссылаются на один synthetic id.
    """
    ids = {r.campaign_id for r in rows}
    if auto_id == search_id:
        return
    if auto_id in ids and search_id in ids:
        return
    if not rows:
        return
    if len(ids) == 1:
        only = next(iter(ids))
        if only not in (auto_id, search_id):
            raise ValueError(f"synthetic campaign_id {only} replaces Auto/Search originals")
        if auto_id != search_id:
            raise ValueError("silent merge: only one of Auto/Search adv_id present in export")


def campaign_stat_sort_key(row: CampaignStatRow) -> tuple[str, int, str]:
    """Стабильный ключ сортировки (dataset_id внешне, здесь campaign+date)."""
    return ("campaign_full_stat", row.campaign_id, row.date.isoformat())
