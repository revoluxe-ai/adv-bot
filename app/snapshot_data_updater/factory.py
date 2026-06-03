"""Фабрики сборки ``SnapshotUpdater``: stub (по умолчанию) и live.

Точка выбора режима
-------------------
``build_snapshot_updater()`` смотрит на ``config.use_live_updater``:

- ``False`` → ``build_snapshot_updater_stub()`` — без БД, для тестов и dev;
- ``True`` → ``build_snapshot_updater_live()`` — реальный read-only I/O.

См. docstring ``SnapshotUpdaterConfig.use_live_updater`` в ``config.py``.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.snapshot_data_updater.assembler import AdvDataSnapshotAssembler
from app.snapshot_data_updater.cache.redis_adv_data_snapshot_store import (
    RedisAdvDataSnapshotStore,
)
from app.snapshot_data_updater.collector import AdvDataSnapshotCollector
from app.snapshot_data_updater.config import SnapshotUpdaterConfig, get_snapshot_config
from app.snapshot_data_updater.providers.clickhouse_provider import (
    ClickHouseSnapshotProviderLive,
    StubClickHouseSnapshotProvider,
)
from app.snapshot_data_updater.providers.postgres_provider import (
    PostgresSnapshotProviderLive,
    StubPostgresSnapshotProvider,
)
from app.snapshot_data_updater.providers.redis_provider import (
    RedisSnapshotProviderLive,
    StubRedisSnapshotProvider,
)
from app.snapshot_data_updater.resource_queue import build_resource_queue_manager
from app.snapshot_data_updater.services.calculated_keywords_warmup import (
    CalculatedKeywordsWarmupService,
)
from app.snapshot_data_updater.shop_discovery import RedisActiveShopIdDiscovery
from app.snapshot_data_updater.updater import (
    SnapshotUpdater,
    StubShopIdDiscovery,
)


def build_snapshot_updater_live(
    *,
    shop_ids: Sequence[str] | None = None,
    config: SnapshotUpdaterConfig | None = None,
) -> SnapshotUpdater:
    """Собирает live-стек: PG + Redis + CH + warmup + запись snapshot в Redis.

    Args:
        shop_ids: если задан — ``StubShopIdDiscovery`` (smoke / live-once);
            иначе — ``RedisActiveShopIdDiscovery`` (``SMEMBERS active_shops``,
            см. ``shop_discovery.py``).
        config: переопределение флагов; по умолчанию ``DEFAULT_CONFIG``.

    Returns:
        Настроенный ``SnapshotUpdater`` с ``use_live_updater``-эквивалентным стеком.

    Side effects:
        Read/write Redis (новый namespace), read PG/CH, warmup пишет legacy hash
        ``calculated_keywords:{adv_id}`` через ``get_good_bad_phrases``.
    """
    cfg = config or get_snapshot_config()
    queues = build_resource_queue_manager(cfg)
    warmup = CalculatedKeywordsWarmupService(config=cfg, resource_queues=queues)
    collector = AdvDataSnapshotCollector(
        postgres=PostgresSnapshotProviderLive(),
        clickhouse=ClickHouseSnapshotProviderLive(),
        redis=RedisSnapshotProviderLive(),
        assembler=AdvDataSnapshotAssembler(),
        resource_queues=queues,
        keywords_warmup=warmup,
        schema_version=cfg.snapshot_schema_version,
        snapshot_ttl_sec=cfg.snapshot_ttl_sec,
    )
    discovery: StubShopIdDiscovery | RedisActiveShopIdDiscovery
    if shop_ids is not None:
        discovery = StubShopIdDiscovery(shop_ids)
    else:
        discovery = RedisActiveShopIdDiscovery()
    return SnapshotUpdater(
        collector=collector,
        store=RedisAdvDataSnapshotStore(ttl_sec=cfg.snapshot_ttl_sec, no_op=False),
        shop_discovery=discovery,
        resource_queues=queues,
        config=cfg,
    )


def build_snapshot_updater(
    *,
    shop_ids: Sequence[str] | None = None,
    config: SnapshotUpdaterConfig | None = None,
) -> SnapshotUpdater:
    """Главная фабрика: stub или live по ``use_live_updater`` / env.

    По умолчанию (``use_live_updater=False``) — stub, безопасно для CI и локального
    ``updater.py`` без настроенных БД.

    Args:
        shop_ids: опциональный фиксированный список для discovery (тесты).
        config: если ``use_live_updater=True`` — live-стек, иначе stub.

    Returns:
        Готовый ``SnapshotUpdater``.
    """
    cfg = config or get_snapshot_config()
    if cfg.use_live_updater:
        return build_snapshot_updater_live(shop_ids=shop_ids, config=cfg)
    from app.snapshot_data_updater.updater import build_snapshot_updater_stub

    return build_snapshot_updater_stub(shop_ids=shop_ids, config=cfg)
