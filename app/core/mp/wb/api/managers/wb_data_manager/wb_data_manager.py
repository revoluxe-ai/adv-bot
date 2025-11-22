from typing import Sequence

from app.core.mp.wb.dto import KeywordPosition
import logging
import typing

# TODO: Разобраться в NEO4j, почему так много выделяем и так мало грузит
# TODO: Внедрить контроль прогноза ключей, а то иногда не прогнозит


from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword

if typing.TYPE_CHECKING:
    from app.core.mp.wb.api.domain_managers import AnalyticsManager

logger = logging.getLogger(__name__)

class WBDataManager:

    def __init__(self,  analytics_manager: "AnalyticsManager"):
        self._analytics_manager = analytics_manager


    async def get_keywords_positions_from_wb_api(self,
                                                 nmid: int,
                                                 keywords: typing.Sequence[CalculatedKeyword],
                                                 for_last_days: int) -> Sequence[KeywordPosition]:




        positions: Sequence[KeywordPosition] = await self._analytics_manager.get_keywords_positions(
                                                                                               nmid,
                                                                                               keywords,
                                                                                                for_last_days)

        return positions









