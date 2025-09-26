from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Iterable, Mapping

from app.core.mp.wb.adapters.auth_client_mixin import AdapterAuthClient
from app.core.mp.wb.adapters.base import BaseAdapter
from app.core.mp.wb.decorators.rate_limit import rate_limit_decorator
from app.core.mp.wb.decorators.retry import retry_decorator
from app.core.mp.wb.rate_limit.storage import RateLimitStorage
# Import the generated client for promotion v1
from app.core.mp.wb.adapters.promotion.v1.client import Client as PromotionClientV1


class PromotionAdapterV1(BaseAdapter):
    """Adapter for Wildberries Promotion API v1."""

    def __init__(self, shop_id: str, client: AdapterAuthClient, rate_limit_storage: RateLimitStorage) -> None:
        super().__init__(shop_id, rate_limit_storage)
        # Ensure the client is an instance of the generated client mixed with AdapterAuthClient
        # For runtime, we assume it's already properly typed by ClientFactory
        self._client: PromotionClientV1 = client # type: ignore
        self.section = "promotion"
        self.version = 1

    @retry_decorator()
    @rate_limit_decorator(limits=5, interval=1.0) # Example limits, adjust as needed
    async def get_min_bids(
        self,
        adv_id: int,
        nmids: Sequence[int] | Iterable[int],
    ) -> Dict[int, int]:
        return await self._client.post_adv_v1_bids_min(adv_id=adv_id, nmids=list(nmids))

    @retry_decorator()
    @rate_limit_decorator(limits=5, interval=1.0) # Example limits, adjust as needed
    async def get_current_bids(
        self,
        adv_id: int,
        nmids: Sequence[int] | Iterable[int],
    ) -> Dict[int, int]:
        return await self._client.get_adv_v1_auction_adverts(adv_id=adv_id, nmids=list(nmids))

    @retry_decorator()
    @rate_limit_decorator(limits=5, interval=1.0) # Example limits, adjust as needed
    async def update_bids(
        self,
        adv_id: int,
        nm_bids: Sequence[Mapping[str, int]] | Iterable[Mapping[str, int]],
    ) -> None:
        await self._client.patch_adv_v1_bids(adv_id=adv_id, request_body=list(nm_bids))

