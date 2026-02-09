from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.api.campaigns_management import (
    get_adv_v0_pause,
    get_adv_v0_start,
    get_adv_v0_stop,
    patch_adv_v0_bids,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.api.campaigns_management.post_adv_v0_rename import (
    asyncio_detailed as post_adv_v0_rename_asyncio_detailed,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    PatchAdvV0BidsBody,
    PostAdvV0RenameBody,
)
from app.core.mp.wb.api.retry_decorator import retry_decorator


class CampaignsManagementAdapter(BaseSectionAdapter):
    """Adapter for working with campaign lifecycle methods (start, pause, stop)."""

    @retry_decorator(period=1, limit=5)
    async def start_adv(self, adv_id: int) -> None:
        client = await self.auth_client_handler.get_proxy_client(self)
        await with_raise_errors(get_adv_v0_start.asyncio_detailed, client, id=adv_id)

    @retry_decorator(period=1, limit=5)
    async def pause_adv(self, adv_id: int) -> None:
        client = await self.auth_client_handler.get_proxy_client(self)
        await with_raise_errors(get_adv_v0_pause.asyncio_detailed, client, id=adv_id)

    @retry_decorator(period=1, limit=5)
    async def stop_adv(self, adv_id: int) -> None:
        client = await self.auth_client_handler.get_proxy_client(self)
        await with_raise_errors(get_adv_v0_stop.asyncio_detailed, client, id=adv_id)

    @retry_decorator(period=1, limit=2)
    async def patch_adv_bids(self, body: PatchAdvV0BidsBody) -> None:
        client = await self.auth_client_handler.get_proxy_client(self)
        await with_raise_errors(
            patch_adv_v0_bids.asyncio_detailed,
            client,
            body=body,
        )

    @retry_decorator(period=1, limit=2)
    async def rename_adv(self, adv_id: int, new_name: str) -> None:
        client = await self.auth_client_handler.get_proxy_client(self)
        body = PostAdvV0RenameBody(advert_id=adv_id, name=new_name)
        await with_raise_errors(
            post_adv_v0_rename_asyncio_detailed,
            client,
            body=body,
        )
