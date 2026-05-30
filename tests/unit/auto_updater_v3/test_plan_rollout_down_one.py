"""Unit: ``plan_rollout_down_one`` — каталог с RK ratio через ``LadderInputs``."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner import (
    plan_rollout_down_one,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    build_prepared_from_contexts,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from tests.unit.auto_updater_v3.conftest import RK_ORDERS_PER_CART_TEST, ctx

RK = RK_ORDERS_PER_CART_TEST
TS = datetime(2024, 1, 1, tzinfo=UTC)


def _profile() -> list[PositionProfilePoint]:
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


@pytest.mark.unit
def test_plan_rollout_down_one_passes_rk_to_build_mode_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DOWN path: ``rk_orders_per_cart`` из ``LadderInputs``, не conv-only fallback."""
    captured: list[float | None] = []

    def _spy_build_mode_candidates(
        *,
        profile,
        keyword_text: str,
        conv_views_to_orders=None,
        rk_orders_per_cart=None,
    ):
        captured.append(rk_orders_per_cart)
        return build_mode_candidates(
            profile=profile,
            keyword_text=keyword_text,
            conv_views_to_orders=conv_views_to_orders,
            rk_orders_per_cart=rk_orders_per_cart,
        )

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_planner.build_mode_candidates",
        _spy_build_mode_candidates,
    )
    contexts = [
        ctx(ks_id=3, mode=KeywordStrategyMode.MAX_CONVERSION, profile=_profile()),
    ]
    prepared = build_prepared_from_contexts(contexts)
    ladder = LadderInputs.from_contexts(contexts, rk_orders_per_cart=RK)

    actions = plan_rollout_down_one(
        prepared,
        reason="stable",
        ladder_inputs=ladder,
    )

    assert captured == [RK]
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DOWN
    assert actions[0].keyword_setting_id == 3


@pytest.mark.unit
def test_plan_rollout_down_one_without_ladder_still_builds_ladder_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Без явного ``ladder_inputs`` — ``ladder_inputs_for_prepared`` (rk может быть None)."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3 import (
        rollout_planner as rp_mod,
    )

    seen_ladder: list[object] = []
    orig = rp_mod._mode_catalog_for_ctx

    def _track(ctx, prepared=None, ladder_inputs=None):
        seen_ladder.append(ladder_inputs)
        return orig(ctx, prepared, ladder_inputs)

    monkeypatch.setattr(rp_mod, "_mode_catalog_for_ctx", _track)
    contexts = [ctx(ks_id=4, mode=KeywordStrategyMode.OPTIMUM, profile=_profile())]
    prepared = build_prepared_from_contexts(contexts)

    plan_rollout_down_one(prepared, reason="overspend")

    assert len(seen_ladder) == 1
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs as LI,
    )

    assert isinstance(seen_ladder[0], LI)
