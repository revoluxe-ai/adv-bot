"""Unit: gap-rebalance — NO_DATA (нет V2 CPO) = 1 балл в бюджете UP."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rebalance import (
    plan_ladder_gap_rebalance,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
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
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)

from tests.unit.auto_updater_v3.conftest import sample_profile


def _wl_kw(
    *,
    ks_id: int,
    mode: KeywordStrategyMode,
    conv: float,
    cpm_set_bid: int = 200,
) -> CalculatedKeyword:
    stat = make_zero_keyword_stat(f"k{ks_id}").model_copy(
        update={"views": 50, "clicks": 10, "conv_views_to_orders": conv}
    )
    return CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text=f"k{ks_id}",
            relevant=True,
            hard_status=2,
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


@pytest.mark.unit
def test_gap_rebalance_budget_includes_no_data_off_tail_as_one_point() -> None:
    """Хвост: OFF без V2 CPO даёт 1 UP (no_data_min_bid), не 0 баллов."""
    cheap = _wl_kw(ks_id=1, mode=KeywordStrategyMode.MIN_CPA, conv=0.08)
    # Якорь OFF с V2 CPO (не NO_DATA) — не съедает бюджетный UP.
    gap_off = _wl_kw(ks_id=2, mode=KeywordStrategyMode.OFF, conv=0.08)
    tail_no_data = _wl_kw(ks_id=3, mode=KeywordStrategyMode.OFF, conv=0.0, cpm_set_bid=0)
    prof = sample_profile()
    prepared = [
        (KeywordV3Context(keyword=cheap, position_profile=prof), KeywordStrategyMode.MIN_CPA),
        (KeywordV3Context(keyword=gap_off, position_profile=prof), KeywordStrategyMode.OFF),
        (KeywordV3Context(keyword=tail_no_data, position_profile=prof), KeywordStrategyMode.OFF),
    ]
    actions = plan_ladder_gap_rebalance(
        prepared,
        shelf_promotion_active=False,
        shelf_click_mode=ShelfClickMode.UNKNOWN,
        rollout_aggressiveness=1,
    )
    force_offs = [a for a in actions if a.action == V3ActionType.FORCE_OFF]
    assert len(force_offs) == 1
    assert force_offs[0].keyword_setting_id == 3
    ups = [a for a in actions if a.action == V3ActionType.UP]
    assert len(ups) == 1
    assert ups[0].keyword_setting_id == 3
    assert ups[0].reason == "ladder_gap_rebalance_up"
    assert ups[0].target_strategy_mode == KeywordStrategyMode.MIN_CPA
