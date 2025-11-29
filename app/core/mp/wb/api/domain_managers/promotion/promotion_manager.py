from typing import List
import datetime

from app.core.mp.wb.api.adapter.promotion_client.minus_phrases.post_adv_v0_normquery_set_minus.command import (
    SetMinusPhrasesCommand,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import (
    GetNormqueryStatsCommand,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.dto import (
    NormqueryStatsDTO,
)
from app.core.mp.wb.api.domain_managers.promotion.methods.set_minus_phrases import (
    request,
)
from app.core.mp.wb.api.adapter.promotion_client.promotion_client import PromotionClient


class PromotionManager:
    """Доменный менеджер для работы с сущностями продвижения (WB API)."""

    def __init__(self, promotion_client: PromotionClient) -> None:
        self._client = promotion_client

    async def set_minus_phrases(
        self, advert_id: int, nm_id: int, phrases: list[str]
    ) -> None:
        command = SetMinusPhrasesCommand(
            advert_id=advert_id, nm_id=nm_id, norm_queries=phrases
        )
        await request(
            self._client.minus_phrases_adapter.post_adv_v0_normquery_set_minus,
            command,
        )

    async def get_normquery_stats(
        self,
        advert_id: int,
        date_from: datetime.date,
        date_to: datetime.date,
        nm_id: int,
    ) -> List[NormqueryStatsDTO]:
        command = GetNormqueryStatsCommand(
            advert_id=advert_id,
            date_from=date_from,
            date_to=date_to,
            nmid=nm_id,
        )
        return await self._client.normquery_stats_adapter.get_adv_v0_normquery_stats(
            command
        )
