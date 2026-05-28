"""Unit-тесты gap-rebalance V3 (дыра OFF в сортировке MIN_CPO)."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rebalance import (
    find_first_ladder_gap_index,
    plan_ladder_gap_rebalance,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_cpm_sources import (
    KeywordCpmSources,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)

from tests.unit.auto_updater_v3.conftest import sample_profile


def _conv_for_pay_for_order(target_pfo: float, *, cpm: int = 200) -> float:
    return cpm * 1000.0 / (target_pfo * 1_000_000.0)


def _wl_kw(
    *,
    ks_id: int,
    mode: KeywordStrategyMode,
    target_pfo: float,
) -> CalculatedKeyword:
    conv = _conv_for_pay_for_order(target_pfo)
    stat = make_zero_keyword_stat(f"k{ks_id}").model_copy(
        update={"views": 50, "clicks": 10, "orders": 2, "conv_views_to_orders": conv}
    )
    return CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text=f"k{ks_id}",
            relevant=True,
            hard_status=2,
            id=ks_id,
            strategy_mode=mode,
        ),
        cluster_stat=stat,
        state=KeywordState(
            status=KeywordStatus.GOOD,
            reason=KeywordStatusReason.WHITE_LIST,
            best_keyword_status=False,
        ),
        rating=1.0,
        target_pay_for_order=None,
        cpm_sources=KeywordCpmSources(cpm_set_bid=200),
    )


def _prepared_from_keywords(keywords: list[CalculatedKeyword]) -> list:
    prof = sample_profile()
    return [
        (
            KeywordV3Context(keyword=kw, position_profile=prof),
            kw.keyword_setting.strategy_mode,
        )
        for kw in keywords
    ]


@pytest.mark.unit
def test_find_first_ladder_gap_index_none_when_no_hole() -> None:
    sorted_wl = [
        _wl_kw(ks_id=1, mode=KeywordStrategyMode.MIN_CPA, target_pfo=50),
        _wl_kw(ks_id=2, mode=KeywordStrategyMode.OPTIMUM, target_pfo=80),
    ]
    assert find_first_ladder_gap_index(sorted_wl, contexts=[]) is None


@pytest.mark.unit
def test_find_first_ladder_gap_index_detects_off_with_active_below() -> None:
    sorted_wl = [
        _wl_kw(ks_id=1, mode=KeywordStrategyMode.MIN_CPA, target_pfo=50),
        _wl_kw(ks_id=2, mode=KeywordStrategyMode.OFF, target_pfo=80),
        _wl_kw(ks_id=3, mode=KeywordStrategyMode.OPTIMUM, target_pfo=120),
        _wl_kw(ks_id=4, mode=KeywordStrategyMode.MAX_CONVERSION, target_pfo=200),
    ]
    assert find_first_ladder_gap_index(sorted_wl, contexts=[]) == 1


@pytest.mark.unit
def test_plan_ladder_gap_rebalance_tail_force_off_and_budget() -> None:
    keywords = [
        _wl_kw(ks_id=1, mode=KeywordStrategyMode.MIN_CPA, target_pfo=50),
        _wl_kw(ks_id=2, mode=KeywordStrategyMode.OFF, target_pfo=80),
        _wl_kw(ks_id=3, mode=KeywordStrategyMode.OPTIMUM, target_pfo=120),
        _wl_kw(ks_id=4, mode=KeywordStrategyMode.MAX_CONVERSION, target_pfo=200),
        _wl_kw(ks_id=99, mode=KeywordStrategyMode.MAX_CONVERSION, target_pfo=10),
    ]
    kw99 = keywords[-1]
    kw99.keyword_setting = kw99.keyword_setting.model_copy(update={"hard_status": 1})

    prepared = _prepared_from_keywords(keywords)
    actions = plan_ladder_gap_rebalance(
        prepared,
        shelf_promotion_active=False,
        shelf_click_mode=ShelfClickMode.UNKNOWN,
        rollout_aggressiveness=1,
    )
    force_offs = [a for a in actions if a.action == V3ActionType.FORCE_OFF]
    assert len(force_offs) == 2
    assert {a.keyword_setting_id for a in force_offs} == {3, 4}
    assert 2 not in {a.keyword_setting_id for a in force_offs}
    up_count = sum(1 for a in actions if a.action == V3ActionType.UP)
    assert up_count <= 5
