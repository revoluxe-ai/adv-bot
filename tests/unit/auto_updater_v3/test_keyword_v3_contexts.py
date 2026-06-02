"""Unit: сборка ``KeywordV3Context`` для V3."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
    load_campaign_v3_contexts,
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
async def test_load_campaign_v3_contexts_miss_returns_empty_without_redis_fallback() -> None:
    """При cache miss — пустой список; повторного чтения Redis нет."""
    complex_adv = MagicMock()
    complex_adv.adv_id = 42
    complex_adv.get_keywords = AsyncMock(return_value=None)

    with patch(
        "app.modules.calculated_keywords_redis_cache_manager.redis_manager."
        "RedisCalculatedKeywordsCacheManager"
    ) as redis_cls:
        result = await load_campaign_v3_contexts(complex_adv, raw_profiles={})

    assert result == []
    complex_adv.get_keywords.assert_awaited_once_with(
        cache_only=True, allow_miss=True
    )
    redis_cls.assert_not_called()
