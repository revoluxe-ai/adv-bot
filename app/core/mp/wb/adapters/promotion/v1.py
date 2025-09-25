from __future__ import annotations

from typing import Any, Dict, List

from app.core.mp.wb.adapters.base import BaseAdapter


class PromotionV1Adapter(BaseAdapter):
    """Adapter for Promotion API v1. Stateful and scoped by shop_id/section/version."""

    def __init__(self, shop_id: str, version: str) -> None:
        super().__init__(shop_id=shop_id, section="promotion", version=version)

    async def get_min_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Return minimal bids mapping by nmid."""
        raise NotImplementedError

    async def get_current_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Return current bids mapping by nmid."""
        raise NotImplementedError

    async def update_bids(self, payload: Any) -> None:
        """Send bids update batch."""
        raise NotImplementedError
