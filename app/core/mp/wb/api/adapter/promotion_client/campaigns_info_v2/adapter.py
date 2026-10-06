"""Read-only promotion v2 campaigns-info adapter.

Транспорт и rate-limit для `/api/advert/v2/adverts`. Не пишет в WB и не
меняет control-plane semantics.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable, Mapping
from typing import Any, cast

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


# WB: ~5 GET /api/advert/v2/adverts per 1s (sliding). @retry_decorator(period=1, limit=5) paces
# only whole-method calls; inner chunk loop must leave >0.2s between request *starts* (use 0.25).
_V2_ADVERTS_INTER_CHUNK_SECONDS = 0.25


class CampaignsInfoV2Adapter(BaseSectionAdapter):
    """Adapter for /api/advert/v2/adverts endpoint from promotion v2 client."""
    # TODO: тут нормально переделать, вынеся чанки в отдельный метод под ретрай-декоратором
    @retry_decorator(period=1, limit=5)
    async def get_campaigns_info(
        self, adv_ids: list[int]
    ) -> list[GetAdvertsAdvertsItem]:
        if not adv_ids:
            return []

        campaigns: list[GetAdvertsAdvertsItem] = []
        for chunk_idx, chunk in enumerate(_chunks(adv_ids, 50)):
            if chunk_idx > 0:
                await asyncio.sleep(_V2_ADVERTS_INTER_CHUNK_SECONDS)
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
    async def get_campaigns_info_raw_by_ids(
        self, adv_ids: list[int]
    ) -> list[Mapping[str, Any]]:
        """Fetch raw advert dicts via same transport/retry/rate-limit as get_campaigns_info."""
        if not adv_ids:
            return []

        raw_items: list[Mapping[str, Any]] = []
        for chunk_idx, chunk in enumerate(_chunks(adv_ids, 50)):
            if chunk_idx > 0:
                await asyncio.sleep(_V2_ADVERTS_INTER_CHUNK_SECONDS)
            client = await self.auth_client_handler.get_proxy_client(self)
            response: Response[GetAdverts] = await with_raise_errors(
                asyncio_detailed,
                client,
                ids=",".join(str(adv_id) for adv_id in chunk),
            )
            try:
                decoded: object = json.loads(response.content)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                raise ValueError("WB v2 adverts response is not valid JSON") from exc
            if not isinstance(decoded, dict):
                raise ValueError("WB v2 adverts response root must be a JSON object")
            payload = cast(dict[str, object], decoded)
            adverts_raw = payload.get("adverts")
            if adverts_raw is None:
                raise ValueError("WB v2 adverts response missing adverts field")
            if not isinstance(adverts_raw, list):
                raise ValueError("WB v2 adverts field must be a JSON array")
            adverts = cast(list[object], adverts_raw)
            for item in adverts:
                if not isinstance(item, dict):
                    raise ValueError("WB v2 advert entry must be a JSON object")
                advert = cast(dict[str, object], item)
                if advert.get("id") is None:
                    raise ValueError("WB v2 advert entry missing id")
                raw_items.append(cast(Mapping[str, Any], advert))
        return raw_items

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
