"""Unit: лидер CPO белого списка для V3 tick report."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    KeywordV3DecisionTier,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordDataTier,
    KeywordV3Eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    find_white_list_cost_leader,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _full_elig() -> KeywordV3Eligibility:
    return KeywordV3Eligibility(
        data_tier=KeywordDataTier.KEYWORD_FULL,
        allowed_modes=frozenset(
            {
                KeywordStrategyMode.MIN_CPA,
                KeywordStrategyMode.OPTIMUM,
                KeywordStrategyMode.MAX_CONVERSION,
            }
        ),
        max_allowed_mode=KeywordStrategyMode.MAX_CONVERSION,
        participates_in_ladder=True,
        target_place_fallback_zero=False,
        imputed=False,
        fallback_kind=None,
        decision_tier=KeywordV3DecisionTier.FULL,
    )


def _pfo_elig() -> KeywordV3Eligibility:
    return KeywordV3Eligibility(
        data_tier=KeywordDataTier.KEYWORD_PFO,
        allowed_modes=frozenset(
            {
                KeywordStrategyMode.MIN_CPA,
                KeywordStrategyMode.OPTIMUM,
                KeywordStrategyMode.MAX_CONVERSION,
            }
        ),
        max_allowed_mode=KeywordStrategyMode.MAX_CONVERSION,
        participates_in_ladder=True,
        target_place_fallback_zero=False,
        imputed=False,
        fallback_kind=None,
        decision_tier=KeywordV3DecisionTier.NO_CONV,
    )


@pytest.mark.unit
def test_find_white_list_cost_leader_picks_highest_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FULL-tier БС: лидер по state CPO."""
    ctx_cheap = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=1,
            text="дешёвый",
            mode=KeywordStrategyMode.MIN_CPA,
            rating=1.0,
            hard_status=2,
        ),
        position_profile=[],
    )
    ctx_dear = KeywordV3Context(
        keyword=_calc_kw(
            ks_id=2,
            text="дорогой",
            mode=KeywordStrategyMode.MAX_CONVERSION,
            rating=1.0,
            hard_status=2,
        ),
        position_profile=[],
    )
    prepared = build_prepared_from_contexts([ctx_cheap, ctx_dear])
    ladder = LadderInputs.from_contexts(
        [ctx_cheap, ctx_dear], campaign_orders_per_cart_7d=None
    )
    eligibility = {1: _full_elig(), 2: _full_elig()}

    def _fake_cost(
        *,
        ctx: KeywordV3Context,
        to_mode: KeywordStrategyMode,
        **_: object,
    ) -> tuple[float, bool]:
        ks = ctx.keyword.keyword_setting_original_id
        if ks == 2:
            return (500.0, False)
        return (100.0, False)

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.resolve_effective_state_cost_for_mode",
        _fake_cost,
    )

    leader = find_white_list_cost_leader(
        [ctx_cheap, ctx_dear],
        prepared=prepared,
        eligibility_by_ks_id=eligibility,
        ladder_inputs=ladder,
    )
    assert leader is not None
    assert leader.keyword_setting_id == 2
    assert leader.cost_source == "state"
    assert leader.decision_cpo == 500.0


@pytest.mark.unit
def test_find_white_list_cost_leader_pfo_tier_uses_pay_for_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PFO-tier БС: decision по ``pay_for_order``, не state."""
    kw = _calc_kw(
        ks_id=3,
        text="pfo key",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        hard_status=2,
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=[])
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts([ctx], campaign_orders_per_cart_7d=None)

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.resolve_effective_state_cost_for_mode",
        lambda *, ctx, to_mode, **_: (50.0, False),
    )
    monkeypatch.setattr(
        type(kw),
        "pay_for_order",
        property(lambda self: 600.0 if self.keyword_setting.id == 3 else None),
    )

    leader = find_white_list_cost_leader(
        [ctx],
        prepared=prepared,
        eligibility_by_ks_id={3: _pfo_elig()},
        ladder_inputs=ladder,
    )
    assert leader is not None
    assert leader.cost_source == "pfo"
    assert leader.decision_cpo == 600.0
    assert leader.pfo_cpo == 600.0


@pytest.mark.unit
def test_find_white_list_cost_leader_full_uses_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kw = _calc_kw(
        ks_id=5,
        text="full wl",
        mode=KeywordStrategyMode.MAX_CONVERSION,
        rating=1.0,
        hard_status=2,
    )
    ctx = KeywordV3Context(
        keyword=kw,
        position_profile=[
            PositionProfilePoint(
                position=1,
                bid=100.0,
                predicted_conversion=0.1,
                pay_for_cart=1.0,
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            )
        ],
    )
    prepared = build_prepared_from_contexts([ctx])
    ladder = LadderInputs.from_contexts([ctx], campaign_orders_per_cart_7d=None)

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.resolve_effective_state_cost_for_mode",
        lambda *, ctx, to_mode, **_: (250.0, False),
    )

    leader = find_white_list_cost_leader(
        [ctx],
        prepared=prepared,
        eligibility_by_ks_id={5: _full_elig()},
        ladder_inputs=ladder,
    )
    assert leader is not None
    assert leader.cost_source == "state"
    assert leader.decision_cpo == 250.0
