from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, cast

if TYPE_CHECKING:
    from app.core.mp.wb.base_wb_api import BaseWBApi
    from app.core.mp.wb.adapters.promotion.promotion_adapter_protocol import PromotionAdapterProtocol


class CurrentBidMixin:
    async def get_current_bids(self: BaseWBApi, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Delegate to promotion adapter to get current bids."""
        promotion_adapter = self.get_adapter(section="promotion", version=1)
        typed_adapter = cast(PromotionAdapterProtocol, promotion_adapter)
        return await typed_adapter.get_current_bids(adv_id=adv_id, nmids=nmids)
