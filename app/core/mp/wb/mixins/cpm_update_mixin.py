from __future__ import annotations

from typing import cast

from app.core.mp.wb.adapters.promotion.promotion_adapter_protocol import PromotionAdapterProtocol
from app.shared.application.commands.search_adv_bid_update import UpdateBidsForShopCommand


class CPMUpdateMixin:
    """Mixin that routes CPM update commands through the promotion adapter obtained from BaseWBApi."""

    promotion_adapter_version: str = "v1"

    def _promotion_adapter(self) -> PromotionAdapterProtocol:
        adapter = self.get_adapter("promotion", self.promotion_adapter_version)
        return cast(PromotionAdapterProtocol, adapter)

    async def update_bids_for_shop(
        self,
        update_cpms_for_shop_command: UpdateBidsForShopCommand,
    ) -> None:
        adapter = self._promotion_adapter()
        await adapter.update_cpms_in_search_advs(update_cpms_for_shop_command)

