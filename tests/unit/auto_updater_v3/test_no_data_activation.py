"""Unit: активация ключей без V2 CPO (OFF → MIN_CPA, target_place=0)."""

from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import replace
from unittest.mock import patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    NO_DATA_TARGET_PLACE_FALLBACK,
    keyword_lacks_v3_decision_data,
    keyword_missing_ch_position_profile,
    keyword_v2_pay_for_order_unavailable,
    plan_campaign_no_data_bootstrap_safe,
    plan_data_bootstrap_v3,
    plan_no_ch_min_bootstrap_actions,
    plan_no_data_keyword_actions,
    plan_no_data_min_up_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    AdvState,
    build_update_context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.ladder_state_kind import (
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.states_list_generator import (
    StatesListGenerator,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    pick_effective_down_ladder_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.action_merge import (
    merge_and_dedup_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
    SalesStates,
    detect_campaign_state,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.common_slaves.wildberries.models.fact_methods_enum import (
    FactMethods,
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
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)


def _kw(
    *,
    ks_id: int,
    text: str,
    mode: KeywordStrategyMode,
    hard_status: int = 2,
    conv: float = 0.0,
    cpm_set_bid: int = 200,
) -> CalculatedKeyword:
    stat = make_zero_keyword_stat(text).model_copy(
        update={"conv_views_to_orders": conv, "views": 10, "clicks": 1}
    )
    return CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text=text,
            relevant=True,
            hard_status=hard_status,
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
        cpm_sources=KeywordCpmSources(cpm_set_bid=cpm_set_bid),
    )


def _sample_profile() -> list[PositionProfilePoint]:
    return [
        PositionProfilePoint(
            position=1,
            bid=100,
            predicted_conversion=0.05,
            pay_for_cart=40.0,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    ]


@pytest.mark.unit
def test_detect_campaign_state_no_pay_returns_no_data() -> None:
    plan = PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=300)
    fact = FactData(
        predict_orders=5.0,
        pay_for_order=None,
        original_orders=5,
        fact_method=FactMethods.DIRECT_SALES,
    )
    assert detect_campaign_state(plan, fact) == SalesStates.NO_DATA


@pytest.mark.unit
def test_keyword_v2_pay_for_order_unavailable_when_no_cpm() -> None:
    kw = _kw(ks_id=1, text="a", mode=KeywordStrategyMode.OFF, conv=0.05, cpm_set_bid=0)
    assert keyword_v2_pay_for_order_unavailable(kw)
    assert kw.pay_for_order is None


@pytest.mark.unit
def test_keyword_v2_pay_for_order_available_with_conv_and_cpm() -> None:
    kw = _kw(ks_id=2, text="b", mode=KeywordStrategyMode.MIN_CPA, conv=0.05, cpm_set_bid=200)
    assert not keyword_v2_pay_for_order_unavailable(kw)
    assert kw.pay_for_order is not None


@pytest.mark.unit
def test_keyword_v2_pay_for_order_available_when_only_bid_log_cascade() -> None:
    """Полный каскад CPM (bid_log) даёт pay_for_order — target_place не в fallback 0."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        resolve_keyword_v2_pay_for_order_cost,
    )

    kw = _kw(ks_id=6, text="bid_log_only", mode=KeywordStrategyMode.MIN_CPA, conv=0.05, cpm_set_bid=200)
    sources = kw.cpm_sources
    assert sources is not None
    kw = kw.model_copy(
        update={
            "cpm_sources": sources.model_copy(
                update={
                    "cpm_set_bid": None,
                    "cpm_from_api": None,
                    "cpm_from_stats": None,
                    "cpm_from_bid_log": 3990.0,
                }
            ),
        }
    )
    assert resolve_keyword_v2_pay_for_order_cost(kw) is None
    assert kw.pay_for_order is not None


@pytest.mark.unit
def test_plan_no_data_min_up_off_without_v2_cpo() -> None:
    """INVALID (нет CH, нет conv/V2): OFF → MIN через ``plan_no_data_min_up_actions``."""
    off = _kw(ks_id=1, text="a", mode=KeywordStrategyMode.OFF, conv=0.0, cpm_set_bid=0)
    ctx = KeywordV3Context(keyword=off, position_profile=None)
    assert keyword_lacks_v3_decision_data(ctx, [ctx])
    actions = plan_no_data_min_up_actions([(ctx, KeywordStrategyMode.OFF)])
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert actions[0].reason == "no_data_min_bid"


@pytest.mark.unit
def test_plan_no_data_min_up_off_without_ch_profile_despite_v2_cpo() -> None:
    """NO_CH+own conv — не INVALID; safe bootstrap (CAMPAIGN_NO_DATA) → MIN."""
    off = _kw(ks_id=3, text="c", mode=KeywordStrategyMode.OFF, conv=0.08, cpm_set_bid=200)
    ctx = KeywordV3Context(keyword=off, position_profile=None)
    assert not keyword_lacks_v3_decision_data(ctx, [ctx])
    actions = plan_campaign_no_data_bootstrap_safe([ctx])
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_plan_no_data_down_optimum_without_ch_profile() -> None:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
        plan_campaign_no_data_bootstrap_safe,
    )

    opt = _kw(ks_id=4, text="d", mode=KeywordStrategyMode.OPTIMUM, conv=0.08, cpm_set_bid=200)
    ctx = KeywordV3Context(keyword=opt, position_profile=None)
    actions = plan_campaign_no_data_bootstrap_safe([ctx])
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DOWN
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_keyword_missing_ch_position_profile() -> None:
    assert keyword_missing_ch_position_profile(None)
    assert keyword_missing_ch_position_profile([])


@pytest.mark.unit
def test_plan_no_data_skips_when_v2_cpo_and_ch_profile() -> None:
    off = _kw(ks_id=2, text="b", mode=KeywordStrategyMode.OFF, conv=0.08, cpm_set_bid=200)
    ctx = KeywordV3Context(keyword=off, position_profile=_sample_profile())
    assert not keyword_lacks_v3_decision_data(ctx, [ctx])
    actions = plan_no_data_min_up_actions([(ctx, KeywordStrategyMode.OFF)])
    assert actions == []


@pytest.mark.unit
def test_no_data_with_campaign_fact_stays_gap() -> None:
    """Campaign fact не заменяет ключевой GAP без operational pay_for_order."""
    kw = _kw(ks_id=7, text="nd", mode=KeywordStrategyMode.OFF, conv=0.0, cpm_set_bid=0)
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    adv_state = replace(AdvState.empty(), fact_pay_for_order=123.0)
    dto = build_update_context([ctx], adv_state=adv_state).prepared.keywords[0]

    assert len(dto.ladder_states) == 2
    assert any(state.is_gap for state in dto.ladder_states)
    assert not any(state.synthetic_no_data for state in dto.ladder_states)
    assert dto.stored_mode == KeywordStrategyMode.OFF
    assert dto.current_mode == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_no_data_with_ch_profile_stays_gap_with_campaign_fact() -> None:
    """CH-профиль без PFO не переводит ключ в FULL/MIN singleton."""
    kw = _kw(
        ks_id=10,
        text="nd_fact_priority",
        mode=KeywordStrategyMode.OFF,
        conv=0.0,
        cpm_set_bid=0,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=_sample_profile())
    adv_state = replace(AdvState.empty(), fact_pay_for_order=222.0)
    update_ctx = build_update_context([ctx], adv_state=adv_state)

    dto = update_ctx.prepared.keywords[0]
    assert len(dto.ladder_states) == 2
    assert any(state.is_gap for state in dto.ladder_states)
    assert not any(state.synthetic_no_data for state in dto.ladder_states)
    assert dto.stored_mode == KeywordStrategyMode.OFF
    assert dto.current_mode == KeywordStrategyMode.OFF
    assert not dto.is_no_data_singleton()

    current, potential = StatesListGenerator(update_ctx.adv_state).get_current_states(
        update_ctx.keywords
    )
    assert current == []
    assert potential == []

    down = pick_effective_down_ladder_state(dto)
    assert down is None


@pytest.mark.unit
def test_no_data_gap_stays_out_of_current_and_potential_pools() -> None:
    kw = _kw(ks_id=9, text="nd2", mode=KeywordStrategyMode.OFF, conv=0.0, cpm_set_bid=0)
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    adv_state = replace(AdvState.empty(), fact_pay_for_order=321.0)
    update_ctx = build_update_context([ctx], adv_state=adv_state)
    current, potential = StatesListGenerator(update_ctx.adv_state).get_current_states(
        update_ctx.keywords
    )

    assert current == []
    assert potential == []


@pytest.mark.unit
def test_no_data_without_fact_remains_gap_singleton_or_empty_behavior() -> None:
    kw = _kw(ks_id=8, text="gap", mode=KeywordStrategyMode.OFF, conv=0.0, cpm_set_bid=0)
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    dto = build_update_context([ctx]).prepared.keywords[0]

    assert len(dto.ladder_states) == 2
    assert any(state.is_gap for state in dto.ladder_states)


@pytest.mark.unit
def test_plan_no_data_min_up_only_off_returns_up_not_down() -> None:
    """gap-rebalance: min_up — только UP для OFF, не DOWN для O/C."""
    opt = _kw(ks_id=5, text="e", mode=KeywordStrategyMode.OPTIMUM, conv=0.0)
    ctx_opt = KeywordV3Context(keyword=opt, position_profile=None)
    assert plan_no_data_min_up_actions([(ctx_opt, KeywordStrategyMode.OPTIMUM)]) == []

    off = _kw(ks_id=6, text="f", mode=KeywordStrategyMode.OFF, conv=0.0)
    ctx_off = KeywordV3Context(keyword=off, position_profile=None)
    up_only = plan_no_data_min_up_actions([(ctx_off, KeywordStrategyMode.OFF)])
    assert len(up_only) == 1
    assert up_only[0].action == V3ActionType.UP


@pytest.mark.unit
def test_diagnose_keyword_v3_data_cpo_without_ch_profile() -> None:
    """V2 CPO и CH-матрица независимы: может быть CPO без bid profile."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
        diagnose_keyword_v3_data,
    )

    kw = _kw(ks_id=20, text="x", mode=KeywordStrategyMode.OFF, conv=0.08, cpm_set_bid=200)
    diag = diagnose_keyword_v3_data(kw, None)
    assert diag.has_v2_cpo
    assert not diag.has_ch_position_profile
    assert not diag.n_state
    assert diag.missing_labels_ru() == ("нет матрицы CH (bid profile по ключу)",)


@pytest.mark.unit
def test_diagnose_v2_cpo_gap_no_cpm() -> None:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
        diagnose_v2_cpo_gap,
    )

    kw = _kw(ks_id=21, text="y", mode=KeywordStrategyMode.OFF, conv=0.05, cpm_set_bid=0)
    assert diagnose_v2_cpo_gap(kw) == "нет CPM (каскад ставок ключа)"


