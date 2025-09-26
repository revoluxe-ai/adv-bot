from asyncio import Future

from app.core.utils.future_getter_base import FutureGetterBase
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword


class CurrentBidsForAdvGetter(FutureGetterBase):
    def _fetch(self, shop_id: str, adv_id: int, nmids: list[int], best_keyword_future: Future[CalculatedKeyword]):
        from .wb_api import WBApi
        wb_api = WBApi(shop_id)

    def get_future(self, shop_id, adv_id: int, nmids: list[int], best_keyword_future: Future[CalculatedKeyword]):
        return super()._get_future(shop_id, adv_id, nmids, best_keyword_future)
