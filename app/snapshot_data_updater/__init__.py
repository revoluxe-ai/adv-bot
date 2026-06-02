"""Пакет ``snapshot_data_updater`` — централизованные снимки данных РК.

Быстрый старт
-------------
- **Stub (по умолчанию)**: ``use_live_updater=False`` — без Postgres/Redis/CH.
  ``build_snapshot_updater_stub()`` или ``build_snapshot_updater()``.
- **Live**: ``SNAPSHOT_UPDATER_USE_LIVE=1`` → ``build_snapshot_updater_live()``.

Подробнее про ``use_live_updater`` — module docstring в ``config.py``.
"""

from app.snapshot_data_updater.collector import AdvDataSnapshotCollector
from app.snapshot_data_updater.dto import (
    AdvDataSnapshotDTO,
    CalculatedKeywordSnapshotDTO,
    ShopAdvSnapshotBatchDTO,
)
from app.snapshot_data_updater.factory import (
    build_snapshot_updater,
    build_snapshot_updater_live,
)
from app.snapshot_data_updater.protocols import AdvDataSnapshotStore
from app.snapshot_data_updater.refresh_shop_snapshot_task import (
    RefreshShopSnapshotTask,
)
from app.snapshot_data_updater.updater import (
    SnapshotUpdater,
    build_snapshot_updater_stub,
)

__all__ = [
    "AdvDataSnapshotCollector",
    "AdvDataSnapshotDTO",
    "AdvDataSnapshotStore",
    "CalculatedKeywordSnapshotDTO",
    "RefreshShopSnapshotTask",
    "ShopAdvSnapshotBatchDTO",
    "SnapshotUpdater",
    "build_snapshot_updater",
    "build_snapshot_updater_live",
    "build_snapshot_updater_stub",
]
