"""In-memory результат одного PG-запроса на shop (не сериализуется в Redis).

``PostgresShopSnapshotLoad`` передаётся из postgres provider в collector/warmup.
``complex_advs_by_id`` содержит ORM-bound ``ComplexAdv`` только в live-процессе.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.snapshot_data_updater.dto import AdvSettingsSnapshotDTO


@dataclass
class PostgresShopSnapshotLoad:
    """Настройки DTO + ComplexAdv для keyword warmup."""

    shop_id: str
    settings: list[AdvSettingsSnapshotDTO] = field(default_factory=list)
    complex_advs_by_id: dict[int, ComplexAdv] = field(default_factory=dict)
