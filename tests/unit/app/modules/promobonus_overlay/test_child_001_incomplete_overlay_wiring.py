"""RED regression CHILD-001: overlay SoT must drive keyword GOOD/BAD and cost-activity.

Инвариант: при ``promo_fraction > 0`` на ``ComplexAdv`` runtime CPO/plan пороги
должны браться из ``PlanFactProvider.get_effective_plan_data(..., complex_adv=...)``,
а не из сырых ``AdvSetting`` plan columns и не из вызова без ``ComplexAdv``.

См. BUGCASE-PROMOBONUS-P1-SSOT-20260908T014900Z / CHILD-001.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from app.modules.wb_adv_updater.calculated_keywords_manager.above_target_cooldown_entry import (
    AboveTargetCooldownEntry,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager import (
    CalculatedKeywordsManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.shared.domains.wb.utils.auto_campaign_cost_activity import (
    get_auto_campaign_cost_activity_metrics,
    is_auto_campaign_active,
)

from tests.factories.keyword_pipeline import HardStatus, PreCalculatedKeywordFactory


def _plan_fact_summary(
    *,
    fact_predict_orders: float = 5.0,
    fact_pay_for_order: float | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        fact_predict_orders=fact_predict_orders,
        fact_original_orders=None,
        fact_pay_for_order=fact_pay_for_order,
        fact_method=None,
        plan_fact_ch_ts_msk="01.01.2025 00:00",
    )


def _fake_adv_setting(
    *,
    adv_id: int = 88001,
    plan_orders: int = 10,
    target: float = 50.0,
    max_pay: float = 100.0,
) -> SimpleNamespace:
    return SimpleNamespace(
        adv_id=adv_id,
        plan_for_sales_for_day=plan_orders,
        target_price_for_order=target,
        max_price_for_order=max_pay,
        raise_plan_on_promobonuses=True,
        sales_predict_method=FactMethods.DIRECT_SALES,
        auto_shelf_bid_control_enabled=False,
        bidder_coroutine_type=None,
        promo_fraction=None,
    )


def _complex_adv_with_promo(
    adv_setting: SimpleNamespace,
    *,
    promo_fraction: Decimal,
) -> MagicMock:
    mock = MagicMock()
    mock.adv_id = adv_setting.adv_id
    mock.hard_min_ctr = None
    mock.rec_system_promotion_mode_active = False
    mock.auto_add_only_relevant_phrase = False
    # Production shape: the DTO is already baked with the base resolve CPO.
    mock.target_pay_for_order = 100.0
    mock.resolve_cpo = 100.0
    mock.white_list_mode = WhiteListMode.ABOVE_MIN_RATING
    mock.promo_fraction = promo_fraction
    mock.adv_setting = adv_setting
    return mock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keyword_above_target_gate_uses_effective_overlay_max_not_base_adv_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CPO между base max и overlay max: overlay → GOOD, base-only → BAD."""
    adv_setting = _fake_adv_setting(max_pay=100.0)
    complex_adv = _complex_adv_with_promo(adv_setting, promo_fraction=Decimal("0.5"))
    # f=0.5 → M=2 → effective max=200 при base max=100.
    _conv_for_pay_150 = 100_000 / 150_000_000
    pre_kw = PreCalculatedKeywordFactory(
        adv_id=adv_setting.adv_id,
        keyword_setting__hard_status=HardStatus.WHITELIST,
        keyword_setting__text="overlay_gate_kw",
        keyword_setting__target_place=20,
        cluster_stat__norm_query="overlay_gate_kw",
        cluster_stat__position=5.0,
        cluster_stat__cpm=100.0,
        cluster_stat__views=1000,
        cluster_stat__clicks=100,
        cluster_stat__conv_views_to_orders=_conv_for_pay_150,
    )
    monkeypatch.setattr(
        "app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager.PlanFactReader.get_latest_plan_fact",
        AsyncMock(return_value=_plan_fact_summary(fact_predict_orders=5.0)),
    )
    updates: dict[str, AboveTargetCooldownEntry | None] = {}
    fixed_now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    result = await CalculatedKeywordsManager._CalculatedKeywordsManager__get_calculated_keywords(
        complex_adv,
        [pre_kw],
        min_bid_for_adv=100,
        cooldown_map={},
        cooldown_updates=updates,
        now=fixed_now,
    )
    assert result[0].status == KeywordStatus.GOOD
    assert result[0].reason == KeywordStatusReason.WHITE_LIST
    assert result[0].target_pay_for_order == 200.0
    assert result[0].above_target_min_bid is not None
    assert result[0].above_target_min_bid.resolved_target_cost == 200.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_telegram_menu_cost_activity_path_must_match_overlay_when_fraction_on_complex_adv(
) -> None:
    """AdvSettingMenu передаёт ``complex_adv=`` в metrics (не inspect-стек).

    Bare-вызов без аргумента и inspect-костыль покрыты в
    ``test_auto_campaign_cost_activity_overlay.py`` — этот тест не должен
    иметь локаль ``complex_adv`` рядом с вызовом без аргумента.
    """
    adv = _fake_adv_setting(max_pay=100.0)
    overlay_carrier = SimpleNamespace(promo_fraction=Decimal("0.5"))
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(return_value=_plan_fact_summary())
    )
    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ):
        menu_metrics = await get_auto_campaign_cost_activity_metrics(
            adv,
            plan_fact_reader=reader,
            complex_adv=overlay_carrier,
        )
    assert menu_metrics.target_cost == 200.0
    assert menu_metrics.is_active is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_auto_campaign_active_accepts_complex_adv_for_overlay_fraction(
) -> None:
    """Wrapper должен принимать complex_adv (calculated_keywords / telegram paths)."""
    import inspect

    adv = _fake_adv_setting(max_pay=100.0)
    overlay_carrier = SimpleNamespace(promo_fraction=Decimal("0.5"))
    reader = SimpleNamespace(
        get_latest_plan_fact=AsyncMock(return_value=_plan_fact_summary())
    )
    params = inspect.signature(is_auto_campaign_active).parameters
    assert "complex_adv" in params
    with patch(
        "app.shared.domains.wb.utils.auto_campaign_cost_activity.full_wb_adv_stat.get_additional_cost_per_order_for_adv",
        new=AsyncMock(return_value=150.0),
    ):
        result = await is_auto_campaign_active(
            adv,
            plan_fact_reader=reader,
            complex_adv=overlay_carrier,
        )
    assert result is True
