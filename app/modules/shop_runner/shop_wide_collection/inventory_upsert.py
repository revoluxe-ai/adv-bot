"""Upsert ``default_db.shop_campaign_inventory`` по WB discovery.

Spec: ``connected-shop-campaign-ad-data-collection`` (scenario «Завершённая
кампания в WB», design §D.1, §B lifecycle).
Placement: proposed decision
``decisions/shop-runner-shop-wide-collection/decision.md`` — writer живёт в
shop-runner, не в ``scripts/`` Job.
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.
Qualification: ``openspec/decisions/clickhouse-sql-database-qualification/decision.md``.

Задача 2.2. Модуль принимает уже открытый ClickHouse-клиент (parent handoff)
и не открывает ``get_clickhouse_client``. Tick shop-runner его не вызывает:
feature flag — задача 2.3, resolver маршрута — задача 3.1. Пустой ``route``
(``ROUTE_NOT_ASSIGNED``) не является MANAGED / UNMANAGED / UNKNOWN.

Единственный durable route epoch — колонка ``route_version`` этой таблицы.
Redis здесь не читается и не пишется.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

logger = logging.getLogger(__name__)

# Пустая строка: резолвер ещё не записал маршрут. Не путать с route UNKNOWN.
ROUTE_NOT_ASSIGNED = ""

# Коды статуса GET /api/advert/v2/adverts (GetAdvertsAdvertsItem):
# 9 активна, 11 на паузе, 7 завершена. Прочие коды (-1, 4, 8, …) — unknown.
_LIFECYCLE_BY_WB_STATUS: dict[int, str] = {
    9: "active",
    11: "paused",
    7: "finished",
}

_SELECT_CURRENT = """
SELECT
    adv_id,
    argMax(route, version) AS route,
    argMax(route_version, version) AS route_version,
    argMax(version, version) AS version,
    argMax(discovered_at, version) AS discovered_at
FROM default_db.shop_campaign_inventory
WHERE shop_id = %(shop_id)s
  AND adv_id IN %(adv_ids)s
GROUP BY adv_id
"""

_INSERT_ROW = """
INSERT INTO default_db.shop_campaign_inventory
    (shop_id, adv_id, nm_ids, wb_status, wb_lifecycle, route,
     discovered_at, last_seen_at, route_version, version)
VALUES
    (%(shop_id)s, %(adv_id)s, %(nm_ids)s, %(wb_status)s, %(wb_lifecycle)s,
     %(route)s, %(discovered_at)s, %(last_seen_at)s, %(route_version)s,
     %(version)s)
