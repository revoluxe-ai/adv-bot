"""Phase-level: released_steps в plan_cost_reallocation / plan_state_rebalance."""

from __future__ import annotations

import logging

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    count_effective_released_aggression_steps as _count_released_orig,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    _StateView,
    plan_cost_reallocation,
    plan_max_cpa_guard,
    plan_state_rebalance,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    build_prepared_from_contexts,
)
from tests.unit.auto_updater_v3.test_effective_ladder_steps import _fake_catalog_places
from tests.unit.auto_updater_v3.test_effective_phases_acceptance import _o_eq_m_profile
from tests.unit.test_auto_updater_v3 import _calc_kw

_REALLOC_LOGGER = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner"
)


def _policy() -> SelectionPolicy:
    return SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )


def _patch_catalog(monkeypatch: pytest.MonkeyPatch, cat: dict) -> None:
    monkeypatch.setattr(
        f"{_REALLOC_LOGGER}._mode_catalog_for_ctx",
        lambda _ctx, _prepared, _ladder=None: cat,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking._catalog_for_ctx",
        lambda _ctx, _prepared=None, **_kwargs: cat,
    )


def _track_released_in_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[KeywordStrategyMode, KeywordStrategyMode | None, int]]:
    """Записывает каждый вызов count_* из фазы (не подменяет логику подсчёта)."""
    recorded: list[tuple[KeywordStrategyMode, KeywordStrategyMode | None, int]] = []

    def _wrapped(
        from_mode: KeywordStrategyMode,
        to_mode: KeywordStrategyMode | None,
        catalog: dict,
    ) -> int:
        n = _count_released_orig(from_mode, to_mode, catalog)
        recorded.append((from_mode, to_mode, n))
        return n

    monkeypatch.setattr(f"{_REALLOC_LOGGER}.count_effective_released_aggression_steps", _wrapped)
    return recorded


def _install_realloc_collectors(
    monkeypatch: pytest.MonkeyPatch,
    *,
    active_ks: int,
    active_mode: KeywordStrategyMode,
    active_cost: float,
    potential_ks: int = 31,
) -> None:
    def _active(_prepared: object, **kwargs: object) -> list[_StateView]:
        overrides: dict[int, KeywordStrategyMode] = kwargs.get("overrides") or {}
        if overrides.get(active_ks) is not None:
            return []
        return [
            _StateView(
                ks_id=active_ks,
                strategy_mode=active_mode,
                cost=active_cost,
                from_mode=active_mode,
                to_mode=active_mode,
                imputed=False,
            )
        ]

    def _potential(_prepared: object, **_kwargs: object) -> list[_StateView]:
        return [
            _StateView(
                ks_id=potential_ks,
                strategy_mode=KeywordStrategyMode.MIN_CPA,
                cost=50.0,
                from_mode=KeywordStrategyMode.OFF,
                to_mode=KeywordStrategyMode.MIN_CPA,
                imputed=False,
            )
        ]

    monkeypatch.setattr(
        f"{_REALLOC_LOGGER}._collect_active_more_expensive_than",
        _active,
    )
    monkeypatch.setattr(
        f"{_REALLOC_LOGGER}.collect_potential_passing_states",
        _potential,
    )


def _install_m2_collectors(
    monkeypatch: pytest.MonkeyPatch,
    *,
    active_ks: int,
    active_mode: KeywordStrategyMode,
    active_cost: float,
    potential_ks: int = 31,
    potential_to: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
) -> None:
    def _active(_prepared: object, **kwargs: object) -> list[_StateView]:
        overrides: dict[int, KeywordStrategyMode] = kwargs.get("overrides") or {}
        if overrides.get(active_ks) is not None:
            return []
        return [
            _StateView(
                ks_id=active_ks,
                strategy_mode=active_mode,
                cost=active_cost,
                from_mode=active_mode,
                to_mode=active_mode,
                imputed=False,
            )
        ]

    def _potential(_prepared: object, **_kwargs: object) -> list[_StateView]:
        return [
            _StateView(
                ks_id=potential_ks,
                strategy_mode=potential_to,
                cost=50.0,
                from_mode=KeywordStrategyMode.OFF,
                to_mode=potential_to,
                imputed=False,
            )
        ]

    monkeypatch.setattr(f"{_REALLOC_LOGGER}._collect_active_expensive", _active)
    monkeypatch.setattr(f"{_REALLOC_LOGGER}._collect_potential_expensive", _potential)


