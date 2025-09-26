from __future__ import annotations

from typing import TYPE_CHECKING, List, Dict, Any, cast

if TYPE_CHECKING:
    from app.core.mp.wb.base_wb_api import BaseWBApi
    from app.core.mp.wb.adapters.promotion.promotion_adapter_protocol import PromotionAdapterProtocol


class BidUpdateMixin:

    async def update_bids(self: BaseWBApi, *, adv_id: int, nmids_bids: List[Dict[str, Any]]) -> None:
        """Delegate to promotion adapter to update bids."""
        promotion_adapter = self.get_adapter(section="promotion", version=1)
        typed_adapter = cast(PromotionAdapterProtocol, promotion_adapter)
        await typed_adapter.update_bids(adv_id=adv_id, nmids_bids=nmids_bids)


