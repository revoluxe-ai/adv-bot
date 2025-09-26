from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, cast

if TYPE_CHECKING:
    from app.core.mp.wb.base_wb_api import BaseWBApi
    from app.core.mp.wb.adapters.promotion.promotion_adapter_protocol import PromotionAdapterProtocol


class MinBidMixin:
    async def get_min_bids(self: BaseWBApi, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Delegate to promotion adapter to get min bids."""
        promotion_adapter = self.get_adapter(section="promotion", version=1)
        typed_adapter = cast(PromotionAdapterProtocol, promotion_adapter)
        return await typed_adapter.get_min_bids(adv_id=adv_id, nmids=nmids)


