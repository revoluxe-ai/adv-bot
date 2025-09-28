from __future__ import annotations

import logging
from typing import cast

from app.shared.application.commands.search_adv_bid_update import UpdateBidsForShopCommand

logger = logging.getLogger(__name__)


class CPMUpdateMixin:
    """Mixin that routes CPM update commands through the promotion adapter."""

    section: str = "promotion"
    version: int = 1


    async def update_bids_for_shop(
        self,
        update_cpms_for_shop_command: UpdateBidsForShopCommand,
    ) -> None:
        adapter = self.get_adapter(self.section, self.version)
        await adapter.update_cpms_in_search_advs(update_cpms_for_shop_command)
