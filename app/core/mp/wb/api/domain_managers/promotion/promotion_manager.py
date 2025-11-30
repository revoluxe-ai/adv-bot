from typing import List
import datetime


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
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv


class PromotionManager:
    """Доменный менеджер для работы с сущностями продвижения (WB API)."""

    def __init__(self, promotion_client: PromotionClient) -> None:
        self._client = promotion_client

    async def set_minus_phrases(
        self, advert_id: int, nm_id: int, phrases: list[str]
    ) -> None:
        from app.core.mp.wb.api.adapter.promotion_client.minus_phrases.post_adv_v0_normquery_set_minus.command import (
            SetMinusPhrasesCommand,
        )
        command = SetMinusPhrasesCommand(
            advert_id=advert_id, nm_id=nm_id, norm_queries=phrases
        )
        await request(
            self._client.minus_phrases_adapter.post_adv_v0_normquery_set_minus,
            command,
        )

    async def get_normquery_stats(
        self,
        complex_advs: list["ComplexAdv"],
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> List[NormqueryStatsDTO] | None:
        command = GetNormqueryStatsCommand(
            complex_advs=complex_advs,
            date_from=date_from,
            date_to=date_to)
        return await self._client.normquery_stats_adapter.get_adv_v0_normquery_stats(
            command
        )
