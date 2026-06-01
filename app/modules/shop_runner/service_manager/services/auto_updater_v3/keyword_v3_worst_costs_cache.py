"""Redis-кеш worst CPO M/O/C по РК для UI и повторных чтений на тике.

Ключ ``v3_worst_costs:{adv_id}`` — JSON ``{mode_name: cost}``. Пересчитывается при
``LadderInputs.from_contexts`` (updater / карточка Telegram).
"""

from __future__ import annotations

import json
import logging

from app.core.redis_manager import RedisManager
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
)

logger = logging.getLogger(__name__)

_WORST_COSTS_TTL_SEC = 600


class V3WorstCostsRedisCache(RedisManager):
    """Кеш per-mode worst (max predicted CPA) по ключам РК с валидной CH-матрицей."""

    @staticmethod
    def _key(adv_id: int) -> str:
        return f"v3_worst_costs:{adv_id}"

    async def get_worst_costs(
        self, adv_id: int
    ) -> dict[AggressionTargetMode, float] | None:
        """Прочитать кеш или ``None``, если нет / битый JSON."""
        raw = await self.client.get(self._key(adv_id))
        if raw is None:
            return None
        try:
            payload = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
            return {
                AggressionTargetMode[k]: float(v)
                for k, v in payload.items()
                if k in AggressionTargetMode.__members__
            }
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("v3 worst_costs cache corrupt adv_id=%s", adv_id)
            return None

    async def set_worst_costs(
        self,
        adv_id: int,
        worst_costs: dict[AggressionTargetMode, float],
    ) -> None:
        """Сохранить worst на ``_WORST_COSTS_TTL_SEC`` секунд."""
        if not worst_costs:
            return
        payload = {mode.name: cost for mode, cost in worst_costs.items()}
        await self.client.set(
            self._key(adv_id),
            json.dumps(payload),
            ex=_WORST_COSTS_TTL_SEC,
        )
