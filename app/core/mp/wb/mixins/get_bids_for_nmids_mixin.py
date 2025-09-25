import logging

from app.core.mp.wb.base_adapters.base_adapter import WBBaseAdapters
from app.modules.common_slaves.wildberries.models import AdvSetting

logger = logging.getLogger(__name__)


class GetBidsForNmidsMixin(WBBaseAdapters):
    async def get_bids_for_search_adv(self, adv: AdvSetting) -> dict[int, int]:
        search_adv_id = adv.search_adv_id
        if not search_adv_id:
            logger.error("skip: empty adv search_adv_id", extra={"adv_id": adv.adv_id})
            raise Exception("empty adv search_adv_id")

        bids = await self._get_bids_for_adv_id(search_adv_id, adv.nmids)
        return bids

    async def _get_bids_for_adv_id(self,
                                   adv_id: int,
                                   nmids: list[int],
                                   ):



