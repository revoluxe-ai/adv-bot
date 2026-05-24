"""Tests for v2 adverts response to legacy format converter."""

import pytest

from app.core.wb_api.data_classes.advs import adv_fabric
from app.core.wb_api.v2_adverts_to_legacy import v2_advert_item_to_legacy


@pytest.fixture
def v2_item_manual() -> dict:
    """Sample GET /api/advert/v2/adverts item (bid_type=manual, type 9)."""
    return {
        "id": 12345,
        "bid_type": "manual",
        "status": 9,
        "settings": {
            "name": "Test Search Campaign",
            "payment_type": "cpm",
            "placements": {"search": True, "recommendations": False},
        },
        "nm_settings": [
            {
                "nm_id": 1000001,
                "subject": {"id": 42, "name": "Subject Name"},
                "bids_kopecks": {"search": 5000, "recommendations": 1000},
            }
        ],
        "timestamps": {
            "created": "2025-01-01T10:00:00",
            "updated": "2025-01-02T12:00:00",
            "started": "2025-01-02T12:00:00",
            "deleted": "2030-01-01T00:00:00",
        },
    }


@pytest.fixture
def v2_item_unified() -> dict:
    """Sample GET /api/advert/v2/adverts item (bid_type=unified, type 8)."""
    return {
        "id": 67890,
        "bid_type": "unified",
        "status": 4,
        "settings": {
            "name": "Test Auto Campaign",
            "payment_type": "cpm",
            "placements": {"search": False, "recommendations": True},
        },
        "nm_settings": [
            {
                "nm_id": 2000002,
                "subject": {"id": 10, "name": "Auto Subject"},
                "bids_kopecks": {"search": 0, "recommendations": 3000},
            }
        ],
        "timestamps": {
            "created": "2025-02-01T00:00:00",
            "updated": "2025-02-02T00:00:00",
            "started": None,
            "deleted": "2030-01-01T00:00:00",
        },
    }


@pytest.mark.unit
def test_v2_advert_item_to_legacy_manual_maps_id_and_type(v2_item_manual: dict) -> None:
    legacy = v2_advert_item_to_legacy(v2_item_manual)
    assert legacy["advertId"] == 12345
    assert legacy["type"] == 9
    assert legacy["bidType"] == "manual"
    assert legacy["name"] == "Test Search Campaign"
    assert legacy["status"] == 9
    assert legacy["dailyBudget"] == 0


@pytest.mark.unit
def test_v2_advert_item_to_legacy_unified_maps_type_8(v2_item_unified: dict) -> None:
    legacy = v2_advert_item_to_legacy(v2_item_unified)
    assert legacy["advertId"] == 67890
    assert legacy["type"] == 8
    assert legacy["bidType"] == "unified"
    assert legacy["name"] == "Test Auto Campaign"
    assert legacy["status"] == 4


@pytest.mark.unit
def test_v2_advert_item_to_legacy_has_auto_params(v2_item_manual: dict) -> None:
    legacy = v2_advert_item_to_legacy(v2_item_manual)
    ap = legacy["autoParams"]
    assert ap["subject"] == {"id": 42, "name": "Subject Name"}
    assert ap["active"]["search"] is True
    assert ap["active"]["recom"] is False
    assert ap["active"]["booster"] is False
    assert ap["active"]["carousel"] is False


@pytest.mark.unit
def test_v2_advert_item_to_legacy_united_params_and_nmids(v2_item_manual: dict) -> None:
    legacy = v2_advert_item_to_legacy(v2_item_manual)
    assert legacy["unitedParams"] == [
        {
            "searchCPM": 5000,
            "subject": {"id": 42, "name": "Subject Name"},
            "nms": [1000001],
        }
    ]
    assert legacy["auction_multibids"] == [{"bid": 5000}]


@pytest.mark.unit
def test_v2_advert_item_to_legacy_timestamps(v2_item_manual: dict) -> None:
    legacy = v2_advert_item_to_legacy(v2_item_manual)
    assert "createTime" in legacy
    assert "changeTime" in legacy
    assert "startTime" in legacy
    assert "endTime" in legacy
    assert legacy["createTime"] == "2025-01-01T10:00:00"
    assert legacy["changeTime"] == "2025-01-02T12:00:00"


@pytest.mark.unit
def test_v2_to_legacy_then_adv_fabric_manual_returns_auction_adv(
    v2_item_manual: dict,
) -> None:
    legacy = v2_advert_item_to_legacy(v2_item_manual)
    adv = adv_fabric.get_adv_data_class(legacy)
    assert adv is not None
    assert adv.advertId == 12345
    assert adv.type == 9
    assert adv.name == "Test Search Campaign"
    assert adv.nmids == [1000001]
    assert adv.cpm == 5000


@pytest.mark.unit
def test_v2_to_legacy_then_adv_fabric_unified_returns_auto_adv(
    v2_item_unified: dict,
) -> None:
    legacy = v2_advert_item_to_legacy(v2_item_unified)
    adv = adv_fabric.get_adv_data_class(legacy)
    assert adv is not None
    assert adv.advertId == 67890
    assert adv.type == 8
    assert adv.nmids == [2000002]
    assert adv.cpm == 3000


@pytest.mark.unit
def test_v2_advert_item_to_legacy_empty_nm_settings() -> None:
    item = {
        "id": 1,
        "bid_type": "manual",
        "status": 4,
        "settings": {"name": "Empty", "payment_type": "cpm", "placements": {}},
        "nm_settings": [],
        "timestamps": {},
    }
    legacy = v2_advert_item_to_legacy(item)
    assert legacy["advertId"] == 1
    assert legacy["type"] == 9
    assert legacy["autoParams"]["subject"] == {"id": 0, "name": ""}
    assert legacy["unitedParams"] == [{"searchCPM": 0, "subject": {"id": 0, "name": ""}, "nms": []}]
    assert legacy["auction_multibids"] == [{"bid": 0}]


@pytest.mark.unit
def test_v2_advert_item_to_legacy_exports_recommendations_bids_map(
    v2_item_unified: dict,
) -> None:
    legacy = v2_advert_item_to_legacy(v2_item_unified)
    assert legacy["recommendationsBidsByNmidKopecks"] == {2000002: 3000}
