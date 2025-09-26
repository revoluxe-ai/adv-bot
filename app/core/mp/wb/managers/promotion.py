from __future__ import annotations

from typing import Dict, List

from app.core.mp.wb.adapter_factory import WbApiAdapterFactory


class PromotionManager:
    """Proxy manager for promotion operations that delegates to adapters via factory."""

    def __init__(self, adapter_factory: WbApiAdapterFactory) -> None:
        self._adapter_factory = adapter_factory

    def _get_adapter(self, shop_id: str):
        return self._adapter_factory.get_adapter(shop_id, section="promotion", version=1)

    async def get_min_bids(self, shop_id: str, *, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        adapter = self._get_adapter(shop_id)
        return await getattr(adapter, "get_min_bids")(shop_id, adv_id=adv_id, nmids=nmids)

    async def get_current_bids(self, shop_id: str, *, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        adapter = self._get_adapter(shop_id)
        return await getattr(adapter, "get_current_bids")(shop_id, adv_id=adv_id, nmids=nmids)

    async def update_bids(self, shop_id: str, *, adv_id: int, nm_bids: List[Dict[str, int]]) -> None:
        adapter = self._get_adapter(shop_id)
        await getattr(adapter, "update_bids")(shop_id, adv_id=adv_id, nm_bids=nm_bids)
