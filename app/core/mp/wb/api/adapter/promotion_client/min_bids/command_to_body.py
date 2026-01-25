from __future__ import annotations

from app.core.mp.wb.api.generated.promotion.v1.marketing_and_promotions_client.models import (
    PostAdvV0BidsMinBody,
    PostAdvV0BidsMinBodyPaymentType,
)

from .command import GetMinBidsCommandItem


def convert(item: GetMinBidsCommandItem) -> PostAdvV0BidsMinBody:
    return PostAdvV0BidsMinBody(
        advert_id=item.adv_id,
        nm_ids=item.nmids,
        payment_type=PostAdvV0BidsMinBodyPaymentType.CPM,
        placement_types=[item.placement_type.to_wb_placement_type()],
    )
















