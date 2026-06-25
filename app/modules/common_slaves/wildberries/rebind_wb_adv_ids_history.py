"""Redis-хранилище WB adv_id, снятых при ручной перепривязке кампаний.

Нужно для дневной статистики в боте: в ClickHouse метрики остаются под старым
adv_id, а в Postgres уже новый ID.
"""

from __future__ import annotations

import logging
from typing import Literal

from app.core.redis_manager.base_redis_manager import BaseRedis

logger = logging.getLogger(__name__)

RebindAdvKind = Literal["auto", "auction"]


class RebindWbAdvIdsHistory(BaseRedis):
    """Множества прошлых auto/search adv_id по ``AdvSetting.id`` (PK)."""

    prefix = "adv_setting_rebind_wb_ids"

    def _key(self, adv_setting_id: int, kind: RebindAdvKind) -> str:
        return f"{self.prefix}:{adv_setting_id}:{kind}"

    async def append(self, adv_setting_id: int, kind: RebindAdvKind, adv_id: int) -> None:
        """Добавляет снятый WB adv_id в историю перепривязок."""
        key = self._key(adv_setting_id, kind)
        await self.client.sadd(key, str(adv_id))  # pyright: ignore[reportUnknownMemberType]

    async def get_ids(
        self, adv_setting_id: int, kind: RebindAdvKind
    ) -> set[int]:
        """Возвращает множество сохранённых adv_id для слота auto или auction."""
        key = self._key(adv_setting_id, kind)
        raw = await self.client.smembers(key)  # pyright: ignore[reportUnknownMemberType]
        out: set[int] = set()
        for item in raw:
            try:
                out.add(int(item))
            except (TypeError, ValueError):
                logger.warning("rebind history: skip invalid adv_id %r", item)
        return out


_history = RebindWbAdvIdsHistory()


async def append_rebound_wb_adv_id(
    adv_setting_id: int, kind: RebindAdvKind, adv_id: int
) -> None:
    """Сохраняет adv_id, заменённый при перепривязке."""
    await _history.append(adv_setting_id, kind, adv_id)


async def get_rebound_wb_adv_ids(
    adv_setting_id: int,
) -> tuple[set[int], set[int]]:
    """Возвращает (исторические auto adv_id, исторические auction adv_id)."""
    auto_ids = await _history.get_ids(adv_setting_id, "auto")
    auction_ids = await _history.get_ids(adv_setting_id, "auction")
    return auto_ids, auction_ids
