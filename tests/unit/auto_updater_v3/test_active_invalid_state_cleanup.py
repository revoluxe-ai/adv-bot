"""Unit: ``plan_active_invalid_state_cleanup`` — сброс active MIN/OPT/MAX при invalid/worst."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderCostSource,
    LadderInputs,
    LadderStageResult,
    LadderView,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    resolve_keyword_v3_eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_active_invalid_state_cleanup,
    plan_max_cpa_guard,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.test_auto_updater_v3 import _calc_kw, _conv_for_pay_for_order

KS_ID = 501
MAX_PFO = 400.0
RESOLVE = 350.0
RK = 0.2


def _mc(
    mode: AggressionTargetMode,
    *,
    place: int | None,
    cpa: float | None,
    valid: bool,
) -> ModeCandidate:
    return ModeCandidate(
        mode=mode,
        position=place,
        bid=500.0 if place == 1 else 510.0,
        predicted_cpa=cpa,
        is_valid=valid,
        invalid_reason=None if valid else "no_rk_conv_carts_to_orders",
    )


def _catalog_max_invalid_min_valid() -> dict[AggressionTargetMode, ModeCandidate]:
    return {
        AggressionTargetMode.MIN_CPA: _mc(
            AggressionTargetMode.MIN_CPA, place=22, cpa=300.0, valid=True
        ),
        AggressionTargetMode.OPTIMUM: _mc(
            AggressionTargetMode.OPTIMUM, place=None, cpa=None, valid=False
        ),
        AggressionTargetMode.MAX_CONVERSION: _mc(
            AggressionTargetMode.MAX_CONVERSION, place=None, cpa=None, valid=False
        ),
    }


def _profile_two_places() -> list[PositionProfilePoint]:
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        PositionProfilePoint(
            position=1,
            bid=14_555.0,
            predicted_conversion=0.13,
            pay_for_cart=1.0,
            timestamp=ts,
            ch_observed=True,
        ),
        PositionProfilePoint(
            position=22,
            bid=510.0,
            predicted_conversion=0.02,
            pay_for_cart=1.0,
            timestamp=ts,
            ch_observed=True,
        ),
    ]


def _ctx_max_wl(*, target_place: int = 1) -> KeywordV3Context:
    kw = _calc_kw(
        ks_id=KS_ID,
        text="антивозрастной крем для лица 60 плюс",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=10.0,
        conv=0.02,
        hard_status=2,
    )
    kw = kw.model_copy(
        update={
            "keyword_setting": kw.keyword_setting.model_copy(
                update={"target_place": target_place}
            )
        }
    )
    return KeywordV3Context(keyword=kw, position_profile=_profile_two_places())


def _catalog_all_invalid() -> dict[AggressionTargetMode, ModeCandidate]:
    """Все CH-кандидаты invalid — симулирует отсутствие пригодной CH-матрицы."""
    return {
        AggressionTargetMode.MIN_CPA: _mc(
            AggressionTargetMode.MIN_CPA, place=None, cpa=None, valid=False
        ),
        AggressionTargetMode.OPTIMUM: _mc(
            AggressionTargetMode.OPTIMUM, place=None, cpa=None, valid=False
        ),
        AggressionTargetMode.MAX_CONVERSION: _mc(
            AggressionTargetMode.MAX_CONVERSION, place=None, cpa=None, valid=False
        ),
    }


def _synthetic_only_profile() -> list[PositionProfilePoint]:
    """CH raw без usable точек (только синтетика)."""
    return [
        PositionProfilePoint(
            position=1,
            bid=1000,
            predicted_conversion=0.1,
            pay_for_cart=100.0,
            ch_observed=False,
        ),
    ]


def _ctx_collapsed_ch_active(
    *,
    mode: KeywordStrategyMode,
    pay_for_order_target: float = 49.0,
    hard_status: int = 2,
) -> KeywordV3Context:
    """Collapsed CH + pay_for_order: stored MIN_CPA, operational cost из PFO."""
    kw = _calc_kw(
        ks_id=KS_ID,
        text="collapsed_ch_pfo",
        mode=mode,
        rating=10.0,
        conv=_conv_for_pay_for_order(pay_for_order_target),
        hard_status=hard_status,
    )
    return KeywordV3Context(keyword=kw, position_profile=_synthetic_only_profile())


def _ctx_no_ch_active(
    *,
    mode: KeywordStrategyMode,
    pay_for_order_target: float = 49.0,
    hard_status: int = 2,
) -> KeywordV3Context:
    """NO_CH tier: ``position_profile=None``, operational MIN через pay_for_order."""
    kw = _calc_kw(
        ks_id=KS_ID,
        text="no_ch_own_conv",
        mode=mode,
        rating=10.0,
        conv=_conv_for_pay_for_order(pay_for_order_target),
        hard_status=hard_status,
    )
    return KeywordV3Context(keyword=kw, position_profile=None)


def _patch_catalog(monkeypatch: pytest.MonkeyPatch, cat: dict) -> None:
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._mode_catalog_for_ctx",
        lambda _ctx, _prepared, _ladder=None: cat,
    )


def _patch_cost_for_mode(
    monkeypatch: pytest.MonkeyPatch,
    costs: dict[KeywordStrategyMode, tuple[float, bool]],
) -> None:
    """Подмена ``cost_for_mode`` (импорт внутри planner из ``keyword_v3_ladder_view``)."""

    def _fake(
        ctx: KeywordV3Context,
        to_mode: KeywordStrategyMode,
        *,
        ladder_inputs: LadderInputs,
        eligibility: object = None,
    ) -> tuple[float, bool]:
        _ = ctx, ladder_inputs, eligibility
        return costs.get(to_mode, (float("inf"), False))

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view.cost_for_mode",
        _fake,
    )


def _patch_ladder_view_for_invalid_max(
    monkeypatch: pytest.MonkeyPatch,
    *,
    min_source: LadderCostSource = LadderCostSource.PROFILE,
    max_source: LadderCostSource = LadderCostSource.WORST,
    max_cost: float = 242_360.0,
    min_cost: float = 300.0,
) -> None:
    cat = _catalog_max_invalid_min_valid()

    def _fake_view(
        ctx: KeywordV3Context,
        ladder_inputs: LadderInputs,
        *,
        eligibility: object = None,
    ) -> LadderView:
        _ = ctx, ladder_inputs, eligibility

        def _stage(
            mode: AggressionTargetMode,
            source: LadderCostSource,
            cost: float | None,
            valid: bool,
        ) -> LadderStageResult:
            c = cat[mode]
            return LadderStageResult(
                mode=mode,
                is_valid=valid,
                cost=cost,
                source=source,
                candidate=c,
            )

        return LadderView(
            stages={
                AggressionTargetMode.MIN_CPA: _stage(
                    AggressionTargetMode.MIN_CPA, min_source, min_cost, True
                ),
                AggressionTargetMode.OPTIMUM: _stage(
                    AggressionTargetMode.OPTIMUM, LadderCostSource.NONE, None, False
                ),
                AggressionTargetMode.MAX_CONVERSION: _stage(
                    AggressionTargetMode.MAX_CONVERSION,
                    max_source,
                    max_cost,
                    max_source == LadderCostSource.WORST,
                ),
            }
        )

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view.resolve_ladder_stage_display",
        _fake_view,
    )


@pytest.mark.unit
def test_no_ch_min_active_invalid_catalog_no_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NO_CH MIN + pay_for_order <= max: missing CH candidate не даёт cleanup."""
    _patch_catalog(monkeypatch, _catalog_all_invalid())
    ctx = _ctx_no_ch_active(mode=KeywordStrategyMode.MIN_CPA, pay_for_order_target=49.0)
    contexts = [ctx]
    prepared = build_prepared_from_contexts(contexts)
    ladder = LadderInputs.from_contexts(contexts, rk_orders_per_cart=RK)
    elig = resolve_keyword_v3_eligibility(ctx, contexts)
    assert elig.data_tier == KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV

    actions = plan_active_invalid_state_cleanup(
        prepared,
        max_pay_for_order=MAX_PFO,
        resolve=RESOLVE,
        ladder_inputs=ladder,
        eligibility_by_ks_id={KS_ID: elig},
    )
    assert actions == []


