import asyncio

from app.core.utils.future_getter_base import FutureGetterBase


class MinBidsForAdvGetter(FutureGetterBase):
    async def _fetch(self, adv_id: int, nmids: list[int]) -> dict[int, int]:
        # Здесь должна быть реальная логика получения минимальных ставок
        await asyncio.sleep(0)  # имитируем асинхронность
        return {nmid: 100 for nmid in nmids}

    def get_future(self, adv_id: int, nmids: list[int]) -> asyncio.Future:
        return super()._get_future(adv_id, nmids)
