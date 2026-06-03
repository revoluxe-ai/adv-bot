"""Протоколы (контракты) snapshot_data_updater — только read-only.

Реализации
----------
- **Stub** — фикстуры для unit-тестов, без I/O (default при ``use_live_updater=False``).
- **Live** — ``*ProviderLive`` в ``providers/`` (PG/Redis/CH).

``shop_runner`` не обязан импортировать этот пакет; consumers ходят через adapters
по feature flags.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.snapshot_data_updater.dto import (
    AdvSettingsSnapshotDTO,
    CalculatedKeywordSnapshotDTO,
    MinBidsSnapshotDTO,
    PlanFactSnapshotDTO,
    ShopAdvSnapshotBatchDTO,
)


@runtime_checkable
class ShopIdDiscovery(Protocol):
    """Источник списка shop_id для global tick ``SnapshotUpdater``."""

    async def discover_shop_ids(self) -> Sequence[str]:
        """Возвращает shop_id, для которых нужно обновить snapshot."""


@runtime_checkable
class PostgresSnapshotProvider(Protocol):
    """Read-only Postgres: active adv и настройки."""

    async def fetch_active_adv_settings(
        self, shop_id: str
    ) -> list[AdvSettingsSnapshotDTO]:
        """Список active ``bot_active`` кампаний магазина."""


@runtime_checkable
class ClickHouseSnapshotProvider(Protocol):
    """Read-only ClickHouse: batch-агрегаты для shop."""

    async def fetch_plan_facts(
        self, shop_id: str, adv_ids: Sequence[int]
    ) -> dict[int, PlanFactSnapshotDTO]:
        """Карта adv_id → plan/fact; пустая при отсутствии данных."""


@runtime_checkable
class RedisSnapshotProvider(Protocol):
    """Read-only Redis: legacy calculated_keywords и min_bids v2."""

    async def fetch_keywords(
        self, adv_id: int
    ) -> list[CalculatedKeywordSnapshotDTO]:
        """Keywords для adv; пустой список при cache miss."""

    async def fetch_min_bids(self, adv_id: int) -> MinBidsSnapshotDTO | None:
        """Min bids одной adv или None при miss."""


@runtime_checkable
class AdvDataSnapshotStore(Protocol):
    """Запись/чтение готовых пакетов (Redis ``adv_snapshot:v1:...``)."""

    async def save(self, batch: ShopAdvSnapshotBatchDTO) -> None:
        """Сохраняет пакет снимков магазина (batch + per-adv keys)."""