def _phase_released_total(
    recorded: list[tuple[KeywordStrategyMode, KeywordStrategyMode | None, int]],
) -> int:
    return sum(n for _f, _t, n in recorded)


@pytest.mark.unit
def test_cost_realloc_max_to_min_phase_released_steps_one(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """COST_REALLOCATION: MAX=OPT place → effective DOWN в MIN; released_steps=1."""
    cat = _fake_catalog_places(min_place=40, opt_place=1, max_place=1)
    _patch_catalog(monkeypatch, cat)
    recorded = _track_released_in_planner(monkeypatch)
    _install_realloc_collectors(
        monkeypatch,
        active_ks=10,
        active_mode=KeywordStrategyMode.MAX_CONVERSION,
        active_cost=500.0,
    )
    prof = _o_eq_m_profile()
    max_kw = _calc_kw(
        ks_id=10,
        text="realloc_max",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=50.0,
        conv=0.05,
        hard_status=2,
    )
    cheap = _calc_kw(
        ks_id=31,
        text="cheap",
        mode=KeywordStrategyMode.OFF,
        rating=0.1,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=max_kw, position_profile=prof),
            KeywordV3Context(keyword=cheap, position_profile=prof),
        ]
    )
    ladder = LadderInputs.from_contexts([c for c, _ in prepared])

    with caplog.at_level(logging.DEBUG, logger=_REALLOC_LOGGER):
        actions = plan_cost_reallocation(
            prepared,
            resolve=200.0,
            policy=_policy(),
            ladder_inputs=ladder,
        )

    assert _phase_released_total(recorded) == 1
    assert len(recorded) == 1
    assert recorded[0][0] == KeywordStrategyMode.MAX_CONVERSION
    assert recorded[0][1] == KeywordStrategyMode.MIN_CPA
    assert recorded[0][2] == 1
    assert "v3 cost_reallocation released_steps=1" in caplog.text
    assert "released_steps=2" not in caplog.text

    downs = [a for a in actions if a.keyword_setting_id == 10]
    assert len(downs) == 1
    assert downs[0].action == V3ActionType.DOWN
    assert downs[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_cost_realloc_m_o_c_off_phase_released_steps_one(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """COST_REALLOCATION: M=O=C → MAX effective OFF; released_steps=1 (не 2)."""
    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    _patch_catalog(monkeypatch, cat)
    recorded = _track_released_in_planner(monkeypatch)
    _install_realloc_collectors(
        monkeypatch,
        active_ks=30,
        active_mode=KeywordStrategyMode.MAX_CONVERSION,
        active_cost=500.0,
    )
    prof = _o_eq_m_profile()
    max_kw = _calc_kw(
        ks_id=30,
        text="max_degen",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=50.0,
        conv=0.05,
        hard_status=2,
    )
    cheap = _calc_kw(
        ks_id=31,
        text="cheap",
        mode=KeywordStrategyMode.OFF,
        rating=0.1,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=max_kw, position_profile=prof),
            KeywordV3Context(keyword=cheap, position_profile=prof),
        ]
    )
    ladder = LadderInputs.from_contexts([c for c, _ in prepared])

    with caplog.at_level(logging.DEBUG, logger=_REALLOC_LOGGER):
        plan_cost_reallocation(
            prepared,
            resolve=200.0,
            policy=_policy(),
            ladder_inputs=ladder,
        )

    assert _phase_released_total(recorded) == 1
    assert len(recorded) == 1
    assert recorded[0][1] == KeywordStrategyMode.OFF
    assert "v3 cost_reallocation released_steps=1" in caplog.text
    assert "released_steps=2" not in caplog.text


