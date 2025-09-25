from __future__ import annotations

from typing import Dict, List

from app.core.mp.wb.factories.adapter_factory import WbApiAdapterFactory


class PromotionManager:
    """Business-level PromotionManager that delegates to adapters via factory."""

    def __init__(self, adapter_factory: WbApiAdapterFactory) -> None:
        self.adapter_factory = adapter_factory

    async def get_min_bids(self, shop_id: str, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        adapter = self.adapter_factory.get_adapter(shop_id, "promotion", "v1")
        return await adapter.get_min_bids(adv_id, nmids)

    async def get_current_bids(self, shop_id: str, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        adapter = self.adapter_factory.get_adapter(shop_id, "promotion", "v1")
        return await adapter.get_current_bids(adv_id, nmids)

    async def update_bids(self, shop_id: str, payload: object) -> None:
        adapter = self.adapter_factory.get_adapter(shop_id, "promotion", "v1")
        await adapter.update_bids(payload)
