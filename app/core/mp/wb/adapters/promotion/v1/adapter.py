from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class GetMinBidsCommand:
    adv_id: int
    nmids: List[int]
    payment_type: Optional[str] = None
    placement_types: Optional[List[str]] = None


@dataclass
class GetCurrentBidsCommand:
    adv_id: int
    nmids: List[int]


@dataclass
class UpdateBidsCommand:
    adv_id: int
    nm_bids: List[dict]


from .methods.sozdanie_kampanij.post_adv_v0_bids_min import PostAdvV0BidsMinResponse200
from app.core.mp.wb.adapters.base_adapter import WBBaseAdapter
from app.core.mp.wb.decorators.auth import auth_for_adapter
from typing import ClassVar
from app.core.mp.wb.decorators.rate_limit import rate_limit_decorator
from app.core.mp.wb.rate_limit.storage import RateLimitConfig



class PromotionAdapterV1(WBBaseAdapter):
    section: ClassVar[str] = "promotion"
    version: ClassVar[int] = 1

    # Base throttle for the whole promotion v1 section.
    section_rate_limit: ClassVar[RateLimitConfig] = RateLimitConfig(
        requests_per_interval=20,
        interval_seconds=1.0,
        burst=20,
    )

    @rate_limit_decorator(limits=8, interval=1.0)
    @auth_for_adapter()
    async def get_min_bids(self, client, get_min_bids_command) -> dict[int, int]:
        from .methods.sozdanie_kampanij import post_adv_v0_bids_min
        response: PostAdvV0BidsMinResponse200 = await post_adv_v0_bids_min(
            client,
            adv_id=get_min_bids_command.adv_id,
            nmids=get_min_bids_command.nmids,
            payment_type=get_min_bids_command.payment_type,
            placement_types=get_min_bids_command.placement_types,
        )

