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
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv

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

    async def get_norn_query_stat_for_period(
        self,
        complex_advs: list["ComplexAdv"],
        last_days: int,
    ) -> List[NormqueryStatsDTO] | None:
        today = datetime.date.today()
        date_from  = today - datetime.timedelta(days=last_days)

        return await self._promotion_manager.get_normquery_stats(
            complex_advs,
            date_from=date_from,
            date_to=today,
        )

    async def get_norn_query_stat_for_date_range(
        self,
        complex_advs: list["ComplexAdv"],
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> List[NormqueryStatsDTO] | None:
        """Получить статистику normquery за указанный диапазон дат."""
        return await self._promotion_manager.get_normquery_stats(
            complex_advs,
            date_from=date_from,
            date_to=date_to,
        )
