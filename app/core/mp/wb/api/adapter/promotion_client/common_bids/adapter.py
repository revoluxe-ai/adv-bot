from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.api.upravlenie_kampanijami.patch_api_advert_v1_bids import (
    asyncio_detailed as patch_common_bids_async,
)
from app.core.mp.wb.api.retry_decorator import retry_decorator

from .command import SetCommonBidsCommand
from .command_to_body import convert as command_to_body


class CommonBidsAdapter(BaseSectionAdapter):
    """Adapter для изменения общей ставки кампаний по API /api/advert/v1/bids."""

    @retry_decorator(period=1, limit=2)
    async def patch_common_bids(self, command: SetCommonBidsCommand) -> None:
        client = await self.auth_client_handler.get_proxy_client(self)
        body = command_to_body(command)
        await with_raise_errors(
            patch_common_bids_async,
            client,
            body=body,
        )
