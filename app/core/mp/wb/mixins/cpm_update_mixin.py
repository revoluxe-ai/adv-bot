from __future__ import annotations

import logging

from ._adapter_mixins.mixins.promotion_adapter_mixin import PromotionAdapterProtocol
from .base_wb_api_protocol import BaseWBApiProtocol

logger = logging.getLogger(__name__)


from app.shared.application.commands.search_adv_bid_update UdateBIDForShopCommand


from app.shared.application.commands.search_adv_bid_update UdateBIDForShopCommand


@dataclass
class UpdateBIDForShopCommand:
    # TODO: Добавьте необходимые поля
    pass


class CPMUpdateMixin(BaseWBApiProtocol):
    async def update_bids_for_shop(
            self: BaseWBApiProtocol,
            update_cpms_for_shop_command: UpdateBIDForShopCommand
    ) -> None:
        adapter: PromotionAdapterProtocol = self.adapter_manager.get_adapter(
            self.shop_id,
            'promotion',
            version=1
        )
        await adapter.update_cpms_in_search_advs(update_cpms_for_shop_command)
