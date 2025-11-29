from typing import List

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import (
    GetNormqueryStatsCommand,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.dto import (
    NormqueryStatsDTO,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.get_normquery_stats import (
    command_to_body,
)
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.api.search_clusters.post_adv_v0_normquery_stats import (
    asyncio_detailed,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.raw_response_to_dto import raw_response_to_dto
from app.core.mp.wb.api.retry_decorator import retry_decorator
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors


class NormqueryStatsAdapter(BaseSectionAdapter):
    @retry_decorator(period=60, limit=5)
    async def get_adv_v0_normquery_stats(
        self, command: GetNormqueryStatsCommand
    ) -> List[NormqueryStatsDTO]:
        body = command_to_body(command)
        client = await self.auth_client_handler.get_proxy_client(self)
        response = await with_raise_errors(asyncio_detailed, client, body=body)
        # TODO: Тут метод предполагает получение данных по нескольким РК, срочно!!! Переделать
        if response.parsed and response.parsed.stats:
            dtos: list[NormqueryStatsDTO] = []
            for item in response.parsed.stats:
                dto = raw_response_to_dto(item, command.advert_id, command.nmid)
                if dto:
                    dtos.extend(dto)
            return dtos
        return []
