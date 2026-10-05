"""Append-only writer ``default_db.shop_campaign_collection_availability``.

Spec: ``connected-shop-campaign-ad-data-collection`` (design §D.3, §F.3, L6).
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.
Qualification: ``openspec/decisions/clickhouse-sql-database-qualification/decision.md``.

Строка availability — диагностика попытки сбора. ``route_version`` копирует
сверенный epoch inventory и **не** заменяет запрет записи fact grain.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)

_INSERT_AVAILABILITY = """
INSERT INTO default_db.shop_campaign_collection_availability
    (shop_id, adv_id, collector_id, reason_code, route_version)
VALUES
    (%(shop_id)s, %(adv_id)s, %(collector_id)s, %(reason_code)s, %(route_version)s)
"""


class _QueryRows(Protocol):
    """Минимальный ответ ``client.query``."""

    result_rows: Sequence[Sequence[object]]


class ShopCampaignAvailabilityClickHouse(Protocol):
    """Узкий CH-клиент availability. Сессию открывает вызывающий код."""

    async def query(
        self,
        query: str,
        parameters: Mapping[str, object] | None = None,
    ) -> _QueryRows: ...


@dataclass(frozen=True, slots=True)
class ShopCampaignAvailabilityWrite:
    """Append-only строка availability после попытки collector."""

    shop_id: str
    adv_id: int
    collector_id: str
    reason_code: str
    route_version: int


async def append_shop_campaign_collection_availability(
    client: ShopCampaignAvailabilityClickHouse,
    *,
    shop_id: str,
    adv_id: int,
    collector_id: str,
    reason_code: str,
    route_version: int,
) -> ShopCampaignAvailabilityWrite:
    """Append одной diagnostic row; не upsert и не ReplacingMergeTree.

    Args:
        client: уже открытый CH-клиент.
        shop_id: магазин попытки сбора.
        adv_id: physical WB campaign id.
        collector_id: идентификатор collector (literal String в CH).
        reason_code: код исхода попытки.
        route_version: сверенный epoch inventory на момент gate/check.

    Returns:
        Записанная строка (in-memory mirror для тестов).

    Raises:
        ValueError: пустой ``shop_id`` или ``collector_id``.
    """
    if shop_id == "":
        raise ValueError("shop_id must be a non-empty string")
    if collector_id == "":
        raise ValueError("collector_id must be a non-empty string")
    row = ShopCampaignAvailabilityWrite(
        shop_id=shop_id,
        adv_id=adv_id,
        collector_id=collector_id,
        reason_code=reason_code,
        route_version=route_version,
    )
    await client.query(
        _INSERT_AVAILABILITY,
        parameters={
            "shop_id": row.shop_id,
            "adv_id": row.adv_id,
            "collector_id": row.collector_id,
            "reason_code": row.reason_code,
            "route_version": row.route_version,
        },
    )
    logger.info(
        "shop_campaign_collection_availability append shop_id=%s adv_id=%s "
        "collector_id=%s reason_code=%s route_version=%s",
        shop_id,
        adv_id,
        collector_id,
        reason_code,
        route_version,
    )
    return row
