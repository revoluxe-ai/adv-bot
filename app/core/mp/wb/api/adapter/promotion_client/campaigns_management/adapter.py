from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.api.campaigns_management import (
    get_adv_v0_pause,
    get_adv_v0_start,
    get_adv_v0_stop,
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
