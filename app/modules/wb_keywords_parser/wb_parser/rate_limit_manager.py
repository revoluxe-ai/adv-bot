from __future__ import annotations

from app.core.redis_manager_v2 import BaseRedisManager
from app.core.redis_manager_v2.mixins import RateLimitMixin


class ParserRateLimitRedisManager(RateLimitMixin, BaseRedisManager):
    prefix = "wb_rate_limit"

    def _get_key(self, ip: str) -> str:  # type: ignore[override]
        return f"{self.prefix}:{ip}"









