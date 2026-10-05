"""Strict WB normalization boundary tests."""

from __future__ import annotations

import pytest

from app.modules.wb_sky_control_plane.models.enums import (
    CampaignLegRole,
    PaymentTypeAuthority,
    PlacementFlagAuthority,
    ProductMembershipAuthority,
)
from app.modules.wb_sky_control_plane.read.normalizer import normalize_wb_campaign_leg

pytestmark = pytest.mark.unit


def test_missing_payment_type_and_placements_remain_unknown() -> None:
    """Missing/null payment_type and placements stay UNKNOWN (no CPM/false defaults)."""
    raw = {
        "id": 1001,
        "bid_type": "unified",
        "status": 9,
        "settings": {"name": "test-campaign"},
        "nm_settings": [{"nm_id": 123456}],
    }
    leg = normalize_wb_campaign_leg(raw, role=CampaignLegRole.AUTO)
    assert leg.payment_type == PaymentTypeAuthority.UNKNOWN
    assert leg.placements.search == PlacementFlagAuthority.UNKNOWN
    assert leg.placements.recommendations == PlacementFlagAuthority.UNKNOWN
    assert leg.product_membership == ProductMembershipAuthority.KNOWN
    assert leg.nm_ids == [123456]


def test_null_nm_settings_is_unknown_not_known_empty() -> None:
    """Null nm_settings → UNKNOWN membership, not known empty."""
    raw = {
        "id": 1002,
        "bid_type": "manual",
        "status": 11,
        "settings": {
            "payment_type": "cpm",
            "placements": {"search": True, "recommendations": False},
        },
        "nm_settings": None,
    }
    leg = normalize_wb_campaign_leg(raw, role=CampaignLegRole.SEARCH)
    assert leg.product_membership == ProductMembershipAuthority.UNKNOWN
    assert leg.nm_ids == []
    assert leg.payment_type == PaymentTypeAuthority.CPM


def test_missing_nm_settings_key_is_unknown() -> None:
    raw = {
        "id": 1004,
        "bid_type": "manual",
        "status": 11,
        "settings": {"payment_type": "cpm"},
    }
    leg = normalize_wb_campaign_leg(raw, role=CampaignLegRole.AUTO)
    assert leg.product_membership == ProductMembershipAuthority.UNKNOWN


def test_explicit_empty_nm_settings_is_known_empty() -> None:
    raw = {
        "id": 1005,
        "bid_type": "unified",
        "status": 9,
        "settings": {"payment_type": "cpm"},
        "nm_settings": [],
    }
    leg = normalize_wb_campaign_leg(raw, role=CampaignLegRole.AUTO)
    assert leg.product_membership == ProductMembershipAuthority.KNOWN_EMPTY
    assert leg.nm_ids == []


def test_malformed_nm_settings_member_is_unknown() -> None:
    raw = {
        "id": 1006,
        "bid_type": "unified",
        "status": 9,
        "settings": {"payment_type": "cpm"},
        "nm_settings": [{"nm_id": "not-a-number"}],
    }
    leg = normalize_wb_campaign_leg(raw, role=CampaignLegRole.AUTO)
    assert leg.product_membership == ProductMembershipAuthority.UNKNOWN


def test_malformed_nm_settings_list_is_unknown() -> None:
    raw = {
        "id": 1007,
        "bid_type": "unified",
        "status": 9,
        "settings": {"payment_type": "cpm"},
        "nm_settings": "bad",
    }
    leg = normalize_wb_campaign_leg(raw, role=CampaignLegRole.AUTO)
    assert leg.product_membership == ProductMembershipAuthority.UNKNOWN


def test_unknown_payment_type_value_is_unknown() -> None:
    """Unknown payment_type values fail closed to UNKNOWN."""
    raw = {
        "id": 1003,
        "bid_type": "unified",
        "status": 9,
        "settings": {
            "payment_type": "weird",
            "placements": {"search": False},
        },
        "nm_settings": [],
    }
    leg = normalize_wb_campaign_leg(raw, role=CampaignLegRole.AUTO)
    assert leg.payment_type == PaymentTypeAuthority.UNKNOWN
    assert leg.product_membership == ProductMembershipAuthority.KNOWN_EMPTY
