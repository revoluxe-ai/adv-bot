"""Unit: UpdateContextManager."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    UpdateContext,
    UpdateContextInput,
    UpdateContextManager,
)
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from tests.unit.test_auto_updater_v3 import _calc_kw


def _tick_input(keywords) -> UpdateContextInput:
    return UpdateContextInput(
        keywords=keywords,
        plan=PlanData(orders=10, target_pay_for_order=100, max_pay_for_order=200),
        fact=FactData(
            predict_orders=5.0,
            original_orders=5.0,
            pay_for_order=50.0,
            fact_method=FactMethods.DIRECT_SALES,
        ),
        raw_profiles={},
    )


@pytest.mark.unit
def test_build_returns_update_context() -> None:
    keywords = [
        _calc_kw(
            ks_id=1,
            text="kw1",
            mode=KeywordStrategyMode.MIN_CPA,
            rating=1.0,
        ),
        _calc_kw(
            ks_id=2,
            text="kw2",
            mode=KeywordStrategyMode.OPTIMUM,
            rating=2.0,
        ),
    ]
    ctx = UpdateContextManager().build(_tick_input(keywords))
    assert isinstance(ctx, UpdateContext)
    assert len(ctx.prepared) == 2
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.MIN_CPA
    assert ctx.keywords[1].current_mode == KeywordStrategyMode.OPTIMUM
    assert ctx.keywords[0].next_state == []
    assert ctx.prepared.rows[0].keyword.text == "kw1"
    assert ctx.adv_state.max_pay_for_order == 200.0
