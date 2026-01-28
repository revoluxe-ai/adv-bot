from __future__ import annotations

from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    PostApiAdvertV1BidsMinResponse200,
)

from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType

from .dto import MinBidForNmid


def convert(response: PostApiAdvertV1BidsMinResponse200) -> list[MinBidForNmid]:
    min_bids: list[MinBidForNmid] = []
    for bid_item in response.bids:
        for placement_bid in bid_item.bids:
            placement_type = AdvPlacementType.from_wb_placement_type(
                placement_bid.type_
            )
            min_bids.append(
                MinBidForNmid(
                    nmid=bid_item.nm_id,
                    placement_type=placement_type,
                    min_cpm=placement_bid.value,
                )
            )
    return min_bids
