@pytest.mark.unit
def test_no_data_target_place_fallback_is_min_bid_sentinel() -> None:
    assert NO_DATA_TARGET_PLACE_FALLBACK == 0


@pytest.mark.unit
def test_merge_and_dedup_preserves_force_off_then_up_in_same_bucket() -> None:
    """N-state: FORCE_OFF+UP для одного ключа не схлопываются в один UP."""
    no_data = plan_no_data_keyword_actions(
        [
            (
                KeywordV3Context(
                    keyword=_kw(
                        ks_id=30,
                        text="auto_min",
                        mode=KeywordStrategyMode.MIN_CPA,
                        hard_status=1,
                        conv=0.0,
                    ),
                    position_profile=None,
                ),
                KeywordStrategyMode.MIN_CPA,
            )
        ]
    )
    assert len(no_data) == 2
    assert no_data[0].action == V3ActionType.FORCE_OFF
    assert no_data[1].action == V3ActionType.UP

    merged = merge_and_dedup_actions(no_data, [], [], [])
    assert len(merged) == 2
    assert {a.action for a in merged} == {V3ActionType.FORCE_OFF, V3ActionType.UP}


@pytest.mark.unit
def test_merge_and_dedup_higher_priority_bucket_wins_across_lists() -> None:
    """Между bucket'ами побеждает cleanup, не смешивая действия разных bucket."""
    m1_up = V3Action(
        action=V3ActionType.UP,
        keyword_setting_id=1,
        target_strategy_mode=KeywordStrategyMode.OPTIMUM,
        reason="m1",
    )
    cleanup_down = V3Action(
        action=V3ActionType.DOWN,
        keyword_setting_id=1,
        target_strategy_mode=KeywordStrategyMode.MIN_CPA,
        reason="cleanup",
    )
    merged = merge_and_dedup_actions([cleanup_down], [m1_up], [], [])
    assert len(merged) == 1
    assert merged[0].action == V3ActionType.DOWN


