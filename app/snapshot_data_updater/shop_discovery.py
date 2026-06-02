"""Discovery активных ``shop_id`` для global tick ``SnapshotUpdater``.

Live (daemon / ``build_snapshot_updater_live`` без ``shop_ids``)
-----------------------------------------------------------------
``RedisActiveShopIdDiscovery.discover_shop_ids()`` → ``SMEMBERS active_shops`` в Redis.

Set наполняет shop-runner (каждые ~15 с)::

    app/modules/shop_runner/shop_run_worker/update_active_shop_ids_in_redis.py
    → ``select(WBCabinet.shop_id).where(WBCabinet.active)`` (+ whitelist/blacklist)
    → ``RedisShopManager.update_active_shops``

То есть в tick попадают магазины из **того же Redis**, что и воркеры shop_runner,
а не отдельный PG-запрос snapshot updater'а.

Сбор по одному shop (``PostgresSnapshotProviderLive``)
------------------------------------------------------
Внутри ``RefreshShopSnapshotTask`` только РК с ``AdvSetting.bot_active is True``
и ``active_status != 'done'`` — магазин без bot_active РК даст пустой batch.

Smoke / один магазин
--------------------
``StubShopIdDiscovery`` или ``cli live-once --shop-id`` — фиксированный ``shop_id``.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from app.modules.shop_runner.shop_id_filters import filter_shop_ids
from app.modules.shop_runner.shop_run_worker.redis_manager.redis_manager import (
    RedisShopManager,
)

logger = logging.getLogger(__name__)


class RedisActiveShopIdDiscovery:
    """Live discovery: SMEMBERS ``active_shops``."""

    def __init__(self, redis_manager: RedisShopManager | None = None) -> None:
        self._redis = redis_manager or RedisShopManager()

    async def discover_shop_ids(self) -> Sequence[str]:
        """Возвращает отсортированный список shop_id из Redis."""
        members = await self._redis._client.smembers(self._redis._active_shops_set_name)
        if not members:
            return []
        out: list[str] = []
        for m in members:
            if isinstance(m, bytes):
                out.append(m.decode())
            else:
                out.append(str(m))
        filtered = filter_shop_ids(out)
        if len(filtered) != len(out):
            logger.debug(
                "RedisActiveShopIdDiscovery filtered shops %d -> %d "
                "(SHOP_FILTER_LIST / SHOP_EXCLUDE_LIST)",
                len(out),
                len(filtered),
            )
        return sorted(filtered)
