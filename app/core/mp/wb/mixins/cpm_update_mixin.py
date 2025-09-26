from __future__ import annotations

from ..adapters.promotion.v1 import PromotionV1Adapter

"""Миксин для обновления CPM ставок."""

import logging
from .base_wb_api_protocol import  BaseWBApiProtocol

logger = logging.getLogger(__name__)


class CPMUpdateMixin(BaseWBApiProtocol):

    async def def update_bids_for_shop(self: BaseWBApiProtocol, update_cpms_for_shop_command: UpdateBIDForShopCommand ) -> None:
        adapter: PromotionAdapterProtocol = self.adapter_manager.get_adapter(self.shop_id,
                                                                             'promotion',
                                                                             version=1)
        await adapter.update_cpms_in_search_advs(update_cpms_for_shop_command)


