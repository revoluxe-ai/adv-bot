from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import (
    NormqueryBidDTO,
)
from app.core.mp.wb.api.generated.promotion.marketing_and_promotions_client.models import (
    V0GetNormQueryBidsItem,
)


def raw_response_to_dto(raw_bid: V0GetNormQueryBidsItem) -> NormqueryBidDTO:
    return NormqueryBidDTO(
        advert_id=raw_bid.advert_id,
        nm_id=raw_bid.nm_id,
        norm_query=raw_bid.norm_query,
        bid=raw_bid.bid,
    )
