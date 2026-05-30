"""Unit: MAX_CPA_GUARD — white list, M@22 / O=C@1, CPO ниже/выше max (кейс adv 32824944)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    resolve_next_effective_step_down,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_max_cpa_guard,
    plan_profitable_expansion,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    build_prepared_from_contexts,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.test_auto_updater_v3 import _calc_kw

TS = datetime(2024, 1, 1, tzinfo=UTC)
MAX_PFO = 400.0
MIN_CPO = 337.86
OPT_MAX_CPO = 523.42
KS_ID = 301


def _dense_tonal_catalog() -> dict[AggressionTargetMode, ModeCandidate]:
    """M p22 / O=C p1 — как «плотный тональный крем»."""

    def _mc(
        mode: AggressionTargetMode, place: int, bid: float, cpa: float
    ) -> ModeCandidate:
        return ModeCandidate(
            mode=mode,
            position=place,
            bid=bid,
            predicted_cpa=cpa,
            is_valid=True,
        )

    return {
        AggressionTargetMode.MIN_CPA: _mc(
            AggressionTargetMode.MIN_CPA, 22, 510.0, MIN_CPO
        ),
        AggressionTargetMode.OPTIMUM: _mc(
            AggressionTargetMode.OPTIMUM, 1, 14_555.0, OPT_MAX_CPO
        ),
        AggressionTargetMode.MAX_CONVERSION: _mc(
            AggressionTargetMode.MAX_CONVERSION, 1, 14_555.0, OPT_MAX_CPO
        ),
    }


def _profile_dense_tonal() -> list[PositionProfilePoint]:
    return [
        PositionProfilePoint(
            position=1,
            bid=14_555.0,
            predicted_conversion=0.13,
            pay_for_cart=1.0,
            timestamp=TS,
        ),
        PositionProfilePoint(
            position=22,
            bid=510.0,
            predicted_conversion=0.02,
            pay_for_cart=1.0,
            timestamp=TS,
        ),
    ]


def _patch_dense_catalog_and_costs(monkeypatch: pytest.MonkeyPatch) -> None:
    """SSOT cost/place для guard: фиксированные CPO и каталог (RK-профиль вторичен)."""
    cat = _dense_tonal_catalog()
    costs: dict[KeywordStrategyMode, tuple[float, bool]] = {
        KeywordStrategyMode.MIN_CPA: (MIN_CPO, False),
        KeywordStrategyMode.OPTIMUM: (OPT_MAX_CPO, False),
        KeywordStrategyMode.MAX_CONVERSION: (OPT_MAX_CPO, False),
    }

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._mode_catalog_for_ctx",
        lambda _ctx, _prepared, _ladder=None: cat,
    )

    def _fake_cost(
        *,
        ctx: KeywordV3Context,
        to_mode: KeywordStrategyMode,
        **_: object,
    ) -> tuple[float, bool]:
        _ = ctx
        return costs.get(to_mode, (float("inf"), False))

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.resolve_effective_state_cost_for_mode",
        _fake_cost,
    )


def _run_guard(
    *,
    mode: KeywordStrategyMode,
    monkeypatch: pytest.MonkeyPatch,
) -> list:
    _patch_dense_catalog_and_costs(monkeypatch)
    kw = _calc_kw(
        ks_id=KS_ID,
        text="плотный тональный крем",
        mode=mode,
        rating=10.0,
        conv=0.02,
        hard_status=2,
    )
    prepared = build_prepared_from_contexts(
        [KeywordV3Context(keyword=kw, position_profile=_profile_dense_tonal())]
    )
    return plan_max_cpa_guard(
        prepared,
        max_pay_for_order=MAX_PFO,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )


@pytest.mark.unit
def test_max_cpa_guard_white_list_opt_down_to_min(monkeypatch: pytest.MonkeyPatch) -> None:
    """WL + OPT: O/C CPO>max, M CPO<=max → DOWN MIN, reason max_cpa_guard_."""
    actions = _run_guard(mode=KeywordStrategyMode.OPTIMUM, monkeypatch=monkeypatch)
    downs = [a for a in actions if a.action == V3ActionType.DOWN]
    assert len(downs) == 1
    assert downs[0].keyword_setting_id == KS_ID
    assert downs[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert downs[0].reason.startswith("max_cpa_guard_")


@pytest.mark.unit
def test_max_cpa_guard_white_list_max_effective_down_to_min(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WL + MAX: O=C alias — effective DOWN в MIN, без промежуточного OPT."""
    cat = _dense_tonal_catalog()
    step = resolve_next_effective_step_down(KeywordStrategyMode.MAX_CONVERSION, cat)
    assert step.next_mode == KeywordStrategyMode.MIN_CPA
    assert any("OPTIMUM" in msg for msg in step.skipped_aliases)

    actions = _run_guard(mode=KeywordStrategyMode.MAX_CONVERSION, monkeypatch=monkeypatch)
    downs = [a for a in actions if a.action == V3ActionType.DOWN]
    assert len(downs) == 1
    assert downs[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert downs[0].reason.startswith("max_cpa_guard_")
    assert KeywordStrategyMode.OPTIMUM not in {a.target_strategy_mode for a in downs}


def _policy() -> SelectionPolicy:
    return SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )


@pytest.mark.unit
def test_max_cpa_guard_operational_target_place_down_to_min() -> None:
    """WL OPT @target_place=1: CPO на месте > max, каталог O на p22 дешевле — DOWN MIN."""
    rk = 0.2
    kw = _calc_kw(
        ks_id=KS_ID,
        text="плотный тональный крем",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=10.0,
        conv=0.02,
        hard_status=2,
    )
    kw = kw.model_copy(
        update={
            "keyword_setting": kw.keyword_setting.model_copy(
                update={"target_place": 1}
            )
        }
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=_profile_dense_tonal())
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=rk)
    actions = plan_max_cpa_guard(
        prepared,
        max_pay_for_order=MAX_PFO,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        ladder_inputs=ladder,
    )
    downs = [a for a in actions if a.action == V3ActionType.DOWN]
    assert len(downs) == 1
    assert downs[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA


@pytest.mark.unit
def test_expansion_rejects_mode_above_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    """MIN@22: M CPO<=resolve, O/C>resolve — expansion не выбирает OPT/MAX."""
    _patch_dense_catalog_and_costs(monkeypatch)
    kw = _calc_kw(
        ks_id=KS_ID,
        text="плотный тональный крем",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=10.0,
        conv=0.02,
        hard_status=2,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=_profile_dense_tonal())
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts([ctx])
    resolve = 400.0
    actions = plan_profitable_expansion(
        prepared,
        resolve=resolve,
        policy=_policy(),
        ladder_inputs=ladder,
    )
    assert not actions
