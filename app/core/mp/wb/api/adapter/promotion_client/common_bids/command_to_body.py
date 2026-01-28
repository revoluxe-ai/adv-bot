from __future__ import annotations

from collections import defaultdict

from app.shared.domains.wb.enums import AdvType

from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    PatchApiAdvertV1BidsBody,
    PatchApiAdvertV1BidsBodyBidsItem,
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItem,
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement,
)
from .command import SetCommonBidsCommand


_PLACEMENT_BY_ADV_TYPE: dict[AdvType, PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement] = {
    AdvType.AUTO: PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.COMBINED,
    AdvType.SEARCH: PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement.SEARCH,
}


def _to_kopecks(value: float | int) -> int:
    return int(value * 100)


def _get_placement(adv_type: AdvType) -> PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement:
    try:
        return _PLACEMENT_BY_ADV_TYPE[adv_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported adv_type for placement mapping: {adv_type}") from exc


def convert(command: SetCommonBidsCommand) -> PatchApiAdvertV1BidsBody:
    bids_by_advert: dict[int, list[PatchApiAdvertV1BidsBodyBidsItemNmBidsItem]] = defaultdict(
        list
    )

    for item in command.items:
        if item.new_bid is None:
            continue
        placement = _get_placement(item.adv_type)
        bid_kopecks = _to_kopecks(item.new_bid)
        nm_bid = PatchApiAdvertV1BidsBodyBidsItemNmBidsItem(
            nm_id=item.target_nmid,
            bid_kopecks=bid_kopecks,
            placement=placement,
        )
        adv_id = item.complex_adv.get_adv_id_by_type(item.adv_type)
        bids_by_advert[adv_id].append(nm_bid)

    if not bids_by_advert:
        raise ValueError("SetCommonBidsCommand contains no bids after filtering None values")

    return PatchApiAdvertV1BidsBody(
        bids=[
            PatchApiAdvertV1BidsBodyBidsItem(advert_id=advert_id, nm_bids=nm_bids)
            for advert_id, nm_bids in bids_by_advert.items()
        ]
    )
