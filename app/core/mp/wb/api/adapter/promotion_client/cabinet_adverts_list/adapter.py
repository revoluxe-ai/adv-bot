"""Adapter for listing cabinet adverts (GET /adv/v1/adverts) to get adv_ids for v2 batch fetch."""

from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.excs import BadRequestError
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.api.media.get_adv_v1_adverts import (
    asyncio_detailed,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    GetAdvV1AdvertsResponse200Item,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.types import (
    Response,
)
from app.core.mp.wb.api.retry_decorator import retry_decorator


def _is_not_found_or_no_adverts(exc: BadRequestError) -> bool:
    """WB returns 404 / path not found when there are no adverts in the cabinet."""
    detail = (getattr(exc, "detail", None) or str(exc)).lower()
    return (
        "path not found" in detail
        or "not found" in detail
        or "404" in detail
    )


class CabinetAdvertsListAdapter(BaseSectionAdapter):
    """Returns list of advert_id for the cabinet via GET /adv/v1/adverts (paginated)."""

    PAGE_SIZE = 100

    @retry_decorator(period=1, limit=5)
    async def get_cabinet_adv_ids(self) -> list[int]:
        """Fetch all advert IDs for the cabinet (paginated). Returns [] if WB returns 404 (no adverts)."""
        client = await self.auth_client_handler.get_proxy_client(self)
        all_ids: list[int] = []
        offset = 0
        try:
            while True:
                response: Response[
                    list[GetAdvV1AdvertsResponse200Item] | None
                ] = await with_raise_errors(
                    asyncio_detailed,
                    client,
                    limit=self.PAGE_SIZE,
                    offset=offset,
                )
                parsed = response.parsed
                if not isinstance(parsed, list) or not parsed:
                    break
                for item in parsed:
                    if isinstance(item.advert_id, int):
                        all_ids.append(item.advert_id)
                if len(parsed) < self.PAGE_SIZE:
                    break
                offset += self.PAGE_SIZE
        except BadRequestError as e:
            if _is_not_found_or_no_adverts(e):
                return []
            raise
        return all_ids
