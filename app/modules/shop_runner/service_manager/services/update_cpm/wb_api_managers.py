import logging

from app.core.mp.wb.generated.promotion.v1.client.models.patch_adv_v0_bids_body import PatchAdvV0BidsBody
from app.core.mp.wb.generated.promotion.v1.client.models.v0_advert_multi_bid_item import V0AdvertMultiBidItem
from app.core.mp.wb.generated.promotion.v1.client.models.v0_advert_multibid import V0AdvertMultibid

logger = logging.getLogger(__name__)


class WBApiDataGetter:
    async def get_min_bid_for_nmids(self, shop_id: str, *, adv_id: int, nmids: list[int]) -> dict[int, int]:
        return await self._promotion_adapter.get_min_bids(shop_id, adv_id=adv_id, nmids=nmids)

    async def get_current_bids(self, shop_id: str, *, adv_id: int, nmids: list[int]) -> dict[int, int]:
        return await self._promotion_adapter.get_current_bids(shop_id, adv_id=adv_id, nmids=nmids)


class WBApiCpmUpdater:
    async def update_bids(self, shop_id: str, *, adv_id: int, nm_bids: list[dict[str, int]]) -> None:
        # Преобразуем {nm, cpm} -> V0AdvertMultiBidItem(nm, bid)
        items = [V0AdvertMultiBidItem(nm=int(row["nm"]), bid=int(row["cpm"])) for row in nm_bids]
        multibid = V0AdvertMultibid(advert_id=int(adv_id), nm_bids=items)
        payload = PatchAdvV0BidsBody(bids=[multibid])
        await self._promotion_adapter.update_bids(shop_id, payload=payload)


import logging

logger = logging.getLogger(__name__)


class WBApiDataGetter:
    def __init__(self, promotion_adapter) -> None:
        self._promotion_adapter = promotion_adapter

    async def get_min_bid_for_nmids(self, shop_id: str, *, adv_id: int, nmids: list[int]) -> dict[int, int]:
        return await self._promotion_adapter.get_min_bids(shop_id, adv_id=adv_id, nmids=nmids)

    async def get_current_bids(self, shop_id: str, *, adv_id: int, nmids: list[int]) -> dict[int, int]:
        return await self._promotion_adapter.get_current_bids(shop_id, adv_id=adv_id, nmids=nmids)