"""


class _QueryRows(Protocol):
    """Минимальный ответ ``client.query``: строки результата."""

    result_rows: Sequence[Sequence[object]]


class ShopCampaignInventoryClickHouse(Protocol):
    """Узкий CH-клиент inventory. Сессию открывает вызывающий код.

    ``query`` выполняет уже квалифицированный SQL. Соединение создаёт parent.
    """

    async def query(
        self,
        query: str,
        parameters: Mapping[str, object] | None = None,
    ) -> _QueryRows: ...


class _NmSetting(Protocol):
    """Товар в payload кампании WB: нужен только ``nm_id``."""

    @property
    def nm_id(self) -> int: ...


class WbAdvertDiscoveryItem(Protocol):
    """Фрагмент кампании WB API, достаточный для inventory discovery.

    Поля читаются как property, чтобы Sequence был ковариантным для тестовых
    и generated DTO.
    """

    @property
    def id(self) -> int: ...

    @property
    def status(self) -> int: ...

    @property
    def nm_settings(self) -> Sequence[_NmSetting]: ...


@dataclass(frozen=True)
class DiscoveredWbCampaign:
    """Кампания из WB discovery до записи inventory.

    ``wb_status`` — сырой код WB (``None``, если код отсутствует).
    ``nm_ids`` могут быть пустыми: пустой список не выкидывает кампанию.
    """

    adv_id: int
    wb_status: int | None
    nm_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        # bool является int; код статуса WB bool не бывает.
        if isinstance(self.adv_id, bool) or isinstance(self.wb_status, bool):
            raise TypeError("adv_id and wb_status must not be bool")
        if any(isinstance(nm_id, bool) for nm_id in self.nm_ids):
            raise TypeError("nm_ids must not contain bool")


@dataclass(frozen=True)
class ShopCampaignInventoryWrite:
    """Строка, которую upsert отправил в ``default_db.shop_campaign_inventory``.

    Поля совпадают с DDL задачи 2.1. ``route_version`` — epoch этой строки,
    не ключ Redis.
    """

    shop_id: str
    adv_id: int
    nm_ids: tuple[int, ...]
    wb_status: str
    wb_lifecycle: str
    route: str
    discovered_at: datetime
    last_seen_at: datetime
    route_version: int
    version: int


@dataclass(frozen=True)
class _CurrentInventory:
    """Текущая строка inventory по ``(shop_id, adv_id)`` после argMax."""

    route: str
    route_version: int
    version: int
    discovered_at: datetime


def map_wb_lifecycle(wb_status: object) -> str:
    """Ось ``wb_lifecycle``: active / paused / finished, иначе ``unknown``.

    Spec ``connected-shop-campaign-ad-data-collection``: неизвестное состояние
    нельзя молча считать отсутствием кампании. Эта функция только называет
    ось; отбрасывание строки делает не она, а запрет фильтра в upsert.

    Args:
        wb_status: сырой код статуса WB или иное значение payload.

    Returns:
        ``active``, ``paused``, ``finished`` или ``unknown``.
    """
    if isinstance(wb_status, bool) or not isinstance(wb_status, int):
        return "unknown"
    return _LIFECYCLE_BY_WB_STATUS.get(wb_status, "unknown")


def discovered_campaign_from_advert(
    item: WbAdvertDiscoveryItem,
) -> DiscoveredWbCampaign:
    """Снимает id, статус и nm_id с элемента WB discovery.

    Spec ``connected-shop-campaign-ad-data-collection``: discovery идёт из
    payload WB, без enrollment и ``bot_active``. Не фильтрует завершённые
    и неизвестные статусы.

    Args:
        item: элемент ``CampaignsInfoV2`` / совместимый объект.

    Returns:
        Кампания для ``upsert_discovered_shop_campaign_inventory``.
    """
    wb_status = None if isinstance(item.status, bool) else int(item.status)
    nm_ids = tuple(int(nm.nm_id) for nm in item.nm_settings)
    return DiscoveredWbCampaign(
        adv_id=int(item.id),
        wb_status=wb_status,
        nm_ids=nm_ids,
    )


def _as_ch_datetime(value: datetime) -> datetime:
    """Приводит момент к naive UTC: колонка inventory — ``DateTime``."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _require_shop_id(shop_id: str) -> str:
    if shop_id == "":
        raise ValueError("shop_id must be a non-empty string")
    return shop_id


def _dedupe_campaigns(
    campaigns: Sequence[DiscoveredWbCampaign],
) -> tuple[DiscoveredWbCampaign, ...]:
    """Последнее вхождение ``adv_id`` побеждает; порядок записи — по id."""
    by_id: dict[int, DiscoveredWbCampaign] = {}
    for campaign in campaigns:
        by_id[campaign.adv_id] = campaign
    return tuple(by_id[adv_id] for adv_id in sorted(by_id))


def _as_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} from inventory read must be int")
    return value


def _as_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} from inventory read must be str")
    return value


def _current_from_row(row: Sequence[object]) -> tuple[int, _CurrentInventory]:
    if len(row) != 5:
        raise TypeError("inventory select must return 5 columns")
    adv_id = _as_int(row[0], "adv_id")
    discovered_at = row[4]
    if not isinstance(discovered_at, datetime):
        raise TypeError("discovered_at from inventory read must be datetime")
    current = _CurrentInventory(
        route=_as_text(row[1], "route"),
        route_version=_as_int(row[2], "route_version"),
        version=_as_int(row[3], "version"),
        discovered_at=_as_ch_datetime(discovered_at),
    )
    return adv_id, current


def _next_route(
    current: _CurrentInventory | None,
    supplied_route: str | None,
) -> tuple[str, int]:
    """Сохраняет epoch, пока вызывающий не передал новый route.

    ``supplied_route is None`` значит «маршрута в этом вызове нет»: у новой
    строки остаётся ``ROUTE_NOT_ASSIGNED`` и ``route_version`` 0; у старой
    route и epoch не меняются. Явная строка, отличная от текущей, увеличивает
    ``route_version`` на 1. Число живёт только в колонке inventory.
    """
    if current is None:
        if supplied_route is None or supplied_route == ROUTE_NOT_ASSIGNED:
            return ROUTE_NOT_ASSIGNED, 0
        return supplied_route, 1
    route = current.route if supplied_route is None else supplied_route
    if route == current.route:
        return route, current.route_version
    return route, current.route_version + 1


