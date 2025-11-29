from typing import List, Sequence
import datetime

from app.core.mp.wb.dto import KeywordPosition
import logging
import typing

# TODO: Разобраться в NEO4j, почему так много выделяем и так мало грузит
# TODO: Внедрить контроль прогноза ключей, а то иногда не прогнозит


from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.dto import NormqueryStatsDTO


if typing.TYPE_CHECKING:
    from app.core.mp.wb.api.domain_managers import AnalyticsManager, PromotionManager

logger = logging.getLogger(__name__)


class NornQueryStat:
    pass


class WBDataManager:

    def __init__(self, analytics_manager: "AnalyticsManager", promotion_manager: "PromotionManager"):
        self._analytics_manager = analytics_manager
        self._promotion_manager = promotion_manager

    async def get_keywords_positions_from_wb_api(
        self,
        nmid: int,
        keywords: typing.Sequence[CalculatedKeyword],
        for_last_days: int,
    ) -> Sequence[KeywordPosition]:

        positions: Sequence[KeywordPosition] = (
            await self._analytics_manager.get_keywords_positions(
                nmid, keywords, for_last_days
            )
        )

        return positions

    async def get_norn_query_stat(
        self,
        advert_id: int,
        nmid: int,
        last_days: int,
    ) -> List[NormqueryStatsDTO]:
        today = datetime.date.today()
        date_from  = today - datetime.timedelta(days=last_days)

        return await self._promotion_manager.get_normquery_stats(
            advert_id=advert_id,
            date_from=date_from,
            date_to=today,
            nm_id=nmid,
        )
