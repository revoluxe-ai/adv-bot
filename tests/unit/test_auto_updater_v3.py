"""Unit tests for AutoUpdater v3 ladder, selector post-gate, and keyword JSON roundtrip."""

import json
from datetime import UTC, datetime

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ActivationStrategy,
    ShelfClickMode,
    activation_strategy_for_shelf_underperform,
    resolve_shelf_click_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    step_down,
    step_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
    normalize_v3_rollout_aggressiveness,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
    select_v3_post_gate_actions,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    TrafficClicksDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.position_profile_point import (
    PositionProfilePoint,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_cpm_sources import (
    KeywordCpmSources,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)


def _sample_profile() -> list[PositionProfilePoint]:
    return [
        PositionProfilePoint(
            position=1,
            bid=100,
            predicted_conversion=0.01,
            pay_for_cart=40.0,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        ),
        PositionProfilePoint(
            position=2,
            bid=80,
            predicted_conversion=0.02,
            pay_for_cart=25.0,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    ]


def _conv_for_pay_for_order(target_pfo: float, *, cpm: int = 200) -> float:
    """Подобрать conv при фиксированном CPM, чтобы pay_for_order ≈ target_pfo."""
    return cpm * 1000.0 / (target_pfo * 1_000_000.0)


def _calc_kw(
    *,
    ks_id: int,
    text: str,
    mode: KeywordStrategyMode,
    rating: float,
    views: int = 50,
    conv: float = 0.05,
    hard_status: int = 2,
    status: KeywordStatus = KeywordStatus.GOOD,
    reason: KeywordStatusReason = KeywordStatusReason.WHITE_LIST,
    above_rec: bool | None = True,
    cpm_set_bid: int = 200,
) -> CalculatedKeyword:
    stat = make_zero_keyword_stat(text).model_copy(
        update={"views": views, "clicks": 10, "orders": 2, "conv_views_to_orders": conv}
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
            status=status,
            reason=reason,
            best_keyword_status=True,
        ),
        rating=rating,
        target_pay_for_order=None,
        above_rec_conversion=above_rec,
        cpm_sources=KeywordCpmSources(cpm_set_bid=cpm_set_bid),
    )


@pytest.mark.unit
def test_normalize_v3_rollout_aggressiveness_clamps() -> None:
    assert normalize_v3_rollout_aggressiveness(None) == V3RolloutAggressiveness.MAX
    assert normalize_v3_rollout_aggressiveness(0) == V3RolloutAggressiveness.MIN
    assert normalize_v3_rollout_aggressiveness(2) == V3RolloutAggressiveness.MID
    assert normalize_v3_rollout_aggressiveness(99) == V3RolloutAggressiveness.MAX


@pytest.mark.unit
def test_ladder_step_up_down() -> None:
    assert step_up(KeywordStrategyMode.OFF) == KeywordStrategyMode.MIN_CPA
    assert step_up(KeywordStrategyMode.MAX_CONVERSION) is None
    assert step_down(KeywordStrategyMode.OFF) is None
    assert step_down(KeywordStrategyMode.MIN_CPA) == KeywordStrategyMode.OFF


@pytest.mark.unit
def test_select_v3_post_gate_returns_stub() -> None:
    ctx = KeywordV3Context(
        keyword=_calc_kw(ks_id=1, text="a", mode=KeywordStrategyMode.MIN_CPA, rating=1.0),
        position_profile=_sample_profile(),
    )
    actions = select_v3_post_gate_actions(
        contexts=[ctx],
        shelf_promotion_active=False,
    )
    assert len(actions) == 1
    assert actions[0].action == V3ActionType.DO_NOTHING
    assert actions[0].reason == "post_gate_preamble_only"


@pytest.mark.unit
def test_resolve_shelf_click_mode_and_activation_strategy() -> None:
    assert resolve_shelf_click_mode(None) == ShelfClickMode.UNKNOWN
    assert (
        resolve_shelf_click_mode(
            TrafficClicksDTO(organic_clicks=10, shelf_clicks=5, keyword_clicks=3)
        )
        == ShelfClickMode.ORGANIC_DOMINANT
    )
    assert (
        resolve_shelf_click_mode(
            TrafficClicksDTO(organic_clicks=5, shelf_clicks=10, keyword_clicks=3)
        )
        == ShelfClickMode.SHELF_DOMINANT_OR_EQUAL
    )
    assert (
        resolve_shelf_click_mode(
            TrafficClicksDTO(organic_clicks=7, shelf_clicks=7, keyword_clicks=3)
        )
        == ShelfClickMode.SHELF_DOMINANT_OR_EQUAL
    )
    assert (
        activation_strategy_for_shelf_underperform(ShelfClickMode.ORGANIC_DOMINANT)
        == ActivationStrategy.LAYERED
    )
    assert (
        activation_strategy_for_shelf_underperform(ShelfClickMode.SHELF_DOMINANT_OR_EQUAL)
        == ActivationStrategy.PIECEWISE
    )
    assert (
        activation_strategy_for_shelf_underperform(ShelfClickMode.UNKNOWN)
        == ActivationStrategy.PIECEWISE
    )


@pytest.mark.unit
def test_calculated_keyword_position_profile_json_roundtrip() -> None:
    kw = _calc_kw(ks_id=1, text="x", mode=KeywordStrategyMode.MIN_CPA, rating=1.0)
    kw = kw.model_copy(update={"position_profile": _sample_profile()})
    raw = kw.model_dump_json()
    restored = CalculatedKeyword.model_validate(json.loads(raw))
    assert restored.position_profile is not None
    assert restored.position_profile[0].position == 1
    assert restored.strategy_mode == KeywordStrategyMode.MIN_CPA