def _build_write(
    *,
    shop_id: str,
    campaign: DiscoveredWbCampaign,
    current: _CurrentInventory | None,
    supplied_route: str | None,
    observed_at: datetime,
) -> ShopCampaignInventoryWrite:
    route, route_version = _next_route(current, supplied_route)
    version = 1 if current is None else current.version + 1
    discovered_at = observed_at if current is None else current.discovered_at
    wb_status = "" if campaign.wb_status is None else str(campaign.wb_status)
    return ShopCampaignInventoryWrite(
        shop_id=shop_id,
        adv_id=campaign.adv_id,
        nm_ids=campaign.nm_ids,
        wb_status=wb_status,
        wb_lifecycle=map_wb_lifecycle(campaign.wb_status),
        route=route,
        discovered_at=discovered_at,
        last_seen_at=observed_at,
        route_version=route_version,
        version=version,
    )


def _insert_parameters(row: ShopCampaignInventoryWrite) -> dict[str, object]:
    """Имена параметров совпадают с колонками INSERT inventory."""
    return {
        "shop_id": row.shop_id,
        "adv_id": row.adv_id,
        "nm_ids": list(row.nm_ids),
        "wb_status": row.wb_status,
        "wb_lifecycle": row.wb_lifecycle,
        "route": row.route,
        "discovered_at": row.discovered_at,
        "last_seen_at": row.last_seen_at,
        "route_version": row.route_version,
        "version": row.version,
    }


async def _load_current(
    client: ShopCampaignInventoryClickHouse,
    shop_id: str,
    adv_ids: Sequence[int],
) -> dict[int, _CurrentInventory]:
    result = await client.query(
        _SELECT_CURRENT,
        parameters={"shop_id": shop_id, "adv_ids": list(adv_ids)},
    )
    loaded: dict[int, _CurrentInventory] = {}
    for row in result.result_rows:
        adv_id, current = _current_from_row(row)
        loaded[adv_id] = current
    return loaded


async def upsert_discovered_shop_campaign_inventory(
    client: ShopCampaignInventoryClickHouse,
    *,
    shop_id: str,
    campaigns: Sequence[DiscoveredWbCampaign],
    routes: Mapping[int, str] | None = None,
    observed_at: datetime | None = None,
) -> tuple[ShopCampaignInventoryWrite, ...]:
    """Пишет все переданные WB-кампании в ``shop_campaign_inventory``.

    Spec ``connected-shop-campaign-ad-data-collection``, scenario «Завершённая
    кампания в WB»: завершённый lifecycle остаётся в discovery. Неизвестный
    код статуса становится ``wb_lifecycle=unknown`` и всё равно пишется.
    Фильтра по enrollment, ``bot_active`` и management нет.

    ``routes`` — необязательная подстановка от будущего резолвера (задача 3.1).
    Отсутствие ключа не удаляет кампанию. Модуль сам маршрут не выбирает.

    Args:
        client: уже открытый CH-клиент. Модуль соединение не создаёт.
        shop_id: магазин строки inventory.
        campaigns: кампании одного discovery. Пустой список не пишет SQL.
        routes: явный route по ``adv_id``. ``None`` и пропущенный ключ не
            затирают уже записанный route.
        observed_at: момент ``last_seen_at``. По умолчанию UTC now.

    Returns:
        Записанные строки в порядке ``adv_id``. Пустой discovery — ``()``.

    Raises:
        ValueError: пустой ``shop_id``.
        TypeError: битая форма кампании или строки SELECT.
        Exception: ошибка клиента пробрасывается, кампании не глотаются.
    """
    scoped_shop_id = _require_shop_id(shop_id)
    discovered = _dedupe_campaigns(campaigns)
    if not discovered:
        return ()
    moment = _as_ch_datetime(
        datetime.now(timezone.utc) if observed_at is None else observed_at
    )
    current_by_adv = await _load_current(
        client,
        scoped_shop_id,
        tuple(campaign.adv_id for campaign in discovered),
    )
    written: list[ShopCampaignInventoryWrite] = []
    for campaign in discovered:
        supplied = None if routes is None else routes.get(campaign.adv_id)
        row = _build_write(
            shop_id=scoped_shop_id,
            campaign=campaign,
            current=current_by_adv.get(campaign.adv_id),
            supplied_route=supplied,
            observed_at=moment,
        )
        await client.query(_INSERT_ROW, parameters=_insert_parameters(row))
        written.append(row)
    logger.info(
        "shop_campaign_inventory upsert shop_id=%s rows=%s",
        scoped_shop_id,
        len(written),
    )
    return tuple(written)
