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


def permitted_physical_adv_ids(auto_id: int, search_id: int | None) -> set[int]:
    """Физические WB adv_id одной ComplexAdv: Auto и Search, без синтетического id."""
    allowed = {auto_id}
    if search_id is not None:
        allowed.add(search_id)
    return allowed


def preserve_distinct_adv_ids(
    rows: list[CampaignStatRow],
    scoped: ScopedAdvIds,
) -> list[CampaignStatRow]:
    """
    Оставляет строки известных физических adv_id.

    Отсутствие одной ноги не ошибка: missing leg не превращается в нулевую
    строку и не считается синтетическим слиянием. Чужие id здесь только
    отфильтровываются; отказ по ним делает ``assert_no_synthetic_merge``.
    """
    allowed: set[int] = set()
    if scoped.auto_adv_id is not None:
        allowed.add(scoped.auto_adv_id)
    if scoped.auction_adv_id is not None:
        allowed.add(scoped.auction_adv_id)
    return [row for row in rows if row.campaign_id in allowed]


def assert_observed_ids_are_physical(
    observed_ids: set[int],
    permitted_ids: set[int],
) -> None:
    """
    Запрещает campaign_id вне разрешённых физических adv_id scope.

    Raises:
        ValueError: если наблюдаемый id не входит в permitted physical set.
    """
    unexpected = sorted(observed_ids - permitted_ids)
    if not unexpected:
        return
    shown = ", ".join(str(campaign_id) for campaign_id in unexpected)
    raise ValueError(f"synthetic campaign_id {shown} replaces Auto/Search originals")


def assert_no_synthetic_merge(
    rows: list[CampaignStatRow],
    auto_id: int,
    search_id: int,
) -> None:
    """
    Отклоняет campaign_id вне физических Auto/Search.

    Допустимые состояния присутствия данных: обе ноги, только Auto, только
    Search, ни одной. Missing leg не является доказательством synthetic merge
    и не требует нулевой строки отсутствующей ноги.

    Raises:
        ValueError: если в строках есть id вне ``{auto_id, search_id}``.
    """
    assert_observed_ids_are_physical(
        {row.campaign_id for row in rows},
        permitted_physical_adv_ids(auto_id, search_id),
    )


def campaign_stat_sort_key(row: CampaignStatRow) -> tuple[str, int, str]:
    """Стабильный ключ сортировки (dataset_id внешне, здесь campaign+date)."""
    return ("campaign_full_stat", row.campaign_id, row.date.isoformat())
