import asyncio

from app.core.utils.future_getter_base import FutureGetterBase


class MinBidsForAdvGetter(FutureGetterBase):
    async def _fetch(self, shop_id, adv_id: int, nmids: list[int]) -> dict[int, int]:







    def get_future(self, shop_id: str, adv_id: int, nmids: list[int]) -> asyncio.Future:
        return super()._get_future(shop_id, adv_id, nmids)
