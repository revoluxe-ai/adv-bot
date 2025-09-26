from __future__ import annotations

from typing import Dict, List, Protocol


class PromotionAdapterProtocol(Protocol):
    """Protocol defining the interface for Promotion API adapters."""

    async def get_min_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Return minimal bids mapping by nmid."""
        ...

    async def get_current_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Return current bids mapping by nmid."""
        ...

    async def update_bids(self, adv_id: int, nm_bids: List[dict[str, int]]) -> None:
        """Send bids update batch for specified advert."""
        ...
