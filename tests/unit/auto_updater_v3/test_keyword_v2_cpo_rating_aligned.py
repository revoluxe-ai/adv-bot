"""Unit: V2 CPO для NO_CH — conv CH + CPM set_bid/stats (как rating), без bid_log."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    rating_aligned_cpm,
    resolve_keyword_v2_pay_for_order_cost,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_orders_per_1000_rub,
    calc_pay_for_order,
)
from tests.unit.auto_updater_v3.test_no_data_activation import _kw


@pytest.mark.unit
def test_rating_aligned_cpm_prefers_set_bid_over_bid_log() -> None:
    kw = _kw(
        ks_id=1,
        text="a",
        mode=KeywordStrategyMode.OFF,
        conv=0.05,
        cpm_set_bid=510,
    )
    sources = kw.cpm_sources
    assert sources is not None
    kw = kw.model_copy(
        update={
            "cpm_sources": sources.model_copy(update={"cpm_from_bid_log": 3990.0}),
        }
    )
    assert rating_aligned_cpm(kw) == 510.0
    assert kw.cpm == 510.0


@pytest.mark.unit
def test_rating_aligned_cpm_skips_zero_set_bid_uses_stats() -> None:
    """``cpm_set_bid == 0`` не блокирует ``cpm_from_stats``."""
    conv = 0.00139
    kw = _kw(
        ks_id=4,
        text="zero_set_bid",
        mode=KeywordStrategyMode.OFF,
        conv=conv,
        cpm_set_bid=0,
    )
    sources = kw.cpm_sources
    assert sources is not None
    kw = kw.model_copy(
        update={
            "cpm_sources": sources.model_copy(
                update={"cpm_from_stats": 510.0, "cpm_from_bid_log": 3990.0}
            ),
        }
    )
    assert rating_aligned_cpm(kw) == 510.0


@pytest.mark.unit
def test_resolve_v2_cpo_uses_worst_min_when_no_rating_cpm() -> None:
    """Нет rating CPM → pessimistic MIN CPA с других ключей, не ``pay_for_order``/bid_log."""
    kw = _kw(
        ks_id=5,
        text="no_cpm",
        mode=KeywordStrategyMode.OFF,
        conv=0.05,
        cpm_set_bid=0,
    )
    sources = kw.cpm_sources
    assert sources is not None
    kw = kw.model_copy(
        update={
            "cpm_sources": sources.model_copy(
                update={
                    "cpm_set_bid": 0,
                    "cpm_from_stats": 0.0,
                    "cpm_from_bid_log": 3990.0,
                }
            ),
        }
    )
    assert rating_aligned_cpm(kw) is None
    worst = {AggressionTargetMode.MIN_CPA: 120.0}
    cost = resolve_keyword_v2_pay_for_order_cost(kw, worst_costs=worst)
    assert cost == 120.0
    assert resolve_keyword_v2_pay_for_order_cost(kw, worst_costs=None) is None


@pytest.mark.unit
def test_resolve_v2_cpo_matches_rating_formula_not_cascade_bid_log() -> None:
    """При отсутствии set_bid rating берёт stats, каскад — bid_log → разный CPO."""
    conv = 0.00139
    cpm_stats = 510.0
    cpm_bid_log = 3990.0
    kw = _kw(
        ks_id=2,
        text="b",
        mode=KeywordStrategyMode.OFF,
        conv=conv,
        cpm_set_bid=0,
    )
    sources = kw.cpm_sources
    assert sources is not None
    kw = kw.model_copy(
        update={
            "cpm_sources": sources.model_copy(
                update={
                    "cpm_set_bid": None,
                    "cpm_from_bid_log": cpm_bid_log,
                    "cpm_from_stats": cpm_stats,
                }
            ),
        }
    )
    expected = calc_pay_for_order(
        calc_orders_per_1000_rub(conv, cpm_stats)  # type: ignore[arg-type]
    )
    assert expected is not None
    rating_cost = resolve_keyword_v2_pay_for_order_cost(kw)
    assert rating_cost is not None
    assert abs(rating_cost - expected) < 0.5
    cascade = kw.pay_for_order
    assert cascade is not None
    assert cascade > rating_cost * 5


@pytest.mark.unit
def test_resolve_v2_cpo_ignores_precomputed_pay_for_order_with_bid_log() -> None:
    """Не возвращать keyword.pay_for_order, если он посчитан по bid_log."""
    conv = 0.00139
    kw = _kw(ks_id=3, text="c", mode=KeywordStrategyMode.OFF, conv=conv, cpm_set_bid=510)
    sources = kw.cpm_sources
    assert sources is not None
    kw = kw.model_copy(
        update={
            "cpm_sources": sources.model_copy(update={"cpm_from_bid_log": 3990.0}),
        }
    )
    assert kw.pay_for_order is not None
    rating_cost = resolve_keyword_v2_pay_for_order_cost(kw)
    assert rating_cost is not None
    assert abs(rating_cost - kw.pay_for_order) < 0.5
