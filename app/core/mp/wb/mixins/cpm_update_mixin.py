from __future__ import annotations

import logging

from ._adapter_mixins.mixins.promotion_adapter_mixin import PromotionAdapterProtocol
from .base_wb_api_protocol import BaseWBApiProtocol
from app.shared.application.commands.search_adv_bid_update import UpdateBidsForShopCommand

logger = logging.getLogger(__name__)


class CPMUpdateMixin(BaseWBApiProtocol):
    async def update_bids_for_shop(
        self,
        update_cpms_for_shop_command: UpdateBidsForShopCommand,
    ) -> None:
        adapter: PromotionAdapterProtocol = self.adapter_manager.get_adapter(
            self.shop_id,
            "promotion",
            version=1,
        )
        await adapter.update_cpms_in_search_advs(update_cpms_for_shop_command)
