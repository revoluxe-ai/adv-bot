"""
Провайдеры Task 4.1: history → inventory, spend, supplier orders.

Чтения ClickHouse и ``ReportsManager``. Новых таблиц и миграций нет.
Воронка продаж магазина этим провайдером не читается.
"""

from __future__ import annotations

from collections.abc import Awaitable, Sequence
from decimal import Decimal, InvalidOperation
from typing import Protocol

from app.modules.attribution_facts.domain.models import DateWindow
from app.utils.click_house.clickhouse_protocol import ClickHouseClientProtocol

# Назначение: distinct adv_id магазина из settings history (не spend).
_HISTORY_ADV_IDS = """
SELECT adv_id
FROM default_db.campaign_settings_history
WHERE shop_id = %(shop_id)s
GROUP BY adv_id
ORDER BY adv_id
""".strip()

# Назначение: актуальные adv_id из shop_campaign_inventory для spend universe.
_INVENTORY_ADV_IDS = """
SELECT adv_id
FROM default_db.shop_campaign_inventory
WHERE shop_id = %(shop_id)s
GROUP BY adv_id
ORDER BY adv_id
""".strip()

# Назначение: argMax spend из full_adv_wb_stat по inventory adv_id и окну.
_SPEND_BY_ADV = """
SELECT
    adv_id,
    SUM(latest_spend) AS spend
FROM (
    SELECT
        adv_id,
        date,
        argMax(spend, version) AS latest_spend
    FROM default_db.full_adv_wb_stat
    WHERE date BETWEEN toDate(%(start_date)s) AND toDate(%(end_date)s)
      AND adv_id IN %(adv_ids)s
    GROUP BY adv_id, date
)
GROUP BY adv_id
""".strip()


class SupplierOrdersClient(Protocol):
    """Узкий ``ReportsManager.get_supplier_orders``.

    Возврат — ``Awaitable``, а не ``async def``: coroutine result инвариантен,
    и ``list[OrdersItem]`` иначе не подходит под ``list[object]``.
    """

    def get_supplier_orders(
        self,
        *,
        date_from: str,
        flag: int | None = 0,
    ) -> Awaitable[Sequence[object]]:
        """Одна страница statistics-api supplier orders."""
        ...


class HistoryThenInventoryAdvIds:
    """Сначала settings history, затем inventory. Ошибка чтения — ``None``."""

    def __init__(self, client: ClickHouseClientProtocol, *, source: str) -> None:
        if source not in {"history", "inventory"}:
            raise ValueError("source must be history or inventory")
        self._client = client
        self._sql = _HISTORY_ADV_IDS if source == "history" else _INVENTORY_ADV_IDS

    async def list_adv_ids(self, shop_id: str) -> tuple[int, ...] | None:
        """Успех, включая пустой набор. Исключение драйвера → None."""
        try:
            result = await self._client.query(
                self._sql,
                parameters={"shop_id": shop_id},
            )
        except Exception:
            return None
        ids: list[int] = []
        for row in result.result_rows:
            if not row:
                continue
            parsed = _as_int(row[0])
            if parsed is None or parsed <= 0:
                return None
            ids.append(parsed)
        return tuple(ids)


class FullAdvShopSpend:
    """Shop/campaign spend из ``full_adv_wb_stat`` по переданным adv id."""

    def __init__(self, client: ClickHouseClientProtocol) -> None:
        self._client = client

    async def sum_spend_by_adv(
        self,
        adv_ids: tuple[int, ...],
        window: DateWindow,
    ) -> dict[int, Decimal] | None:
        """None при сбое. Пустой ``adv_ids`` не выполняет SQL и возвращает ``{}``."""
        if not adv_ids:
            return {}
        try:
            result = await self._client.query(
                _SPEND_BY_ADV,
                parameters={
                    "start_date": window.start.isoformat(),
                    "end_date": window.end.isoformat(),
                    "adv_ids": list(adv_ids),
                },
            )
        except Exception:
            return None
        spend: dict[int, Decimal] = {}
        for row in result.result_rows:
            if len(row) < 2:
                return None
            adv_id = _as_int(row[0])
            amount = _as_decimal(row[1])
            if adv_id is None or amount is None:
                return None
            spend[adv_id] = amount
        return spend


class ReportsManagerOrdersAdapter:
    """Одна страница через ``ReportsManager``. Без sales и без записи."""

    def __init__(self, reports_manager: SupplierOrdersClient) -> None:
        self._reports = reports_manager

    async def get_supplier_orders(
        self,
        *,
        date_from: str,
        flag: int = 0,
    ) -> Sequence[object]:
        """Прокси ``get_supplier_orders`` с явным flag."""
        rows = await self._reports.get_supplier_orders(date_from=date_from, flag=flag)
        return list(rows or [])


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _as_decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (int, float, str, Decimal)):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
