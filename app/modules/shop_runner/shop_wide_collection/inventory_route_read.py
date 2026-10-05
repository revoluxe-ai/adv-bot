"""Read-latest inventory route epoch для pre-write gate (task 4.4).

Spec: ``connected-shop-campaign-ad-data-collection`` (design §C, §D.1).
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.
Qualification: ``openspec/decisions/clickhouse-sql-database-qualification/decision.md``.

Читает ``route`` и ``route_version`` через argMax; не пишет inventory и не
использует Redis как второй SoT epoch.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from app.modules.shop_runner.shop_wide_collection.route_write_gate import (
    InventoryRouteSnapshot,
)

_SELECT_ROUTE_SNAPSHOT = """
SELECT
    adv_id,
    argMax(route, version) AS route,
    argMax(route_version, version) AS route_version
FROM default_db.shop_campaign_inventory
WHERE shop_id = %(shop_id)s
  AND adv_id IN %(adv_ids)s
GROUP BY adv_id
"""


class _QueryRows(Protocol):
    """Минимальный ответ ``client.query``."""

    result_rows: Sequence[Sequence[object]]


class ShopCampaignInventoryRouteReader(Protocol):
    """Узкий CH-клиент для read-latest route epoch."""

    async def query(
        self,
        query: str,
        parameters: Mapping[str, object] | None = None,
    ) -> _QueryRows: ...


def _as_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} from inventory read must be int")
    return value


def _as_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} from inventory read must be str")
    return value


def _snapshot_from_row(row: Sequence[object]) -> InventoryRouteSnapshot:
    if len(row) != 3:
        raise TypeError("inventory route select must return 3 columns")
    return InventoryRouteSnapshot(
        adv_id=_as_int(row[0], "adv_id"),
        route=_as_text(row[1], "route"),
        route_version=_as_int(row[2], "route_version"),
    )


async def load_inventory_route_snapshots(
    client: ShopCampaignInventoryRouteReader,
    *,
    shop_id: str,
    adv_ids: Sequence[int],
) -> dict[int, InventoryRouteSnapshot]:
    """Read-latest ``route`` и ``route_version`` per ``adv_id``.

    Args:
        client: уже открытый CH-клиент; соединение создаёт вызывающий код.
        shop_id: магазин inventory.
        adv_ids: physical WB campaign ids. Пустой список не выполняет SQL.

    Returns:
        Словарь ``adv_id → InventoryRouteSnapshot`` только для найденных id.
    """
    if not adv_ids:
        return {}
    result = await client.query(
        _SELECT_ROUTE_SNAPSHOT,
        parameters={"shop_id": shop_id, "adv_ids": list(adv_ids)},
    )
    loaded: dict[int, InventoryRouteSnapshot] = {}
    for row in result.result_rows:
        snapshot = _snapshot_from_row(row)
        loaded[snapshot.adv_id] = snapshot
    return loaded
