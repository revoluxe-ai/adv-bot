from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids import (
    NormqueryBidsAdapter,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import (
    NormqueryBidDTO,
)
from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    V0GetNormQueryBidsRequest,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

from . import convertor

# WB camp-api-public-cache: "too many items: N, maximum allowed is 100"
MAX_ITEMS_PER_REQUEST = 100


async def get_current_bids(
    normquery_bids_adapter: NormqueryBidsAdapter,
    complex_advs: list[ComplexAdv],
) -> list[NormqueryBidDTO] | None:
    """Возвращает текущие ставки по нормкапам, запрашивая WB API."""

    if not complex_advs:
        return None

    command = convertor.dto_to_request(complex_advs)
    if not command.items:
        return None

    merged: list[NormqueryBidDTO] = []
    for start in range(0, len(command.items), MAX_ITEMS_PER_REQUEST):
        chunk = command.items[start : start + MAX_ITEMS_PER_REQUEST]
        sub = V0GetNormQueryBidsRequest(items=chunk)
        part = await normquery_bids_adapter.post_adv_v0_normquery_get_bids(sub)
        if part is None:
            continue
        merged.extend(part)

    return merged or None
