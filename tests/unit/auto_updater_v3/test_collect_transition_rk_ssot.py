"""Unit: ``collect_transition_candidates`` — RK catalog/worst SSOT как expansion."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.effective_ladder_steps import (
    iter_effective_upper_modes,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    SelectionPolicy,
    _catalog_for_ctx,
    build_prepared_from_contexts,
    build_worst_per_state_costs,
    collect_transition_candidates,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.auto_updater_v3.conftest import RK_ORDERS_PER_CART_TEST, ctx
from tests.unit.test_auto_updater_v3 import _calc_kw as _calc_kw_fixture

RK = RK_ORDERS_PER_CART_TEST
TS = datetime(2024, 1, 1, tzinfo=UTC)


def _o_eq_m_profile() -> list[PositionProfilePoint]:
    return [
        PositionProfilePoint(
            position=1,
            bid=10_000,
            predicted_conversion=0.13,
            pay_for_cart=50.0,
            timestamp=TS,
        ),
        PositionProfilePoint(
            position=40,
            bid=500,
            predicted_conversion=0.015,
            pay_for_cart=10.0,
            timestamp=TS,
        ),
    ]


def _policy() -> SelectionPolicy:
    return SelectionPolicy.from_aggressiveness(
        click_mode=ShelfClickMode.ORGANIC_DOMINANT,
        aggressiveness=V3RolloutAggressiveness.MAX,
    )


@pytest.mark.unit
def test_rk_ladder_catalog_o_eq_m_effective_up_only_max() -> None:
    """RK CPO на профиле O=M: effective UP из MIN только в MAX."""
    prof = _o_eq_m_profile()
    rk_cat = build_mode_candidates(
        profile=prof, keyword_text="kw", rk_orders_per_cart=RK
    )
    assert rk_cat[AggressionTargetMode.MIN_CPA].position == rk_cat[
        AggressionTargetMode.OPTIMUM
    ].position
    assert list(
        iter_effective_upper_modes(KeywordStrategyMode.MIN_CPA, rk_cat)
    ) == [KeywordStrategyMode.MAX_CONVERSION]


@pytest.mark.unit
def test_collect_transition_rk_skips_opt_alias_matches_expansion() -> None:
    """MIN→MAX при O=M; pooled candidates совпадают с profitable_expansion."""
    prof = _o_eq_m_profile()
    min_kw = _calc_kw_fixture(
        ks_id=20,
        text="rk_ssot",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=5.0,
        conv=0.05,
        hard_status=2,
    )
    contexts = [KeywordV3Context(keyword=min_kw, position_profile=prof)]
    prepared = build_prepared_from_contexts(contexts)
    ladder = LadderInputs.from_contexts(contexts, rk_orders_per_cart=RK)
    policy = _policy()

    catalog = _catalog_for_ctx(contexts[0], prepared, ladder_inputs=ladder)
    assert list(iter_effective_upper_modes(KeywordStrategyMode.MIN_CPA, catalog)) == [
        KeywordStrategyMode.MAX_CONVERSION
    ]

    cands = collect_transition_candidates(
        prepared, policy=policy, ladder_inputs=ladder
    )
    min_up = [c for c in cands if c.from_mode == KeywordStrategyMode.MIN_CPA]
    assert len(min_up) == 1
    assert min_up[0].to_mode == KeywordStrategyMode.MAX_CONVERSION
    assert KeywordStrategyMode.OPTIMUM not in {c.to_mode for c in cands}


@pytest.mark.unit
def test_collect_does_not_rebuild_worst_when_ladder_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``collect_transition_candidates`` не вызывает ``build_worst_per_state_costs``."""
    prof = _o_eq_m_profile()
    contexts = [ctx(ks_id=21, mode=KeywordStrategyMode.MIN_CPA, profile=prof)]
    prepared = build_prepared_from_contexts(contexts)
    ladder = LadderInputs.from_contexts(contexts, rk_orders_per_cart=RK)
    rebuild_calls: list[int] = []

    def _spy_build_worst(*_a: object, **_k: object) -> dict[AggressionTargetMode, float]:
        rebuild_calls.append(1)
        return {}

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking.build_worst_per_state_costs",
        _spy_build_worst,
    )
    collect_transition_candidates(
        prepared, policy=_policy(), ladder_inputs=ladder
    )
    assert rebuild_calls == []
    assert build_worst_per_state_costs(prepared, ladder_inputs=ladder) == {}
