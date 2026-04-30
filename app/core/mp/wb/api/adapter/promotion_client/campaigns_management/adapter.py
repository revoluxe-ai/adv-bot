from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.api.campaigns_management import (
    get_adv_v0_pause,
    get_adv_v0_start,
    get_adv_v0_stop,
    post_adv_v0_rename,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    PostAdvV0RenameBody,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.api.upravlenie_kampanijami.patch_api_advert_v1_bids import (
    asyncio_detailed as patch_api_advert_v1_bids_async,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    PatchApiAdvertV1BidsBody,
)
from app.core.mp.wb.api.generated.promotion.v5.marketing_and_promotions_client.marketing_and_promotions_client.api.campaigns_management import (
    put_adv_v0_auction_placements,
)
from app.core.mp.wb.api.generated.promotion.v5.marketing_and_promotions_client.marketing_and_promotions_client.models import (
    PutAdvV0AuctionPlacementsBody,
    PutAdvV0AuctionPlacementsBodyPlacementsItem,
    PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements,
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
    async def patch_adv_v1_bids(self, body: PatchApiAdvertV1BidsBody) -> None:
        client = await self.auth_client_handler.get_proxy_client(self)
        await with_raise_errors(
            patch_api_advert_v1_bids_async,
            client,
            body=body,
        )

    @retry_decorator(period=1, limit=5)
    async def rename_adv(self, adv_id: int, new_name: str) -> None:
        client = await self.auth_client_handler.get_proxy_client(self)
        body = PostAdvV0RenameBody(advert_id=adv_id, name=new_name)
        await with_raise_errors(
            post_adv_v0_rename.asyncio_detailed,
            client,
            body=body,
        )

    @retry_decorator(period=1, limit=5)
    async def put_auction_placements(
        self, adv_id: int, *, search: bool, recommendations: bool
    ) -> None:
        """Set placement (search / recommendations) for auction campaign."""
        client = await self.auth_client_handler.get_proxy_client(self)
        body = PutAdvV0AuctionPlacementsBody(
            placements=[
                PutAdvV0AuctionPlacementsBodyPlacementsItem(
                    advert_id=adv_id,
                    placements=PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements(
                        search=search,
                        recommendations=recommendations,
                    ),
                )
            ]
        )
        await with_raise_errors(
            put_adv_v0_auction_placements.asyncio_detailed,
            client,
            body=body,
        )
