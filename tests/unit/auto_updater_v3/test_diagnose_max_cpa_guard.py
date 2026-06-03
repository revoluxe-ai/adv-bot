"""Unit: ``diagnose_max_cpa_guard_keyword`` совпадает с live trim skip по operational CPO."""

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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    diagnose_max_cpa_guard_keyword,
    plan_max_cpa_guard,
    should_skip_trim_for_same_effective_target,
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
KS_ID = 301
RK = 0.2


def _catalog_opt_min_same_place() -> dict[AggressionTargetMode, ModeCandidate]:
    """M/O на p22; C на p1 — trim OPT→MIN при operational>max не same-place skip."""

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

    cheap = 337.0
    dear = 523.0
    return {
        AggressionTargetMode.MIN_CPA: _mc(
            AggressionTargetMode.MIN_CPA, 22, 510.0, cheap
        ),
        AggressionTargetMode.OPTIMUM: _mc(
            AggressionTargetMode.OPTIMUM, 22, 510.0, cheap
        ),
        AggressionTargetMode.MAX_CONVERSION: _mc(
            AggressionTargetMode.MAX_CONVERSION, 1, 14_555.0, dear
        ),
    }


def _profile_tonal() -> list[PositionProfilePoint]:
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


def _ctx_opt_at_place(*, place: int) -> KeywordV3Context:
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
                update={"target_place": place}
            )
        }
    )
    return KeywordV3Context(keyword=kw, position_profile=_profile_tonal())


def _patch_catalog_and_trim_costs(
    monkeypatch: pytest.MonkeyPatch,
    *,
    operational_cpo: float | None,
) -> None:
    cat = _catalog_opt_min_same_place()
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._mode_catalog_for_ctx",
        lambda _ctx, _prepared, _ladder=None: cat,
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
        if mode == current == KeywordStrategyMode.OPTIMUM:
            # trim ищет MIN; operational CPO — отдельный patch для skip-check
            return 500.0, False
        return costs.get(mode, float("inf")), False

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.resolve_effective_state_cost_for_mode",
        _fake_resolve_cost,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner._trim_state_cost_for_mode",
        _fake_trim_cost,
    )

    def _fake_operational(
        ctx: KeywordV3Context, *, ladder_inputs: object
    ) -> float | None:
        _ = ctx, ladder_inputs
        return operational_cpo

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view.operational_cpo_at_keyword_target_place",
        _fake_operational,
    )


