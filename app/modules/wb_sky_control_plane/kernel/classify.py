"""Classify campaign resource from authoritative WB normalization."""

from __future__ import annotations

from app.modules.wb_sky_control_plane.models.enums import (
    BidTypeAuthority,
    CampaignTopology,
    PaymentTypeAuthority,
    PlacementFlagAuthority,
    ProductMembershipAuthority,
)  # BidTypeAuthority used in _leg_has_unknown_fields
from app.modules.wb_sky_control_plane.models.snapshot import (
    CampaignClassificationV1,
    CampaignLegSnapshotV1,
    CampaignResourceSnapshotV1,
)


def _leg_has_unknown_fields(leg: CampaignLegSnapshotV1 | None) -> bool:
    if leg is None:
        return False
    if leg.payment_type == PaymentTypeAuthority.UNKNOWN:
        return True
    if leg.bid_type == BidTypeAuthority.UNKNOWN:
        return True
    if leg.placements.search == PlacementFlagAuthority.UNKNOWN:
        return True
    if leg.placements.recommendations == PlacementFlagAuthority.UNKNOWN:
        return True
    if leg.product_membership == ProductMembershipAuthority.UNKNOWN:
        return True
    return False


def classify_snapshot(snapshot: CampaignResourceSnapshotV1) -> CampaignClassificationV1:
    """Classify topology/payment from WB legs (not AdvSetting.type 8/9)."""
    reason_codes: list[str] = []
    has_unknown = False

    auto = snapshot.auto_leg
    search = snapshot.search_leg

    if auto is None and search is None:
        return CampaignClassificationV1(
            topology=CampaignTopology.UNKNOWN,
            payment_type=PaymentTypeAuthority.UNKNOWN,
            has_unknown_authoritative_fields=True,
            reason_codes=["NO_WB_LEGS"],
        )

    if _leg_has_unknown_fields(auto):
        has_unknown = True
        reason_codes.append("AUTO_LEG_UNKNOWN_FIELDS")
    if _leg_has_unknown_fields(search):
        has_unknown = True
        reason_codes.append("SEARCH_LEG_UNKNOWN_FIELDS")

    if auto is not None and search is not None:
        topology = CampaignTopology.AUTO_AND_SEARCH
    elif auto is not None:
        topology = CampaignTopology.AUTO_ONLY
    elif search is not None:
        topology = CampaignTopology.SEARCH_ONLY
    else:
        topology = CampaignTopology.UNKNOWN

    payment_types: set[PaymentTypeAuthority] = set()
    for leg in (auto, search):
        if leg is not None:
            payment_types.add(leg.payment_type)
    payment_types.discard(PaymentTypeAuthority.UNKNOWN)

    if len(payment_types) > 1:
        has_unknown = True
        reason_codes.append("CONFLICTING_PAYMENT_TYPES")
        payment_type = PaymentTypeAuthority.UNKNOWN
    elif len(payment_types) == 1:
        payment_type = next(iter(payment_types))
    else:
        payment_type = PaymentTypeAuthority.UNKNOWN
        has_unknown = True
        reason_codes.append("PAYMENT_TYPE_UNKNOWN")

    return CampaignClassificationV1(
        topology=topology,
        payment_type=payment_type,
        has_unknown_authoritative_fields=has_unknown,
        reason_codes=reason_codes,
    )
