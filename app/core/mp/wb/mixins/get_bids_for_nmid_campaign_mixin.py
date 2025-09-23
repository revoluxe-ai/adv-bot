import logging

from app.core.mp.wb.base_adapters.base_adapter import WBBaseAdapters

logger = logging.getLogger(__name__)


class GetBidsForNmidCampaignMixin(WBBaseAdapters):
    """
    Миксин для получения ставок по nmids в рамках кампании через promotion_adapter.
    """

    async def get_bids_for_nmid_campaign(
            self,
            adv_id: int,
            nmids: list[int],
    ) -> dict[int, int]:
        """
        Получить ставки для списка nmids в рамках кампании adv_id через promotion_adapter.
        """
        return await self.promotion_adapter.get_bids_for_nmid_campaign(adv_id, nmids)
