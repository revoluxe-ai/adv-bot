"""Unit tests for connect_existing_advs filter and classification."""

import pytest

from app.modules.connect_existing_advs.candidates_service import (
    filter_and_classify_campaigns_by_nmid,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    GetAdvertsAdvertsItem,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.get_adverts_adverts_item_status import (
    GetAdvertsAdvertsItemStatus,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.advert_settings import (
    AdvertSettings,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.advert_settings_placements import (
    AdvertSettingsPlacements,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.advert_settings_payment_type import (
    AdvertSettingsPaymentType,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.advert_n_ms_settings import (
    AdvertNMsSettings,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.advert_bids_kopecks import (
    AdvertBidsKopecks,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.advert_subject import (
    AdvertSubject,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.timestamps import (
    Timestamps,
)
import datetime


def _make_nm_setting(nm_id: int) -> AdvertNMsSettings:
    return AdvertNMsSettings(
        bids_kopecks=AdvertBidsKopecks(search=1000, recommendations=1000),
        subject=AdvertSubject(id=1, name="x"),
        nm_id=nm_id,
    )


def _make_placements(search: bool, recommendations: bool, shelf: bool = False) -> AdvertSettingsPlacements:
    p = AdvertSettingsPlacements(search=search, recommendations=recommendations)
    if shelf:
        p["shelf"] = True
    return p


def _make_item(
    id: int,
    bid_type: str,
    payment_type: AdvertSettingsPaymentType,
    search: bool,
    recommendations: bool,
    shelf: bool,
    nmid: int,
    status: GetAdvertsAdvertsItemStatus,
    name: str = "Campaign",
) -> GetAdvertsAdvertsItem:
    settings = AdvertSettings(
        payment_type=payment_type,
        name=name,
        placements=_make_placements(search, recommendations, shelf),
    )
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    timestamps = Timestamps(created=now, updated=now, started=now, deleted=now)
    return GetAdvertsAdvertsItem(
        bid_type=bid_type,
        id=id,
        nm_settings=[_make_nm_setting(nmid)],
        settings=settings,
        status=status,
        timestamps=timestamps,
    )


@pytest.mark.unit
def test_filter_and_classify_empty_list() -> None:
    result = filter_and_classify_campaigns_by_nmid([], 12345)
    assert result.auction_candidates == []
    assert result.auto_candidates == []


@pytest.mark.unit
def test_filter_by_status_excludes_done() -> None:
    """Status 7 (done) and -1 (deleted) must be excluded."""
    nmid = 100
    # Auction campaign but status done (7)
    item_done = _make_item(
        id=1,
        bid_type="manual",
        payment_type=AdvertSettingsPaymentType.CPM,
        search=True,
        recommendations=False,
        shelf=False,
        nmid=nmid,
        status=GetAdvertsAdvertsItemStatus.VALUE_7,
    )
    result = filter_and_classify_campaigns_by_nmid([item_done], nmid)
    assert result.auction_candidates == []
    assert result.auto_candidates == []


@pytest.mark.unit
def test_filter_by_nmid() -> None:
    """Only campaigns with nm_settings nm_id == nmid are kept."""
    nmid = 999
    other_nmid = 888
    item_match = _make_item(
        id=1,
        bid_type="manual",
        payment_type=AdvertSettingsPaymentType.CPM,
        search=True,
        recommendations=False,
        shelf=False,
        nmid=nmid,
        status=GetAdvertsAdvertsItemStatus.VALUE_9,
    )
    item_other = _make_item(
        id=2,
        bid_type="manual",
        payment_type=AdvertSettingsPaymentType.CPM,
        search=True,
        recommendations=False,
        shelf=False,
        nmid=other_nmid,
        status=GetAdvertsAdvertsItemStatus.VALUE_9,
    )
    result = filter_and_classify_campaigns_by_nmid([item_match, item_other], nmid)
    assert len(result.auction_candidates) == 1
    assert result.auction_candidates[0].id == 1
    assert result.auto_candidates == []


@pytest.mark.unit
def test_classify_auction_manual_search_cpm() -> None:
    """manual + search true + recommendations false + shelf false + cpm -> auction."""
    nmid = 100
    item = _make_item(
        id=10,
        bid_type="manual",
        payment_type=AdvertSettingsPaymentType.CPM,
        search=True,
        recommendations=False,
        shelf=False,
        nmid=nmid,
        status=GetAdvertsAdvertsItemStatus.VALUE_9,
    )
    result = filter_and_classify_campaigns_by_nmid([item], nmid)
    assert len(result.auction_candidates) == 1
    assert result.auction_candidates[0].id == 10
    assert result.auto_candidates == []


@pytest.mark.unit
def test_classify_auto_unified_shelf_recommendations_cpm() -> None:
    """unified + search false + shelf/recommendations + cpm -> auto."""
    nmid = 100
    item = _make_item(
        id=20,
        bid_type="unified",
        payment_type=AdvertSettingsPaymentType.CPM,
        search=False,
        recommendations=True,
        shelf=True,
        nmid=nmid,
        status=GetAdvertsAdvertsItemStatus.VALUE_9,
    )
    result = filter_and_classify_campaigns_by_nmid([item], nmid)
    assert result.auction_candidates == []
    assert len(result.auto_candidates) == 1
    assert result.auto_candidates[0].id == 20


@pytest.mark.unit
def test_cpc_excluded() -> None:
    """payment_type cpc campaigns are not classified as auction/auto for CPM connect."""
    nmid = 100
    item = _make_item(
        id=30,
        bid_type="manual",
        payment_type=AdvertSettingsPaymentType.CPC,
        search=True,
        recommendations=False,
        shelf=False,
        nmid=nmid,
        status=GetAdvertsAdvertsItemStatus.VALUE_9,
    )
    result = filter_and_classify_campaigns_by_nmid([item], nmid)
    assert result.auction_candidates == []
    assert result.auto_candidates == []


@pytest.mark.unit
def test_allowed_statuses_4_9_11() -> None:
    """Status 4, 9, 11 are allowed (ready_for_start, active, pause)."""
    nmid = 100
    items = [
        _make_item(1, "manual", AdvertSettingsPaymentType.CPM, True, False, False, nmid, GetAdvertsAdvertsItemStatus.VALUE_4),
        _make_item(2, "manual", AdvertSettingsPaymentType.CPM, True, False, False, nmid, GetAdvertsAdvertsItemStatus.VALUE_9),
        _make_item(3, "manual", AdvertSettingsPaymentType.CPM, True, False, False, nmid, GetAdvertsAdvertsItemStatus.VALUE_11),
    ]
    result = filter_and_classify_campaigns_by_nmid(items, nmid)
    assert len(result.auction_candidates) == 3
    assert result.auto_candidates == []


@pytest.mark.unit
def test_auction_included_when_recommendations_true() -> None:
    """manual + search true and recommendations True -> still auction (API may return both)."""
    nmid = 100
    item = _make_item(
        id=1,
        bid_type="manual",
        payment_type=AdvertSettingsPaymentType.CPM,
        search=True,
        recommendations=True,
        shelf=False,
        nmid=nmid,
        status=GetAdvertsAdvertsItemStatus.VALUE_9,
    )
    result = filter_and_classify_campaigns_by_nmid([item], nmid)
    assert len(result.auction_candidates) == 1
    assert result.auto_candidates == []


@pytest.mark.unit
def test_auto_classified_with_shelf_only_via_additional_properties() -> None:
    """unified + search false + shelf only via additional_properties (no recommendations) -> auto."""
    nmid = 100
    placements = AdvertSettingsPlacements(search=False, recommendations=False)
    placements["shelf"] = True
    settings = AdvertSettings(
        payment_type=AdvertSettingsPaymentType.CPM,
        name="AutoShelf",
        placements=placements,
    )
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    timestamps = Timestamps(created=now, updated=now, started=now, deleted=now)
    item = GetAdvertsAdvertsItem(
        bid_type="unified",
        id=21,
        nm_settings=[_make_nm_setting(nmid)],
        settings=settings,
        status=GetAdvertsAdvertsItemStatus.VALUE_9,
        timestamps=timestamps,
    )
    result = filter_and_classify_campaigns_by_nmid([item], nmid)
    assert result.auction_candidates == []
    assert len(result.auto_candidates) == 1
    assert result.auto_candidates[0].id == 21


@pytest.mark.unit
def test_auto_classified_with_shelf_only_recommendations_false() -> None:
    """unified + search false + shelf true + recommendations false -> auto (shelf or recs)."""
    nmid = 100
    item = _make_item(
        id=22,
        bid_type="unified",
        payment_type=AdvertSettingsPaymentType.CPM,
        search=False,
        recommendations=False,
        shelf=True,
        nmid=nmid,
        status=GetAdvertsAdvertsItemStatus.VALUE_9,
    )
    result = filter_and_classify_campaigns_by_nmid([item], nmid)
    assert result.auction_candidates == []
    assert len(result.auto_candidates) == 1
    assert result.auto_candidates[0].id == 22


@pytest.mark.unit
def test_filter_by_nmid_includes_campaign_with_multiple_nm_ids() -> None:
    """Item with nm_settings containing target nmid (and others) is included."""
    target_nmid = 100
    other_nmid = 200
    item = _make_item(
        id=1,
        bid_type="manual",
        payment_type=AdvertSettingsPaymentType.CPM,
        search=True,
        recommendations=False,
        shelf=False,
        nmid=target_nmid,
        status=GetAdvertsAdvertsItemStatus.VALUE_9,
    )
    item.nm_settings = [_make_nm_setting(target_nmid), _make_nm_setting(other_nmid)]
    result = filter_and_classify_campaigns_by_nmid([item], target_nmid)
    assert len(result.auction_candidates) == 1
    assert result.auto_candidates == []
