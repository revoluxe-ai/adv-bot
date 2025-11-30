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
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.models import V0GetNormQueryStatsResponse, \
    V0GetNormQueryStatsItem
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.types import Response
from app.core.mp.wb.api.retry_decorator import retry_decorator
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors


class NormqueryStatsAdapter(BaseSectionAdapter):

    @retry_decorator(period=60, limit=5)
    async def get_adv_v0_normquery_stats(
        self, command: GetNormqueryStatsCommand
    ) -> list[NormqueryStatsDTO] | None:
        body = command_to_body(command)
        client = await self.auth_client_handler.get_proxy_client(self)
        response: Response[V0GetNormQueryStatsResponse] = await with_raise_errors(asyncio_detailed, client, body=body)
        # TODO: Тут метод предполагает получение данных по нескольким РК, срочно!!! Переделать

        parsed: V0GetNormQueryStatsResponse | None = response.parsed
        if parsed is None:
            return None
        norm_query_stats: list[V0GetNormQueryStatsItem] = parsed.stats
        dtos: list[NormqueryStatsDTO] = []
        for raw_stat in norm_query_stats:
            dto: NormqueryStatsDTO = raw_response_to_dto(raw_stat)
            dtos.append(dto)
        return dtos
