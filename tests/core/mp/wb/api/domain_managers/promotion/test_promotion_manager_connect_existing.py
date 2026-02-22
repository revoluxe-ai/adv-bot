"""Unit tests for PromotionManager.get_connect_existing_candidates."""

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.mp.wb.api.domain_managers.promotion.promotion_manager import (
    PromotionManager,
)
from app.core.mp.wb.api.adapter.promotion_client.promotion_client import (
    PromotionClient,
)
from app.modules.connect_existing_advs.candidates_service import (
    ConnectExistingCandidatesResult,
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


def _make_auction_item(item_id: int, nmid: int) -> GetAdvertsAdvertsItem:
    """One auction-type campaign for nmid."""
    placements = AdvertSettingsPlacements(search=True, recommendations=False)
    settings = AdvertSettings(
        payment_type=AdvertSettingsPaymentType.CPM,
        name="AuctionCampaign",
        placements=placements,
    )
    nm_settings = [
        AdvertNMsSettings(
            bids_kopecks=AdvertBidsKopecks(search=1000, recommendations=1000),
            subject=AdvertSubject(id=1, name="x"),
            nm_id=nmid,
        )
    ]
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    timestamps = Timestamps(created=now, updated=now, started=now, deleted=now)
    return GetAdvertsAdvertsItem(
        bid_type="manual",
        id=item_id,
        nm_settings=nm_settings,
        settings=settings,
        status=GetAdvertsAdvertsItemStatus.VALUE_9,
        timestamps=timestamps,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_connect_existing_candidates_flow() -> None:
    """get_connect_existing_candidates calls adapters and returns classified result."""
    mock_promotion_count = AsyncMock(return_value=[1, 2])
    auction_item = _make_auction_item(item_id=1, nmid=100)
    mock_campaigns_info = AsyncMock(return_value=[auction_item])

    mock_client = MagicMock(spec=PromotionClient)
    mock_client.promotion_count_adapter.get_cabinet_adv_ids = mock_promotion_count
    mock_client.campaigns_info_v2_adapter.get_campaigns_info = mock_campaigns_info

    manager = PromotionManager(promotion_client=mock_client)
    result = await manager.get_connect_existing_candidates(100)

    assert isinstance(result, ConnectExistingCandidatesResult)
    mock_promotion_count.assert_called_once()
    mock_campaigns_info.assert_called_once_with([1, 2])
    assert len(result.auction_candidates) == 1
    assert result.auction_candidates[0].id == 1
    assert result.auto_candidates == []
