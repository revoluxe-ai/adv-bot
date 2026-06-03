"""Unit: фаза enable (NO DATA OFF→MIN) — headroom gate fact < 0.9×resolve."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    KeywordV3DecisionTier,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    KeywordV3Eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_preamble_phases import (
    plan_pay_for_order_gap_enable,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
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


def _ctx(*, ks_id: int, mode: KeywordStrategyMode = KeywordStrategyMode.OFF) -> KeywordV3Context:
    kw = CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text=f"k{ks_id}",
            relevant=True,
            hard_status=2,
            id=ks_id,
            strategy_mode=mode,
        ),
        cluster_stat=make_zero_keyword_stat(f"k{ks_id}"),
        state=KeywordState(
            status=KeywordStatus.GOOD,
            reason=KeywordStatusReason.WHITE_LIST,
            best_keyword_status=False,
        ),
        rating=1.0,
        target_pay_for_order=None,
        pay_for_order=None,
    )
    return KeywordV3Context(keyword=kw, position_profile=None)


def _no_data_elig() -> KeywordV3Eligibility:
    return KeywordV3Eligibility(
        data_tier=KeywordDataTier.KEYWORD_NO_DATA,
        allowed_modes=frozenset(),
        max_allowed_mode=KeywordStrategyMode.OFF,
        participates_in_ladder=False,
        target_place_fallback_zero=True,
        imputed=False,
        fallback_kind=None,
        decision_tier=KeywordV3DecisionTier.NO_CONV,
    )


@pytest.mark.unit
def test_gap_enable_requires_fact_below_90pct_resolve() -> None:
    prepared = [(_ctx(ks_id=1), KeywordStrategyMode.OFF)]
    elig = {1: _no_data_elig()}
    resolve = 100.0

    below = plan_pay_for_order_gap_enable(
        prepared,
        eligibility_by_ks_id=elig,
        fact_pay_for_order=89.0,
        resolve=resolve,
        plan_fact_changed=True,
        views_changed=True,
    )
    assert len(below) == 1
    assert below[0].action == V3ActionType.UP

    at_floor = plan_pay_for_order_gap_enable(
        prepared,
        eligibility_by_ks_id=elig,
        fact_pay_for_order=90.0,
        resolve=resolve,
        plan_fact_changed=True,
        views_changed=True,
    )
    assert at_floor == []

    above = plan_pay_for_order_gap_enable(
        prepared,
        eligibility_by_ks_id=elig,
        fact_pay_for_order=120.0,
        resolve=resolve,
        plan_fact_changed=True,
        views_changed=True,
    )
    assert above == []


@pytest.mark.unit
def test_gap_enable_or_gate_plan_or_views() -> None:
    prepared = [(_ctx(ks_id=3), KeywordStrategyMode.OFF)]
    elig = {3: _no_data_elig()}
    kwargs = dict(
        prepared=prepared,
        eligibility_by_ks_id=elig,
        fact_pay_for_order=50.0,
        resolve=100.0,
    )

    assert len(plan_pay_for_order_gap_enable(**kwargs, plan_fact_changed=True, views_changed=False)) == 1
    assert len(plan_pay_for_order_gap_enable(**kwargs, plan_fact_changed=False, views_changed=True)) == 1
    assert plan_pay_for_order_gap_enable(**kwargs, plan_fact_changed=False, views_changed=False) == []


@pytest.mark.unit
def test_gap_enable_skips_when_fact_missing() -> None:
    prepared = [(_ctx(ks_id=2), KeywordStrategyMode.OFF)]
    elig = {2: _no_data_elig()}
    assert (
        plan_pay_for_order_gap_enable(
            prepared,
            eligibility_by_ks_id=elig,
            fact_pay_for_order=None,
            resolve=100.0,
            plan_fact_changed=True,
            views_changed=True,
        )
        == []
    )