@pytest.mark.unit
def test_cost_realloc_m_o_c_hollow_phase_released_steps_zero(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """COST_REALLOCATION: hollow effective DOWN (alias place) — released_steps=0."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
        EffectiveStepResult,
        resolve_next_effective_step_down as _resolve_down_orig,
    )

    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    _patch_catalog(monkeypatch, cat)

    def _hollow_opt_to_min(
        current: KeywordStrategyMode, catalog: dict
    ) -> EffectiveStepResult:
        if current == KeywordStrategyMode.OPTIMUM:
            return EffectiveStepResult(
                KeywordStrategyMode.MIN_CPA,
                ("skipped_mode_alias: OPT equals MIN",),
            )
        return _resolve_down_orig(current, catalog)

    monkeypatch.setattr(
        f"{_REALLOC_LOGGER}.resolve_next_effective_step_down",
        _hollow_opt_to_min,
    )
    recorded = _track_released_in_planner(monkeypatch)
    _install_realloc_collectors(
        monkeypatch,
        active_ks=32,
        active_mode=KeywordStrategyMode.OPTIMUM,
        active_cost=500.0,
    )
    prof = _o_eq_m_profile()
    opt_kw = _calc_kw(
        ks_id=32,
        text="opt_degen",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=50.0,
        conv=0.05,
        hard_status=2,
    )
    cheap = _calc_kw(
        ks_id=33,
        text="cheap2",
        mode=KeywordStrategyMode.OFF,
        rating=0.1,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=opt_kw, position_profile=prof),
            KeywordV3Context(keyword=cheap, position_profile=prof),
        ]
    )
    ladder = LadderInputs.from_contexts([c for c, _ in prepared])

    with caplog.at_level(logging.DEBUG, logger=_REALLOC_LOGGER):
        actions = plan_cost_reallocation(
            prepared,
            resolve=200.0,
            policy=_policy(),
            ladder_inputs=ladder,
        )

    assert _phase_released_total(recorded) == 0
    assert recorded == [(KeywordStrategyMode.OPTIMUM, KeywordStrategyMode.MIN_CPA, 0)]
    assert "cost_reallocation released_steps=" not in caplog.text
    assert not [a for a in actions if a.keyword_setting_id == 32]


@pytest.mark.unit
def test_state_rebalance_max_to_min_phase_released_steps_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """plan_state_rebalance: MAX→MIN effective; budget (released_steps) = 1."""
    cat = _fake_catalog_places(min_place=40, opt_place=1, max_place=1)
    _patch_catalog(monkeypatch, cat)
    recorded = _track_released_in_planner(monkeypatch)
    _install_m2_collectors(
        monkeypatch,
        active_ks=20,
        active_mode=KeywordStrategyMode.MAX_CONVERSION,
        active_cost=500.0,
    )
    prof = _o_eq_m_profile()
    max_kw = _calc_kw(
        ks_id=20,
        text="m2_max",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=50.0,
        conv=0.05,
        hard_status=2,
    )
    cheap = _calc_kw(
        ks_id=21,
        text="m2_cheap",
        mode=KeywordStrategyMode.OFF,
        rating=0.1,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=max_kw, position_profile=prof),
            KeywordV3Context(keyword=cheap, position_profile=prof),
        ]
    )
    ladder = LadderInputs.from_contexts([c for c, _ in prepared])
    actions = plan_state_rebalance(
        prepared,
        resolve=200.0,
        policy=_policy(),
        ladder_inputs=ladder,
    )

    assert _phase_released_total(recorded) == 1
    assert recorded[0][0] == KeywordStrategyMode.MAX_CONVERSION
    assert recorded[0][1] == KeywordStrategyMode.MIN_CPA
    downs = [a for a in actions if a.keyword_setting_id == 20 and a.action == V3ActionType.DOWN]
    assert len(downs) == 1
    assert downs[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert len([a for a in actions if a.action == V3ActionType.UP]) == 1


@pytest.mark.unit
def test_state_rebalance_m_o_c_off_phase_released_steps_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """plan_state_rebalance: M=O=C MAX→OFF; released_steps=1."""
    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    _patch_catalog(monkeypatch, cat)
    recorded = _track_released_in_planner(monkeypatch)
    _install_m2_collectors(
        monkeypatch,
        active_ks=25,
        active_mode=KeywordStrategyMode.MAX_CONVERSION,
        active_cost=500.0,
    )
    prof = _o_eq_m_profile()
    max_kw = _calc_kw(
        ks_id=25,
        text="m2_max_off",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=50.0,
        conv=0.05,
        hard_status=2,
    )
    cheap = _calc_kw(
        ks_id=26,
        text="m2_cheap2",
        mode=KeywordStrategyMode.OFF,
        rating=0.1,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=max_kw, position_profile=prof),
            KeywordV3Context(keyword=cheap, position_profile=prof),
        ]
    )
    ladder = LadderInputs.from_contexts([c for c, _ in prepared])
    actions = plan_state_rebalance(
        prepared,
        resolve=200.0,
        policy=_policy(),
        ladder_inputs=ladder,
    )

    assert _phase_released_total(recorded) == 1
    assert recorded[0][1] == KeywordStrategyMode.OFF
    assert any(
        a.keyword_setting_id == 25 and a.action == V3ActionType.FORCE_OFF for a in actions
    )


@pytest.mark.unit
def test_state_rebalance_m_o_c_hollow_phase_released_steps_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """plan_state_rebalance: hollow effective DOWN — released_steps=0."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
        EffectiveStepResult,
        resolve_next_effective_step_down as _resolve_down_orig,
    )

    cat = _fake_catalog_places(min_place=1, opt_place=1, max_place=1)
    _patch_catalog(monkeypatch, cat)

    def _hollow_opt_to_min(
        current: KeywordStrategyMode, catalog: dict
    ) -> EffectiveStepResult:
        if current == KeywordStrategyMode.OPTIMUM:
            return EffectiveStepResult(
                KeywordStrategyMode.MIN_CPA,
                ("skipped_mode_alias: OPT equals MIN",),
            )
        return _resolve_down_orig(current, catalog)

    monkeypatch.setattr(
        f"{_REALLOC_LOGGER}.resolve_next_effective_step_down",
        _hollow_opt_to_min,
    )
    recorded = _track_released_in_planner(monkeypatch)
    _install_m2_collectors(
        monkeypatch,
        active_ks=27,
        active_mode=KeywordStrategyMode.OPTIMUM,
        active_cost=500.0,
    )
    prof = _o_eq_m_profile()
    opt_kw = _calc_kw(
        ks_id=27,
        text="m2_opt",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=50.0,
        conv=0.05,
        hard_status=2,
    )
    cheap = _calc_kw(
        ks_id=28,
        text="m2_cheap3",
        mode=KeywordStrategyMode.OFF,
        rating=0.1,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [
            KeywordV3Context(keyword=opt_kw, position_profile=prof),
            KeywordV3Context(keyword=cheap, position_profile=prof),
        ]
    )
    ladder = LadderInputs.from_contexts([c for c, _ in prepared])
    actions = plan_state_rebalance(
        prepared,
        resolve=200.0,
        policy=_policy(),
        ladder_inputs=ladder,
    )

    assert _phase_released_total(recorded) == 0
    assert not [a for a in actions if a.keyword_setting_id == 27]


@pytest.mark.unit
def test_max_cpa_guard_no_action_when_effective_target_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MAX_CPA_GUARD: trim не меняет target_place и OFF не нужен → actions == []."""
    cat = _fake_catalog_places(min_place=40, opt_place=40, max_place=1)
    _patch_catalog(monkeypatch, cat)
    prof = _o_eq_m_profile()
    opt_kw = _calc_kw(
        ks_id=80,
        text="guard_opt_ok",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=10.0,
        conv=0.05,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=opt_kw, position_profile=prof)]
    )
    actions = plan_max_cpa_guard(
        prepared,
        max_pay_for_order=1_000_000.0,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )
    assert actions == []
