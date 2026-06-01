"""Unit: сборка ``KeywordV3Context`` для V3."""

from __future__ import annotations

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
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
