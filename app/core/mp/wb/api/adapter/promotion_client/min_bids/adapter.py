from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.api.campaigns_creation.post_adv_v0_bids_min import (
    asyncio_detailed,
)
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.models import (
    PostAdvV0BidsMinResponse200,
)
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.types import (
    Response,
)
from app.core.mp.wb.api.retry_decorator import retry_decorator

from .command import GetMinBidsCommand, GetMinBidsCommandItem
from .command_to_body import convert as command_to_body
from .dto import MinBidForNmid
from .raw_response_to_dto import convert as response_to_dto


class MinBidsAdapter(BaseSectionAdapter):
    """Адаптер запросов минимальных ставок по товарам в рекламных кампаниях."""

    async def post_adv_v0_bids_min(
        self, command: GetMinBidsCommand
    ) -> list[MinBidForNmid]:
        min_bids: list[MinBidForNmid] = []
        for command_item in command.items:
            min_bids.extend(
                await self._post_adv_v0_bids_min_single(
                    command_item=command_item,
                )
            )
        return min_bids

    @retry_decorator(period=3, limit=5)
    async def _post_adv_v0_bids_min_single(
        self,
        command_item: GetMinBidsCommandItem,
    ) -> list[MinBidForNmid]:
        client = await self.auth_client_handler.get_proxy_client(self)
        body = command_to_body(command_item)
        response: Response[PostAdvV0BidsMinResponse200] = await with_raise_errors(
            asyncio_detailed,
            client,
            body,
        )
        parsed = response.parsed
        if parsed is None:
            return []
        return response_to_dto(parsed)






