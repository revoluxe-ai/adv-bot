"""Unit: сборка ``KeywordV3Context`` для V3."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.required_data_miss import ShopRunnerKeywordsCacheMissError
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
    load_campaign_v3_contexts,
    load_campaign_v3_contexts_from_database,
)
from tests.unit.auto_updater_v3.test_no_data_activation import (
    _kw as _calculated_kw_fixture,
)
from tests.unit.auto_updater_v3.test_no_data_activation import (
    _sample_profile,
)


@pytest.mark.unit
def test_build_keyword_v3_contexts_merges_profile() -> None:
    """``position_profile`` попадает в keyword и контекст."""
    from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
    from app.modules.predict_keywords_target_place.clickhouse_manager.dto import (
        BidPosition,
    )
    from datetime import datetime

    kw = _calculated_kw_fixture(
        ks_id=1, text="kw", mode=KeywordStrategyMode.MIN_CPA, conv=0.05
    )
    ts = datetime.now()
    bids = [BidPosition("kw", 1, 100, ts)]
    raw = {"kw": bids}
    contexts = build_keyword_v3_contexts([kw], raw)
    assert len(contexts) == 1
    assert contexts[0].position_profile is not None
    assert len(contexts[0].position_profile) == len(_sample_profile())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_campaign_v3_contexts_strict_redis_miss_raises() -> None:
    complex_adv = MagicMock()
    complex_adv.adv_id = 42
    complex_adv.get_keywords = AsyncMock(
        side_effect=ShopRunnerKeywordsCacheMissError(
            "miss", shop_id="s", adv_id=42
        )
    )

    with pytest.raises(ShopRunnerKeywordsCacheMissError):
        await load_campaign_v3_contexts(complex_adv, raw_profiles={})

    complex_adv.get_keywords.assert_awaited_once_with()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_campaign_v3_contexts_from_database() -> None:
    kw = MagicMock()
    complex_adv = MagicMock()
    with patch(
        "app.modules.wb_adv_updater.keywords_access.fetch_keywords_from_database",
        new=AsyncMock(return_value=[kw]),
    ) as fetch_db:
        result = await load_campaign_v3_contexts_from_database(
            complex_adv, raw_profiles={}
        )

    fetch_db.assert_awaited_once_with(complex_adv)
    assert len(result) == 1
