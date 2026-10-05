"""Strict raw normalization boundary для WB promotion v2 adverts.

Missing/null payment_type, placements остаются UNKNOWN;
missing/null/malformed nm_settings → product_membership UNKNOWN (не known empty).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from app.modules.wb_sky_control_plane.models.enums import (
    BidTypeAuthority,
    CampaignLegRole,
    PaymentTypeAuthority,
    PlacementFlagAuthority,
    ProductMembershipAuthority,
    WbCampaignStatusAuthority,
)
from app.modules.wb_sky_control_plane.models.snapshot import (
    CampaignLegSnapshotV1,
    PlacementAuthorityV1,
)


def _normalize_payment_type(raw: object | None) -> PaymentTypeAuthority:
    if raw is None:
        return PaymentTypeAuthority.UNKNOWN
    value = str(raw).strip().lower()
    if value in ("cpm", "cpc"):
        return PaymentTypeAuthority(value)
    return PaymentTypeAuthority.UNKNOWN


def _normalize_placement_flag(raw: object | None) -> PlacementFlagAuthority:
    if raw is None:
        return PlacementFlagAuthority.UNKNOWN
    if isinstance(raw, bool):
        return PlacementFlagAuthority.TRUE if raw else PlacementFlagAuthority.FALSE
    text = str(raw).strip().lower()
    if text in ("true", "1", "yes"):
        return PlacementFlagAuthority.TRUE
    if text in ("false", "0", "no"):
        return PlacementFlagAuthority.FALSE
    return PlacementFlagAuthority.UNKNOWN


def _normalize_bid_type(raw: object | None) -> BidTypeAuthority:
    if raw is None:
        return BidTypeAuthority.UNKNOWN
    value = str(raw).strip().lower()
    if value in ("unified", "manual"):
        return BidTypeAuthority(value)
    return BidTypeAuthority.UNKNOWN


def _normalize_status(raw: object | None) -> WbCampaignStatusAuthority:
    if raw is None:
        return WbCampaignStatusAuthority.UNKNOWN
    value = str(raw).strip()
    for member in WbCampaignStatusAuthority:
        if member.value == value:
            return member
    return WbCampaignStatusAuthority.UNKNOWN


@dataclass(frozen=True, slots=True)
class _ProductMembershipExtract:
    """Result of nm_settings normalization with explicit certainty."""

    membership: ProductMembershipAuthority
    nm_ids: list[int]


def _extract_product_membership(raw_item: Mapping[str, Any]) -> _ProductMembershipExtract:
    """Normalize product membership: UNKNOWN unless explicitly authoritative."""
    if "nm_settings" not in raw_item:
        return _ProductMembershipExtract(
            membership=ProductMembershipAuthority.UNKNOWN,
            nm_ids=[],
        )
    nm_settings = raw_item.get("nm_settings")
    if nm_settings is None:
        return _ProductMembershipExtract(
            membership=ProductMembershipAuthority.UNKNOWN,
            nm_ids=[],
        )
    if not isinstance(nm_settings, list):
        return _ProductMembershipExtract(
            membership=ProductMembershipAuthority.UNKNOWN,
            nm_ids=[],
        )
    nm_entries = cast(list[Any], nm_settings)
    if len(nm_entries) == 0:
        return _ProductMembershipExtract(
            membership=ProductMembershipAuthority.KNOWN_EMPTY,
            nm_ids=[],
        )
    nm_ids: list[int] = []
    for entry in nm_entries:
        if not isinstance(entry, Mapping):
            return _ProductMembershipExtract(
                membership=ProductMembershipAuthority.UNKNOWN,
                nm_ids=[],
            )
        nm_raw: object | None = entry.get("nm_id")
        if nm_raw is None:
            nm_raw = entry.get("nmId")
        if nm_raw is None:
            return _ProductMembershipExtract(
                membership=ProductMembershipAuthority.UNKNOWN,
                nm_ids=[],
            )
        if not isinstance(nm_raw, (int, str)):
            return _ProductMembershipExtract(
                membership=ProductMembershipAuthority.UNKNOWN,
                nm_ids=[],
            )
        try:
            nm_ids.append(int(nm_raw))
        except (TypeError, ValueError):
            return _ProductMembershipExtract(
                membership=ProductMembershipAuthority.UNKNOWN,
                nm_ids=[],
            )
    return _ProductMembershipExtract(
        membership=ProductMembershipAuthority.KNOWN,
        nm_ids=sorted(set(nm_ids)),
    )


def normalize_wb_campaign_leg(
    raw_item: Mapping[str, Any],
    *,
    role: CampaignLegRole,
) -> CampaignLegSnapshotV1:
    """Normalize one raw WB v2 advert dict into authoritative leg snapshot."""
    settings_raw = raw_item.get("settings")
    settings: Mapping[str, Any] = settings_raw if isinstance(settings_raw, Mapping) else {}

    placements_raw = settings.get("placements")
    placements_map: Mapping[str, Any] = (
        placements_raw if isinstance(placements_raw, Mapping) else {}
    )

    wb_adv_id_raw = raw_item.get("id")
    if wb_adv_id_raw is None:
        raise ValueError("WB advert id is required for normalization")

    product = _extract_product_membership(raw_item)

    return CampaignLegSnapshotV1(
        wb_adv_id=int(wb_adv_id_raw),
        role=role,
        bid_type=_normalize_bid_type(raw_item.get("bid_type")),
        payment_type=_normalize_payment_type(settings.get("payment_type")),
        placements=PlacementAuthorityV1(
            search=_normalize_placement_flag(placements_map.get("search")),
            recommendations=_normalize_placement_flag(
                placements_map.get("recommendations")
            ),
        ),
        status=_normalize_status(raw_item.get("status")),
        product_membership=product.membership,
        nm_ids=product.nm_ids,
        name=str(settings.get("name")) if settings.get("name") is not None else None,
    )


def normalize_wb_campaign_batch(
    raw_items: list[Mapping[str, Any]],
) -> dict[int, CampaignLegSnapshotV1]:
    """Normalize batch keyed by wb_adv_id; skip items without id (caller validates)."""
    out: dict[int, CampaignLegSnapshotV1] = {}
    for raw in raw_items:
        wb_id = raw.get("id")
        if wb_id is None:
            continue
        leg = normalize_wb_campaign_leg(raw, role=CampaignLegRole.AUTO)
        out[int(wb_id)] = leg
    return out
