from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_bids import catch_special_errors
from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.command import (
    SetNormqueryBidsCommand,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import (
    NormqueryBidDTO,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.raw_response_to_dto import (
    raw_response_to_dto,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.api.search_clusters.post_adv_v0_normquery_bids import (
    asyncio_detailed as post_adv_v0_normquery_bids_async,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.api.search_clusters.post_adv_v0_normquery_get_bids import (
    asyncio_detailed as post_adv_v0_normquery_get_bids_async,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    V0GetNormQueryBidsRequest,
    V0SetNormQueryBidsRequest,
    V0SetNormQueryBidsRequestItem,
)
from app.core.mp.wb.api.retry_decorator import retry_decorator


class NormqueryBidsAdapter(BaseSectionAdapter):
    """Адаптер для работы с методами получения и установки ставок по поисковым кластерам."""
    # TODO: Почему-то не возвращает текущие ставки, временно берем из базы последнее CPM
    @retry_decorator(period=60, limit=5)
    async def post_adv_v0_normquery_get_bids(
        self, command: V0GetNormQueryBidsRequest
    ) -> list[NormqueryBidDTO] | None:
        client = await self.auth_client_handler.get_proxy_client(self)
        response = await with_raise_errors(
            post_adv_v0_normquery_get_bids_async,
            client,
            body=command,
        )

        parsed = response.parsed
        if parsed is None:
            return None

        return [raw_response_to_dto(bid) for bid in parsed.bids]

    @retry_decorator(period=1, limit=2)
    async def post_adv_v0_normquery_bids(
        self, command: SetNormqueryBidsCommand
    ) -> None:
        client = await self.auth_client_handler.get_proxy_client(self)
        items = [
            V0SetNormQueryBidsRequestItem(
                advert_id=item.advert_id,
                nm_id=item.nm_id,
                norm_query=item.norm_query,
                bid=item.bid,
            )
            for item in command.bids
        ]
        body = V0SetNormQueryBidsRequest(bids=items)

        await catch_special_errors.catch_special_errors(with_raise_errors(
            post_adv_v0_normquery_bids_async,
            client,
            body=body,
        ))



