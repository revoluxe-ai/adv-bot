from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids import (
    NormqueryBidsAdapter,
)
from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import (
    NormqueryBidDTO,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

from . import convertor

if TYPE_CHECKING:
    from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
        V0GetNormQueryBidsRequest,
    )


async def get_current_bids(
    normquery_bids_adapter: NormqueryBidsAdapter,
    complex_advs: list[ComplexAdv],
) -> list[NormqueryBidDTO] | None:
    """Возвращает текущие ставки по нормкапам, запрашивая WB API."""

    if not complex_advs:
        return None

    command: V0GetNormQueryBidsRequest = convertor.dto_to_request(complex_advs)
    if not command.items:
        return None

    return await normquery_bids_adapter.post_adv_v0_normquery_get_bids(command)