@pytest.mark.unit
def test_should_skip_same_place_when_operational_under_max(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O/M один place: operational <= max → skip trim (как live guard)."""
    _patch_catalog_and_trim_costs(monkeypatch, operational_cpo=300.0)
    ctx = _ctx_opt_at_place(place=22)
    prepared = build_prepared_from_contexts([ctx])
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )

    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=RK)
    cat = _catalog_opt_min_same_place()
    assert should_skip_trim_for_same_effective_target(
        ctx=ctx,
        current=KeywordStrategyMode.OPTIMUM,
        trim_target=KeywordStrategyMode.MIN_CPA,
        catalog=cat,
        cost_ceiling=MAX_PFO,
        ladder_inputs=ladder,
    )


@pytest.mark.unit
def test_should_not_skip_same_place_when_operational_above_max(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """O/M один place в каталоге, operational > max → trim не skip."""
    _patch_catalog_and_trim_costs(monkeypatch, operational_cpo=493.0)
    ctx = _ctx_opt_at_place(place=22)
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )

    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=RK)
    cat = _catalog_opt_min_same_place()
    assert not should_skip_trim_for_same_effective_target(
        ctx=ctx,
        current=KeywordStrategyMode.OPTIMUM,
        trim_target=KeywordStrategyMode.MIN_CPA,
        catalog=cat,
        cost_ceiling=MAX_PFO,
        ladder_inputs=ladder,
    )


@pytest.mark.unit
def test_diagnose_same_place_skip_when_operational_under_max(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_catalog_and_trim_costs(monkeypatch, operational_cpo=300.0)
    ctx = _ctx_opt_at_place(place=22)
    prepared = build_prepared_from_contexts([ctx])
    diag = diagnose_max_cpa_guard_keyword(
        ctx,
        KeywordStrategyMode.OPTIMUM,
        max_pay_for_order=MAX_PFO,
        prepared=prepared,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        guard_would_run=True,
        fact_pay_for_order=554.0,
    )
    assert diag["trim_target_mode"] == KeywordStrategyMode.MIN_CPA.name
    assert "same_target_place" in (diag.get("guard_skip_reason") or "")
    assert diag.get("guard_action") is None


@pytest.mark.unit
def test_diagnose_no_same_place_skip_when_operational_above_max(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Кейс tonal: diagnose и live guard оба ожидают DOWN MIN."""
    _patch_catalog_and_trim_costs(monkeypatch, operational_cpo=493.0)
    ctx = _ctx_opt_at_place(place=22)
    prepared = build_prepared_from_contexts([ctx])
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )

    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=RK)
    diag = diagnose_max_cpa_guard_keyword(
        ctx,
        KeywordStrategyMode.OPTIMUM,
        max_pay_for_order=MAX_PFO,
        prepared=prepared,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        guard_would_run=True,
        fact_pay_for_order=554.0,
        ladder_inputs=ladder,
    )
    assert diag["ladder_inputs_source"] == "ladder_inputs"
    assert diag["rk_orders_per_cart"] == RK
    skip = diag.get("guard_skip_reason") or ""
    assert "same_target_place" not in skip
    assert "same_effective_target" not in skip
    guard_action = diag.get("guard_action")
    assert guard_action is not None
    assert guard_action["action"] == V3ActionType.DOWN.value
    assert guard_action["target_strategy_mode"] == KeywordStrategyMode.MIN_CPA.name

    live = plan_max_cpa_guard(
        prepared,
        max_pay_for_order=MAX_PFO,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        ladder_inputs=ladder,
    )
    assert len(live) == 1
    assert live[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
    assert guard_action["target_strategy_mode"] == live[0].target_strategy_mode.name


@pytest.mark.unit
def test_diagnose_guard_parity_dense_tonal_with_rk_ladder() -> None:
    """С RK ladder diagnose и plan_max_cpa_guard совпадают (кейс adv 32824944)."""
    from tests.unit.auto_updater_v3.test_max_cpa_guard_white_list_trim import (
        _profile_dense_tonal,
    )

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
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )

    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=rk)
    live = plan_max_cpa_guard(
        prepared,
        max_pay_for_order=MAX_PFO,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        ladder_inputs=ladder,
    )
    diag = diagnose_max_cpa_guard_keyword(
        ctx,
        KeywordStrategyMode.OPTIMUM,
        max_pay_for_order=MAX_PFO,
        prepared=prepared,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        ladder_inputs=ladder,
        fact_pay_for_order=554.0,
    )
    assert diag["ladder_inputs_source"] == "ladder_inputs"
    assert diag["rk_orders_per_cart"] == rk
    assert len(live) == 1
    assert diag["guard_action"] is not None
    assert diag["guard_action"]["action"] == V3ActionType.DOWN.value
    assert (
        diag["guard_action"]["target_strategy_mode"]
        == live[0].target_strategy_mode.name
    )


@pytest.mark.unit
def test_diagnose_derived_ladder_differs_from_rk_ladder() -> None:
    """Без ladder_inputs нет RK — CPO/operational расходятся с production guard."""
    from tests.unit.auto_updater_v3.test_max_cpa_guard_white_list_trim import (
        _profile_dense_tonal,
    )

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
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )

    ladder = LadderInputs.from_contexts([ctx], rk_orders_per_cart=rk)
    diag_rk = diagnose_max_cpa_guard_keyword(
        ctx,
        KeywordStrategyMode.OPTIMUM,
        max_pay_for_order=MAX_PFO,
        prepared=prepared,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        ladder_inputs=ladder,
        fact_pay_for_order=554.0,
    )
    diag_derived = diagnose_max_cpa_guard_keyword(
        ctx,
        KeywordStrategyMode.OPTIMUM,
        max_pay_for_order=MAX_PFO,
        prepared=prepared,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        fact_pay_for_order=554.0,
    )
    assert diag_rk["ladder_inputs_source"] == "ladder_inputs"
    assert diag_rk["rk_orders_per_cart"] == rk
    assert diag_derived["ladder_inputs_source"] == "derived_from_prepared"
    assert diag_derived["rk_orders_per_cart"] is None
    assert diag_rk["operational_cpo_at_target_place"] is not None
    assert diag_derived["operational_cpo_at_target_place"] != diag_rk[
        "operational_cpo_at_target_place"
    ]
    live = plan_max_cpa_guard(
        prepared,
        max_pay_for_order=MAX_PFO,
        shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
        ladder_inputs=ladder,
    )
    assert len(live) == 1
    assert diag_rk["guard_action"] is not None
    assert (
        diag_rk["guard_action"]["target_strategy_mode"]
        == live[0].target_strategy_mode.name
    )