@pytest.mark.unit
def test_plan_no_ch_min_bootstrap_off_auto_up_to_min() -> None:
    """NO CH + V2 CPO + OFF + auto → UP MIN (без gate resolve)."""
    off = _kw(
        ks_id=90,
        text="крем для лица с блеском",
        mode=KeywordStrategyMode.OFF,
        hard_status=1,
        conv=0.08,
        cpm_set_bid=510,
    )
    ctx = KeywordV3Context(keyword=off, position_profile=None)
    prepared = [(ctx, KeywordStrategyMode.OFF)]
    actions = plan_no_ch_min_bootstrap_actions(prepared)
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.UP
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert actions[0].reason == "no_ch_min_bootstrap"


@pytest.mark.unit
def test_plan_no_ch_min_bootstrap_skips_up_when_pay_for_order_above_max() -> None:
    """NO CH: ``pay_for_order`` из ключа > max — без UP MIN."""
    off = _kw(
        ks_id=93,
        text="дорогой no ch",
        mode=KeywordStrategyMode.OFF,
        hard_status=2,
        conv=0.08,
        cpm_set_bid=510,
    )
    ctx = KeywordV3Context(keyword=off, position_profile=None)
    prepared = [(ctx, KeywordStrategyMode.OFF)]
    pfo = off.pay_for_order
    assert pfo is not None and pfo > 1.0
    actions = plan_no_ch_min_bootstrap_actions(
        prepared, max_pay_for_order=float(pfo) - 1.0
    )
    assert actions == []