@pytest.mark.unit
def test_no_ch_opt_active_down_to_min_not_force_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NO_CH OPT без CH: DOWN MIN при pay_for_order <= max, не FORCE_OFF."""
    _patch_catalog(monkeypatch, _catalog_all_invalid())
    ctx = _ctx_no_ch_active(mode=KeywordStrategyMode.OPTIMUM, pay_for_order_target=49.0)
    contexts = [ctx]
    prepared = build_prepared_from_contexts(contexts)
    ladder = LadderInputs.from_contexts(contexts, rk_orders_per_cart=RK)
    elig = resolve_keyword_v3_eligibility(ctx, contexts)
    assert elig.data_tier == KeywordDataTier.KEYWORD_NO_CH_PROFILE_WITH_OWN_CONV

    actions = plan_active_invalid_state_cleanup(
        prepared,
        max_pay_for_order=MAX_PFO,
        resolve=RESOLVE,
        ladder_inputs=ladder,
        eligibility_by_ks_id={KS_ID: elig},
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DOWN
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert actions[0].reason == "active_invalid_state_down"


@pytest.mark.unit
def test_collapsed_ch_opt_active_down_to_min(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Collapsed CH + PFO: active OPT → DOWN MIN (не worst cost)."""
    _patch_catalog(monkeypatch, _catalog_all_invalid())
    ctx = _ctx_collapsed_ch_active(
        mode=KeywordStrategyMode.OPTIMUM, pay_for_order_target=49.0
    )
    contexts = [ctx]
    prepared = build_prepared_from_contexts(contexts)
    ladder = LadderInputs.from_contexts(contexts, rk_orders_per_cart=RK)
    elig = resolve_keyword_v3_eligibility(ctx, contexts)
    assert elig.data_tier == KeywordDataTier.KEYWORD_FULL
    assert elig.target_place_fallback_zero is True

    actions = plan_active_invalid_state_cleanup(
        prepared,
        max_pay_for_order=MAX_PFO,
        resolve=RESOLVE,
        ladder_inputs=ladder,
        eligibility_by_ks_id={KS_ID: elig},
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DOWN
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_no_ch_max_active_down_to_min(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NO_CH MAX без CH → DOWN MIN (аналог OPT)."""
    _patch_catalog(monkeypatch, _catalog_all_invalid())
    ctx = _ctx_no_ch_active(
        mode=KeywordStrategyMode.MAX_CONVERSION, pay_for_order_target=80.0
    )
    contexts = [ctx]
    prepared = build_prepared_from_contexts(contexts)
    ladder = LadderInputs.from_contexts(contexts, rk_orders_per_cart=RK)
    elig = resolve_keyword_v3_eligibility(ctx, contexts)

    actions = plan_active_invalid_state_cleanup(
        prepared,
        max_pay_for_order=MAX_PFO,
        resolve=RESOLVE,
        ladder_inputs=ladder,
        eligibility_by_ks_id={KS_ID: elig},
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DOWN
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_no_ch_min_above_max_force_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NO_CH MIN с pay_for_order > max → FORCE_OFF (нет valid lower)."""
    _patch_catalog(monkeypatch, _catalog_all_invalid())
    ctx = _ctx_no_ch_active(
        mode=KeywordStrategyMode.MIN_CPA, pay_for_order_target=500.0
    )
    contexts = [ctx]
    prepared = build_prepared_from_contexts(contexts)
    ladder = LadderInputs.from_contexts(contexts, rk_orders_per_cart=RK)

    actions = plan_active_invalid_state_cleanup(
        prepared,
        max_pay_for_order=MAX_PFO,
        resolve=RESOLVE,
        ladder_inputs=ladder,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.FORCE_OFF
    assert actions[0].reason == "active_invalid_state_force_off"


@pytest.mark.unit
def test_invalid_tier_skipped_not_force_off_from_missing_ch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ключ без own conv (INVALID): cleanup не трогает (не mass FORCE_OFF)."""
    _patch_catalog(monkeypatch, _catalog_all_invalid())
    kw = _calc_kw(
        ks_id=KS_ID,
        text="no_conv",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=0.0,
        views=0,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    contexts = [ctx]
    prepared = build_prepared_from_contexts(contexts)
    ladder = LadderInputs.from_contexts(contexts, rk_orders_per_cart=RK)
    elig = resolve_keyword_v3_eligibility(ctx, contexts)
    assert elig.data_tier == KeywordDataTier.KEYWORD_INVALID
    assert not elig.participates_in_ladder

    actions = plan_active_invalid_state_cleanup(
        prepared,
        max_pay_for_order=MAX_PFO,
        resolve=RESOLVE,
        ladder_inputs=ladder,
        eligibility_by_ks_id={KS_ID: elig},
    )
    assert actions == []


@pytest.mark.unit
def test_wl_max_invalid_min_valid_down_to_min(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WL MAX invalid / worst → DOWN MIN_CPA при valid MIN <= max."""
    _patch_catalog(monkeypatch, _catalog_max_invalid_min_valid())
    _patch_ladder_view_for_invalid_max(monkeypatch)
    _patch_cost_for_mode(
        monkeypatch,
        {
            KeywordStrategyMode.MIN_CPA: (300.0, False),
            KeywordStrategyMode.OPTIMUM: (float("inf"), False),
            KeywordStrategyMode.MAX_CONVERSION: (242_360.0, True),
        },
    )
    ctx = _ctx_max_wl()
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=RK)

    actions = plan_active_invalid_state_cleanup(
        prepared,
        max_pay_for_order=MAX_PFO,
        resolve=RESOLVE,
        ladder_inputs=ladder,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DOWN
    assert actions[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert actions[0].reason == "active_invalid_state_down"
    assert actions[0].keyword_setting_id == KS_ID


@pytest.mark.unit
def test_wl_max_all_lower_worst_or_invalid_force_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WL MAX invalid, MIN тоже worst/huge → FORCE_OFF."""
    cat = {
        AggressionTargetMode.MIN_CPA: _mc(
            AggressionTargetMode.MIN_CPA, place=22, cpa=500.0, valid=True
        ),
        AggressionTargetMode.OPTIMUM: _mc(
            AggressionTargetMode.OPTIMUM, place=None, cpa=None, valid=False
        ),
        AggressionTargetMode.MAX_CONVERSION: _mc(
            AggressionTargetMode.MAX_CONVERSION, place=None, cpa=None, valid=False
        ),
    }
    _patch_catalog(monkeypatch, cat)
    _patch_ladder_view_for_invalid_max(
        monkeypatch,
        min_source=LadderCostSource.WORST,
        min_cost=500.0,
    )

    _patch_cost_for_mode(
        monkeypatch,
        {
            KeywordStrategyMode.MIN_CPA: (500.0, True),
            KeywordStrategyMode.OPTIMUM: (500.0, True),
            KeywordStrategyMode.MAX_CONVERSION: (500.0, True),
        },
    )

    ctx = _ctx_max_wl()
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=RK)

    actions = plan_active_invalid_state_cleanup(
        prepared,
        max_pay_for_order=MAX_PFO,
        resolve=RESOLVE,
        ladder_inputs=ladder,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.FORCE_OFF
    assert actions[0].reason == "active_invalid_state_force_off"


@pytest.mark.unit
def test_cleanup_runs_when_max_cpa_guard_skips_operational(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard skip (same_target_place); active_invalid_cleanup всё равно DOWN."""
    cat = {
        AggressionTargetMode.MIN_CPA: ModeCandidate(
            mode=AggressionTargetMode.MIN_CPA,
            position=22,
            bid=510.0,
            predicted_cpa=337.0,
            is_valid=True,
        ),
        AggressionTargetMode.OPTIMUM: ModeCandidate(
            mode=AggressionTargetMode.OPTIMUM,
            position=22,
            bid=510.0,
            predicted_cpa=337.0,
            is_valid=True,
        ),
        AggressionTargetMode.MAX_CONVERSION: ModeCandidate(
            mode=AggressionTargetMode.MAX_CONVERSION,
            position=1,
            bid=14_555.0,
            predicted_cpa=523.0,
            is_valid=False,
        ),
    }
    _patch_catalog(monkeypatch, cat)

    def _fake_view_guard(
        ctx: KeywordV3Context,
        ladder_inputs: LadderInputs,
        *,
        eligibility: object = None,
    ) -> LadderView:
        _ = ctx, ladder_inputs, eligibility

        def _stage(
            mode: AggressionTargetMode,
            source: LadderCostSource,
            cost: float | None,
            valid: bool,
        ) -> LadderStageResult:
            return LadderStageResult(
                mode=mode,
                is_valid=valid,
                cost=cost,
                source=source,
                candidate=cat[mode],
            )

        return LadderView(
            stages={
                AggressionTargetMode.MIN_CPA: _stage(
                    AggressionTargetMode.MIN_CPA, LadderCostSource.PROFILE, 337.0, True
                ),
                AggressionTargetMode.OPTIMUM: _stage(
                    AggressionTargetMode.OPTIMUM, LadderCostSource.PROFILE, 337.0, True
                ),
                AggressionTargetMode.MAX_CONVERSION: _stage(
                    AggressionTargetMode.MAX_CONVERSION,
                    LadderCostSource.WORST,
                    523.0,
                    False,
                ),
            }
        )

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view.resolve_ladder_stage_display",
        _fake_view_guard,
    )
    _patch_cost_for_mode(
        monkeypatch,
        {
            KeywordStrategyMode.MIN_CPA: (337.0, False),
            KeywordStrategyMode.OPTIMUM: (337.0, False),
            KeywordStrategyMode.MAX_CONVERSION: (523.0, True),
        },
    )

    costs = {
        KeywordStrategyMode.MIN_CPA: 337.0,
        KeywordStrategyMode.OPTIMUM: 337.0,
        KeywordStrategyMode.MAX_CONVERSION: 523.0,
    }

    def _fake_resolve_cost(
        *,
        ctx: KeywordV3Context,
        to_mode: KeywordStrategyMode,
        **_: object,
    ) -> tuple[float, bool]:
        _ = ctx
        return costs.get(to_mode, float("inf")), False

    def _fake_trim_cost(
        ctx: KeywordV3Context,
        mode: KeywordStrategyMode,
        *,
        current: KeywordStrategyMode,
        **__: object,
    ) -> tuple[float, bool]:
        _ = ctx
        if mode == current == KeywordStrategyMode.MAX_CONVERSION:
            return 523.0, True
        return costs.get(mode, float("inf")), False

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.resolve_effective_state_cost_for_mode",
        _fake_resolve_cost,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._trim_state_cost_for_mode",
        _fake_trim_cost,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view.operational_cpo_at_keyword_target_place",
        lambda _ctx, *, ladder_inputs: 300.0,
    )

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.should_skip_trim_for_same_effective_target",
        lambda **_: True,
    )

    ctx = _ctx_max_wl(target_place=1)
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=RK)

    guard_actions = plan_max_cpa_guard(
        prepared,
        max_pay_for_order=MAX_PFO,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        ladder_inputs=ladder,
    )
    assert guard_actions == []

    cleanup_actions = plan_active_invalid_state_cleanup(
        prepared,
        max_pay_for_order=MAX_PFO,
        resolve=RESOLVE,
        ladder_inputs=ladder,
    )
    assert len(cleanup_actions) == 1
    assert cleanup_actions[0].action == V3ActionType.DOWN
    assert cleanup_actions[0].target_strategy_mode == KeywordStrategyMode.OPTIMUM


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orchestrator_runs_cleanup_before_realloc() -> None:
    """Preamble: cleanup вызывается до realloc; stored MAX не доходит до realloc как MAX."""
    from unittest.mock import AsyncMock, patch

    from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater_v2.adv_control_system.sales_state.sales_states import (
        SalesStates,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator import (
        process_adv_v3,
    )

    complex_adv = MagicMock()
    complex_adv.adv_id = 32824944
    complex_adv.adv_setting = MagicMock()
    complex_adv.shelf_promotion_active = False
    complex_adv.individual_keywords_target_place_mode = False
    complex_adv.v3_rollout_aggressiveness = 2
    complex_adv.get_keywords = AsyncMock(return_value=[])

    ctx_max = _ctx_max_wl()
    call_order: list[str] = []
    prepared_builds = 0

    def _cleanup(*_a: object, **_k: object) -> list:
        call_order.append("cleanup")
        return [
            MagicMock(
                keyword_setting_id=KS_ID,
                action=V3ActionType.DOWN,
                target_strategy_mode=KeywordStrategyMode.MIN_CPA,
                reason="active_invalid_state_down",
            )
        ]

    def _realloc(*_a: object, **_k: object) -> list:
        call_order.append("realloc")
        prepared = _k.get("prepared") or (_a[0] if _a else None)
        if prepared:
            for _ctx, mode in prepared:
                assert mode != KeywordStrategyMode.MAX_CONVERSION
        return []

    def _build_prepared(_contexts: object) -> list:
        nonlocal prepared_builds
        prepared_builds += 1
        if prepared_builds <= 1:
            return [(ctx_max, KeywordStrategyMode.MAX_CONVERSION)]
        return [(ctx_max, KeywordStrategyMode.MIN_CPA)]

    dto = MagicMock()
    bootstrap = MagicMock(return_value=[])
    expansion = MagicMock(return_value=[])

    with (
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.is_resolve_valid",
            return_value=True,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.compute_resolve_cost_threshold",
            return_value=100.0,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._load_v3_wb_context",
            new=AsyncMock(return_value=(dto, {})),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_keyword_v3_contexts",
            return_value=[ctx_max],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.build_prepared_from_contexts",
            side_effect=_build_prepared,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_data_bootstrap_v3",
            bootstrap,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_active_invalid_state_cleanup",
            side_effect=_cleanup,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_cost_reallocation",
            side_effect=_realloc,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_profitable_expansion",
            expansion,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater.get_plan_data",
            return_value=MagicMock(
                max_pay_for_order=100.0, orders=10, target_pay_for_order=80.0
            ),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.AdvSettingAutoUpdater"
        ) as updater_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.ChangePlanFact"
        ) as plan_fact_cls,
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.detect_campaign_state",
            return_value=SalesStates.OPTIMAL,
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.select_v3_post_gate_actions",
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.V3TickKeywordLedger.flush_to_db",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator._apply_v3_phase",
            side_effect=lambda ledger, actions, _profiles: [],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.plan_max_cpa_guard",
            return_value=[],
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3.orchestrator.cache_worst_costs_for_adv",
            new=AsyncMock(),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rk_orders_per_cart_7d",
            new=AsyncMock(return_value=RK),
        ),
        patch(
            "app.modules.shop_runner.service_manager.services.v3_point_order_cpo.load_rec_orders_per_view_for_v3",
            new=AsyncMock(return_value=None),
        ),
    ):
        plan_fact = MagicMock()
        plan_fact.check_equal_in_cache = AsyncMock(return_value=True)
        plan_fact_cls.return_value = plan_fact
        updater_cls.return_value.get_fact_data = AsyncMock(
            return_value=MagicMock(pay_for_order=10.0, predict_orders=5)
        )
        await process_adv_v3(complex_adv, wb_shop_data_manager=MagicMock())

    assert call_order.index("cleanup") < call_order.index("realloc")
