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
    command_to_bodies,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.api.search_clusters.post_adv_v0_normquery_stats import (
    asyncio_detailed,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.raw_response_to_dto import raw_response_to_dto
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import V0GetNormQueryStatsResponse, \
    V0GetNormQueryStatsItem, V0GetNormQueryStatsRequest
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.types import Response
from app.core.mp.wb.api.retry_decorator import retry_decorator
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors


class NormqueryStatsAdapter(BaseSectionAdapter):


    async def get_adv_v0_normquery_stats(self,
                                         command: GetNormqueryStatsCommand) -> list[NormqueryStatsDTO] | None:
        bodies = command_to_bodies(command)
        results: list[NormqueryStatsDTO] = []
        for body in bodies:
            result: list[NormqueryStatsDTO] | None  = await self._get_adv_v0_normquery_stats(body)
            if result is not None:
                results.extend(result)
        return results

    @retry_decorator(period=60, limit=5)
    async def _get_adv_v0_normquery_stats(
        self, body: V0GetNormQueryStatsRequest
    ) -> list[NormqueryStatsDTO] | None:
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
