from __future__ import annotations

from typing import Dict, List, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .adapters.promotion_v1_adapter import PromotionV1Adapter

from .factories.adapter_factory import WbApiAdapterFactory


class PromotionManager:
    """Proxy manager for promotion operations that delegates to adapters via factory."""

    def __init__(self, adapter_factory: WbApiAdapterFactory) -> None:
        """Initialize with adapter factory for DI.
        
        Args:
            adapter_factory: Factory to obtain adapters for specific shop/section/version
        """
        self._adapter_factory = adapter_factory

    async def get_min_bids(self, shop_id: str, *, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Get minimum bids for given nmids in advertisement.
        
        Args:
            shop_id: Shop identifier
            adv_id: Advertisement ID
            nmids: List of product IDs (nmids)
            
        Returns:
            Dictionary mapping nmid to minimum bid
        """
        adapter = self._adapter_factory.get_adapter(shop_id, section="promotion", version="v1")
        # Use getattr to call method dynamically to avoid type checker issues
        return await getattr(adapter, "get_min_bids")(shop_id, adv_id=adv_id, nmids=nmids)

    async def get_current_bids(self, shop_id: str, *, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Get current bids for given nmids in advertisement.
        
        Args:
            shop_id: Shop identifier
            adv_id: Advertisement ID
            nmids: List of product IDs (nmids)
            
        Returns:
            Dictionary mapping nmid to current bid
        """
        adapter = self._adapter_factory.get_adapter(shop_id, section="promotion", version="v1")
        # Use getattr to call method dynamically to avoid type checker issues
        return await getattr(adapter, "get_current_bids")(shop_id, adv_id=adv_id, nmids=nmids)

    async def update_bids(self, shop_id: str, *, adv_id: int, nm_bids: List[Dict[str, int]]) -> None:
        """Update bids for products in advertisement.
        
        Args:
            shop_id: Shop identifier
            adv_id: Advertisement ID
            nm_bids: List of dicts with 'nm' (nmid) and 'cpm' (bid) keys
        """
        adapter = self._adapter_factory.get_adapter(shop_id, section="promotion", version="v1")
        # Use getattr to call method dynamically to avoid type checker issues
        await getattr(adapter, "update_bids")(shop_id, adv_id=adv_id, nm_bids=nm_bids)