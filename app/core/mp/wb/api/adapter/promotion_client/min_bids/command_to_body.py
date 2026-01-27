from __future__ import annotations

from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    PostApiAdvertV1BidsMinBody,
    PostApiAdvertV1BidsMinBodyPaymentType,
)

from .command import GetMinBidsCommandItem


def convert(item: GetMinBidsCommandItem) -> PostApiAdvertV1BidsMinBody:
    return PostApiAdvertV1BidsMinBody(
        advert_id=item.adv_id,
        nm_ids=item.nmids,
        payment_type=PostApiAdvertV1BidsMinBodyPaymentType.CPM,
        placement_types=[item.placement_type.to_wb_placement_type()],
    )
















