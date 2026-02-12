from __future__ import annotations

from typing import Iterable

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.api.kampanii.get_api_advert_v2_adverts import (
    asyncio_detailed,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    GetAdverts,
    GetAdvertsAdvertsItem,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.types import (
    Response,
    UNSET,
)
from app.core.mp.wb.api.retry_decorator import retry_decorator


def _chunks(items: list[int], chunk_size: int) -> Iterable[list[int]]:
    for i in range(0, len(items), chunk_size):
        yield items[i : i + chunk_size]


class CampaignsInfoV2Adapter(BaseSectionAdapter):
    """Adapter for /api/advert/v2/adverts endpoint from promotion v2 client."""

    @retry_decorator(period=1, limit=5)
    async def get_campaigns_info(
        self, adv_ids: list[int]
    ) -> list[GetAdvertsAdvertsItem]:
        if not adv_ids:
            return []

        campaigns: list[GetAdvertsAdvertsItem] = []
        for chunk in _chunks(adv_ids, 50):
            client = await self.auth_client_handler.get_proxy_client(self)
            response: Response[GetAdverts] = await with_raise_errors(
                asyncio_detailed,
                client,
                ids=",".join(str(adv_id) for adv_id in chunk),
            )
            parsed = response.parsed
            if isinstance(parsed, GetAdverts):
                campaigns.extend(parsed.adverts)

        return campaigns

    @retry_decorator(period=1, limit=5)
    async def get_all_campaigns(self) -> list[GetAdvertsAdvertsItem]:
        """Fetch all campaigns via GET /api/advert/v2/adverts without ids (fallback when v1 list is empty)."""
        client = await self.auth_client_handler.get_proxy_client(self)
        response: Response[GetAdverts] = await with_raise_errors(
            asyncio_detailed,
            client,
            ids=UNSET,
        )
        parsed = response.parsed
        if isinstance(parsed, GetAdverts):
            return list(parsed.adverts)
        return []