@pytest.mark.unit
def test_plan_data_bootstrap_auto_uses_eligibility_cap() -> None:
    """Auto-mode bootstrap: UP после FORCE_OFF на вычисленный cap, не всегда MIN_CPA."""
    kw = _kw(
        ks_id=92,
        text="cap_test",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        hard_status=1,
        conv=0.08,
        cpm_set_bid=200,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=_sample_profile())
    elig_patch = (
        "app.modules.shop_runner.service_manager.services.auto_updater_v3"
        ".keyword_v3_eligibility"
    )
    with (
        patch(f"{elig_patch}.clamp_target_mode", return_value=KeywordStrategyMode.OPTIMUM),
        patch(f"{elig_patch}.can_target_mode", return_value=True),
    ):
        actions = plan_data_bootstrap_v3([ctx])

    bootstrap = [a for a in actions if a.reason == "data_bootstrap_down"]
    assert any(a.action == V3ActionType.FORCE_OFF for a in bootstrap)
    up = [a for a in bootstrap if a.action == V3ActionType.UP]
    assert len(up) == 1
    assert up[0].target_strategy_mode == KeywordStrategyMode.OPTIMUM


def test_plan_data_bootstrap_does_not_include_no_ch_off_to_min() -> None:
    """plan_data_bootstrap_v3 не поднимает NO_CH OFF→MIN (только safe-start helper)."""
    off = _kw(
        ks_id=91,
        text="no_ch",
        mode=KeywordStrategyMode.OFF,
        hard_status=1,
        conv=0.08,
        cpm_set_bid=510,
    )
    ctx = KeywordV3Context(keyword=off, position_profile=None)
    prepared = build_prepared_from_contexts([ctx])
    bootstrap_actions = plan_data_bootstrap_v3([ctx])
    assert not any(a.reason == "no_ch_min_bootstrap" for a in bootstrap_actions)
    safe_start = plan_no_ch_min_bootstrap_actions(prepared, max_pay_for_order=10_000.0)
    assert any(a.reason == "no_ch_min_bootstrap" for a in safe_start)
