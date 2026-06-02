from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from app.snapshot_data_updater.mappers.keyword_mapper import (
    calculated_keyword_to_snapshot,
    strategy_mode_to_snapshot_str,
)


@pytest.mark.unit
def test_strategy_mode_int_enum_maps_to_name_not_value() -> None:
    assert strategy_mode_to_snapshot_str(KeywordStrategyMode.OFF) == "OFF"
    assert strategy_mode_to_snapshot_str(KeywordStrategyMode.MIN_CPA) == "MIN_CPA"


@pytest.mark.unit
def test_calculated_keyword_to_snapshot_maps_cluster_text() -> None:
    kw = MagicMock()
    kw.text = "phrase"
    kw.adv_id = 1
    kw.status = KeywordStatus.GOOD
    kw.reason = None
    kw.rating = 1.0
    kw.cpm = 100.0
    kw.target_pay_for_order = None
    kw.above_rec_conversion = None
    kw.views = 1
    kw.clicks = 1
    kw.orders = 0
    kw.spend = 0.0
    kw.keyword_setting_original_id = 10
    kw.cluster_stat.text = "norm-query"
    kw.hard_status = 1
    kw.strategy_mode = KeywordStrategyMode.OFF
    kw.target_place = None
    kw.position = 1.0
    kw.conv_views_to_orders = 0.1
    kw.orders_per_1000_rub = 1.0
    kw.pay_for_order = None
    kw.cpm_set_bid = None
    kw.cpm_from_bid_log = None
    kw.cpm_from_stats = None
    kw.predict_ctr = None
    kw.added_clicks = 0
    kw.relevant = True
    kw.timestamp = None
    kw.total_views = None
    kw.total_orders = None
    kw.cpm_sources = None

    snap = calculated_keyword_to_snapshot(kw)
    assert snap.cluster_text == "norm-query"
    assert snap.text == "phrase"
    assert snap.strategy_mode == "OFF"
