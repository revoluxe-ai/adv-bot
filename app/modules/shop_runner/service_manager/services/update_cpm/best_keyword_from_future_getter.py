from typing import Awaitable, Any

from app.core.utils.future_getter_base import FutureGetterBase
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.wb_adv_updater.data_manager import get_best_keyword


class BestKeywordFromFutureGetter(FutureGetterBase):
    async def _fetch(self, keywords_coro: Awaitable[list[CalculatedKeyword]]) -> Any:
        keywords = await keywords_coro
        return get_best_keyword(keywords)

    def _get_future(self, keywords_coro: Awaitable[list[Any]]):
        return super()._get_future(keywords_coro)
