"""Per-shop feature flag dual-path сбора shop-wide.

Spec: ``connected-shop-campaign-ad-data-collection`` (временный dual-path).
Debt: ``openspec/architectural-debt/TEMPORARY_DUAL_CAMPAIGN_COLLECTION.md``.
Decision: ``openspec/changes/shop-wide-campaign-data-collection/decisions/shop-runner-shop-wide-collection/decision.md``.

Флаг живёт в shop-runner и читается из env на вызове. Выключенное состояние
и rollback оставляют managed-only tick и не удаляют историю ClickHouse.
Включённый магазин получает ``DUAL_PATH_ACTIVE``: unmanaged slice стартует
только через ``CoroutinesManager.collect_shop_wide_campaign_advertising``
после resolver/inventory prerequisites (задачи 3.1, 8.1). Единственный
durable epoch — ``shop_campaign_inventory.route_version``; Redis не становится
вторым источником.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

ROUTE_EPOCH_SOURCE = "shop_campaign_inventory.route_version"
_ENV_ENABLED = "SHOP_WIDE_COLLECTION_ENABLED"
_ENV_SHOP_IDS = "SHOP_WIDE_COLLECTION_SHOP_IDS"
_TRUTHY = frozenset({"1", "true", "yes", "on"})


class ShopWideCollectionMode(Enum):
    """Режим tick для одного магазина shop-runner.

    ``MANAGED_ONLY`` — флаг выключен или магазин не в allowlist: существующий
    managed RECORD без unmanaged slice.
    ``DUAL_PATH_ACTIVE`` — флаг включён: shop-runner ставит unmanaged tick
    (``collect_shop_wide_campaign_advertising``) параллельно managed RECORD.
    """

    MANAGED_ONLY = "managed_only"
    DUAL_PATH_ACTIVE = "dual_path_active"


class ShopWideUnmanagedSliceNotReady(Exception):
    """Unmanaged slice с нарушенным fail-closed снимком или без prerequisites.

    Spec запрещает удаление истории CH, запись route epoch в Redis и запуск
    collector при invalid gate snapshot. Исключение поднимается до WB/CH/PG write.
    """

    def __init__(self, shop_id: str) -> None:
        self.shop_id = shop_id
        super().__init__(
            "unmanaged shop-wide slice is fail-closed for invalid gate "
            f"snapshot shop_id={shop_id}"
        )


@dataclass(frozen=True)
class ShopWideCollectionDecision:
    """Решение флага для одного ``shop_id``.

    Поля описывают отказ от side effect, а не строку inventory. История CH
    сохраняется и при rollback. ``route_epoch_source`` называет единственный
    допустимый SoT и не означает, что этот вызов прочитал таблицу.
    """

    shop_id: str
    mode: ShopWideCollectionMode
    unmanaged_slice_entered: bool
    clickhouse_history_retained: bool
    deletes_clickhouse_history: bool
    route_epoch_consulted: bool
    route_epoch_source: str
    redis_route_epoch_written: bool


def _parse_truthy(raw: str | None) -> bool:
    """Пустое и неизвестное значение env — выключено."""
    if raw is None:
        return False
    return raw.strip().lower() in _TRUTHY


def _parse_shop_ids(raw: str | None) -> frozenset[str]:
    """CSV ``shop_id``. Пустые токены не открывают ни один магазин."""
    if raw is None or not raw.strip():
        return frozenset()
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def _decision(
    shop_id: str, mode: ShopWideCollectionMode
) -> ShopWideCollectionDecision:
    """Собрать отказной снимок: без unmanaged, без удаления CH, без Redis epoch."""
    return ShopWideCollectionDecision(
        shop_id=shop_id,
        mode=mode,
        unmanaged_slice_entered=False,
        clickhouse_history_retained=True,
        deletes_clickhouse_history=False,
        route_epoch_consulted=False,
        route_epoch_source=ROUTE_EPOCH_SOURCE,
        redis_route_epoch_written=False,
    )


def evaluate_shop_wide_collection(shop_id: str) -> ShopWideCollectionDecision:
    """Решить режим dual-path для магазина.

    Spec ``connected-shop-campaign-ad-data-collection``, design Migration Plan.
    Master ``SHOP_WIDE_COLLECTION_ENABLED`` и allowlist
    ``SHOP_WIDE_COLLECTION_SHOP_IDS`` оба обязательны для запроса dual-path.
    Иначе режим managed-only. Включённый магазин получает
    ``DUAL_PATH_ACTIVE``; фактический старт unmanaged — в tick wiring §8.1.

    Args:
        shop_id: идентификатор магазина shop-runner. Пустая строка не матчится
            с allowlist.

    Returns:
        Снимок без обращений к ClickHouse, Redis, WB и PG.
    """
    enabled = _parse_truthy(os.environ.get(_ENV_ENABLED))
    allowed = _parse_shop_ids(os.environ.get(_ENV_SHOP_IDS))
    if shop_id and enabled and shop_id in allowed:
        return _decision(shop_id, ShopWideCollectionMode.DUAL_PATH_ACTIVE)
    return _decision(shop_id, ShopWideCollectionMode.MANAGED_ONLY)


def enforce_shop_wide_collection_fail_closed(
    decision: ShopWideCollectionDecision,
) -> ShopWideCollectionDecision:
    """Остановить срез, если снимок просит unmanaged slice или вредный write.

    Spec запрещает старт неполного unmanaged collector, удаление истории CH
    и второй SoT epoch в Redis. Вызывается из tick до TaskGroup.

    Raises:
        ShopWideUnmanagedSliceNotReady: снимок нарушает fail-closed инвариант.
    """
    if (
        decision.unmanaged_slice_entered
        or decision.deletes_clickhouse_history
        or decision.redis_route_epoch_written
        or not decision.clickhouse_history_retained
    ):
        raise ShopWideUnmanagedSliceNotReady(decision.shop_id)
    return decision


def apply_shop_wide_collection_gate(shop_id: str) -> ShopWideCollectionDecision:
    """Применить per-shop флаг в tick shop-runner.

    Spec ``connected-shop-campaign-ad-data-collection``. OFF и rollback не
    меняют managed RECORD и не трогают уже записанную историю ClickHouse.
    ON активирует dual-path scheduling; route epoch читается в unmanaged tick
    через inventory (задача 8.1), не через Redis.

    Returns:
        Fail-closed снимок. Не пишет CH, Redis, AdvSetting и WB management.
    """
    return enforce_shop_wide_collection_fail_closed(
        evaluate_shop_wide_collection(shop_id)
    )
