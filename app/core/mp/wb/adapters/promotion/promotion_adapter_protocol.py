from __future__ import annotations

from typing import Protocol
from typing import Any, Dict, List


class PromotionAdapterProtocol(Protocol):
    """Protocol defining the interface for Promotion API adapters."""

    async def get_min_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Return minimal bids mapping by nmid."""
        ...

    async def get_current_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Return current bids mapping by nmid."""
        ...

    async def update_bids(self, payload: Any) -> None:
        """Send bids update batch."""
        ...

    async def update_cpms_in_search_advs(self, command: Any) -> None:
        """Update CPM values in search advertisements."""
        ...
