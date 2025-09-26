from __future__ import annotations

from typing import ClassVar, Dict, List

from app.core.mp.wb.adapters.base_adapter import WBBaseAdapter
from app.core.mp.wb.decorators.rate_limit import rate_limit_decorator
from app.core.mp.wb.rate_limit.config import RateLimitConfig
from app.core.mp.wb.rate_limit.storage import RateLimitStorage


class PromotionAdapterV1(WBBaseAdapter):
    section: ClassVar[str] = "promotion"
    version: ClassVar[str] = "v1"

    # Base throttle for the whole promotion v1 section.
    section_rate_limit: ClassVar[RateLimitConfig] = RateLimitConfig(
        requests_per_interval=20,
        interval_seconds=1.0,
        burst=20,
    )


    def __init__(
        self,
        shop_id: str,
        *,
        rate_limit_storage: RateLimitStorage | None = None,
    ) -> None:
        super().__init__(shop_id, rate_limit_storage=rate_limit_storage)

    def get_rate_limit_config(self, raw_method: str) -> RateLimitConfig | None:
        return self.section_rate_limit

    @rate_limit_decorator(limits=8, interval=1.0)
    @auth_decorator()
    async def get_min_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Fetch minimal bids for a promotion campaign. Implementation TBD."""
        raise NotImplementedError
