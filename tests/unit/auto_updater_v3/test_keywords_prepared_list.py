"""Unit: KeywordsPreparedList, UpdateContext и ladder states."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_mode import (
    KeywordMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    AdvState,
    KeywordsPreparedList,
    NextState,
    V3LadderStageKind,
    build_keywords_prepared_list,
    build_ladder_states_for_context,
    build_update_context,
    update_context_from_prepared,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto._prepared_builder import (
    assemble_update_context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.ledger_sync import (
    sync_update_context_to_ledger,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger import (
    V3TickKeywordLedger,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    PreparedList,
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.ladder_state_pick import (
    pick_effective_down_ladder_state,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.states_list_generator import (
    StatesListGenerator,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _ctx(
    ks_id: int,
    *,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
    no_data: bool = False,
    profile: list | None = None,
) -> KeywordV3Context:
    views = 0 if no_data else 50
    orders = 0 if no_data else 2
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=2,
        views=views,
        conv=0.05 if not no_data else 0.0,
    )
    if no_data:
        stat = kw.cluster_stat.model_copy(update={"orders": orders, "views": views})
        kw = kw.model_copy(update={"cluster_stat": stat})
    return KeywordV3Context(keyword=kw, position_profile=profile)


@pytest.mark.unit
def test_prepared_list_is_legacy_mutable_list_alias() -> None:
    """``PreparedList`` — legacy ``list[tuple[...]]``; канонический контейнер — ``KeywordsPreparedList``."""
    prepared = build_prepared_from_contexts([_ctx(1)])
    assert isinstance(prepared, KeywordsPreparedList)
    legacy: PreparedList = [(prepared.rows[0].context, prepared.rows[0].active_mode)]
    assert isinstance(legacy, list)


@pytest.mark.unit
def test_build_prepared_row_has_stored_and_active_equal() -> None:
    prepared = build_prepared_from_contexts([_ctx(1)])
    row = prepared.rows[0]
    assert row.stored_mode == row.active_mode == KeywordStrategyMode.MIN_CPA
    assert row.keyword_setting_id == 1
    assert len(row.states) >= 1


@pytest.mark.unit
def test_legacy_iteration_yields_context_and_current_mode() -> None:
    prepared = build_keywords_prepared_list([_ctx(1)])
    ctx, mode = next(iter(prepared))
    assert isinstance(ctx, KeywordV3Context)
    assert mode == KeywordStrategyMode.MIN_CPA
    assert prepared[0][1] == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_next_state_on_dto_updates_current_mode() -> None:
    prepared = build_keywords_prepared_list([_ctx(1)])
    dto = prepared.keywords[0]
    dto.current_mode = NextState(
        new_mode=KeywordMode.OPTIMUM,
        executor_name="Test",
    )
    assert dto.current_mode == KeywordStrategyMode.OPTIMUM
    assert dto.stored_mode == KeywordStrategyMode.MIN_CPA
    assert prepared.rows[0].active_mode == KeywordStrategyMode.OPTIMUM


@pytest.mark.unit
def test_gap_state_when_no_pfo_and_no_profile() -> None:
    ctx = _ctx(2, no_data=True, profile=None)
    states = build_ladder_states_for_context(ctx)
    stages = {s.stage for s in states}
    assert V3LadderStageKind.GAP in stages
    assert V3LadderStageKind.OFF in stages
    gap = next(s for s in states if s.stage == V3LadderStageKind.GAP)
    assert gap.target_position == 0
    assert gap.cpo is None


@pytest.mark.unit
def test_gap_state_when_no_pfo_even_with_ch_profile() -> None:
    """NO DATA с CH-профилем остаётся GAP: без PFO ключ нельзя вести как FULL."""
    ctx = _ctx(22, no_data=True, profile=[PositionProfilePoint(position=1, bid=100)])
    states = build_ladder_states_for_context(ctx)
    stages = {s.stage for s in states}
    assert stages == {V3LadderStageKind.OFF, V3LadderStageKind.GAP}


@pytest.mark.unit
def test_iter_all_ladder_states_flattens() -> None:
    prepared = build_keywords_prepared_list([_ctx(1), _ctx(2)])
    flat = list(prepared.iter_all_ladder_states())
    assert len(flat) >= 2


@pytest.mark.unit
def test_build_update_context_keywords() -> None:
    ctx = build_update_context([_ctx(1)])
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.MIN_CPA
    assert ctx.keywords[0].next_state == []


@pytest.mark.unit
def test_update_context_from_prepared_preserves_next_state() -> None:
    prepared = build_keywords_prepared_list([_ctx(1)])
    prepared.keywords[0].current_mode = NextState(
        new_mode=KeywordMode.MAX_CONVERSION,
        executor_name="Test",
    )
    ctx = update_context_from_prepared(prepared)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.MAX_CONVERSION


@pytest.mark.unit
def test_no_data_gap_is_preserved_with_campaign_fact_for_both_entrypoints() -> None:
    """Campaign fact не подменяет GAP на synthetic MIN_CPA до GAP enable phase."""
    ctx = _ctx(3, mode=KeywordStrategyMode.OFF, no_data=True, profile=None)
    adv_state = replace(AdvState.empty(), fact_pay_for_order=222.0)

    assembled = assemble_update_context([ctx], adv_state=adv_state)
    prepared_ctx = update_context_from_prepared(build_keywords_prepared_list([ctx]), adv_state=adv_state)

    for update_ctx in (assembled, prepared_ctx):
        dto = update_ctx.keywords[0]

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

    ledger = V3TickKeywordLedger.from_keywords([assembled.keywords[0].calculated_keyword])
    assert ledger.baseline_mode_for(assembled.keywords[0].keyword_setting_id) == KeywordStrategyMode.OFF
    assert sync_update_context_to_ledger(assembled, ledger) == []

    ledger = V3TickKeywordLedger.from_keywords([prepared_ctx.keywords[0].calculated_keyword])
    assert ledger.baseline_mode_for(prepared_ctx.keywords[0].keyword_setting_id) == KeywordStrategyMode.OFF
    assert sync_update_context_to_ledger(prepared_ctx, ledger) == []

    gap_ctx = update_context_from_prepared(build_keywords_prepared_list([ctx]))
    gap_dto = gap_ctx.keywords[0]
    assert len(gap_dto.ladder_states) == 2
    assert any(state.is_gap for state in gap_dto.ladder_states)
    assert not any(state.synthetic_no_data for state in gap_dto.ladder_states)
