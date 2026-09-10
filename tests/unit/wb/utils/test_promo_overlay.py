"""Unit: overlay fraction OR across auto/search and stale conservative fallback."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.auto_budget_manager.redis_promo_state_manager import (
    CachedCampaignPromoState,
    CachedShopPromoState,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.shared.domains.wb.utils.promo_overlay import (
    apply_cached_state_to_complex_adv,
    fraction_from_cached_state,
)


def _campaign(*, remaining: int, fraction: Decimal, usable: bool) -> CachedCampaignPromoState:
    return CachedCampaignPromoState(
        remaining=remaining,
        fraction=fraction,
        expires_at=None,
        usable=usable,
        effective_fraction=fraction,
        pool_usable=False,
        campaign_usable=usable,
    )


@pytest.mark.unit
def test_fraction_uses_max_of_auto_and_search() -> None:
    state = CachedShopPromoState(
        updated_at=datetime.now(timezone.utc),
        topup_amount=1000,
        pool_usable=False,
        pool_amount=0,
        pool_fraction=Decimal("0"),
        campaigns={
            11: _campaign(remaining=0, fraction=Decimal("0"), usable=False),
            22: _campaign(remaining=200, fraction=Decimal("0.2"), usable=True),
        },
    )
    assert fraction_from_cached_state(state, 11) == Decimal("0")
    assert fraction_from_cached_state(state, 11, 22) == Decimal("0.2")


@pytest.mark.unit
def test_stale_cache_is_conservative_zero() -> None:
    state = CachedShopPromoState(
        updated_at=datetime.now(timezone.utc) - timedelta(hours=1),
        topup_amount=1000,
        pool_usable=True,
        pool_amount=500,
        pool_fraction=Decimal("0.5"),
        campaigns={
            11: _campaign(remaining=500, fraction=Decimal("0.5"), usable=True),
        },
    )
    assert state.is_stale is True
    assert fraction_from_cached_state(state, 11) == Decimal("0")
    assert fraction_from_cached_state(None, 11) == Decimal("0")


@pytest.mark.unit
def test_untrusted_cache_is_conservative_zero() -> None:
    """Свежий snapshot после failed refresh не может поднять overlay."""
    state = CachedShopPromoState(
        updated_at=datetime.now(timezone.utc),
        topup_amount=1000,
        pool_usable=True,
        pool_amount=500,
        pool_fraction=Decimal("0.5"),
        campaigns={
            11: _campaign(remaining=500, fraction=Decimal("0.5"), usable=True),
        },
        overlay_trusted=False,
    )

    assert state.is_stale is False
    assert fraction_from_cached_state(state, 11) == Decimal("0")


@pytest.mark.unit
def test_apply_cached_state_updates_existing_complex_adv_in_same_tick() -> None:
    """Fresh Redis state must reach DTOs already built by the watchdog."""
    state = CachedShopPromoState(
        updated_at=datetime.now(timezone.utc),
        topup_amount=1000,
        pool_usable=False,
        pool_amount=0,
        pool_fraction=Decimal("0"),
        campaigns={
            11: _campaign(remaining=500, fraction=Decimal("0.5"), usable=True),
        },
    )
    adv_setting = SimpleNamespace(
        adv_id=11,
        search_adv_id=None,
        raise_plan_on_promobonuses=True,
        plan_for_sales_for_day=10,
        target_price_for_order=50.0,
        max_price_for_order=100.0,
        auto_budget_daily_limit=1000,
        search_auto_budget_daily_limit=0,
        common_budget_daily_limit=None,
    )
    complex_adv = ComplexAdv(
        adv_setting=adv_setting,
        target_pay_for_order=100.0,
        resolve_cpo=100.0,
    )

    overlay = apply_cached_state_to_complex_adv(complex_adv, state)

    assert overlay.active is True
    assert complex_adv.promo_fraction == Decimal("0.5")
    assert complex_adv.promo_multiplier == Decimal("2.000000")
    assert complex_adv.effective_promo_plan is overlay
    assert complex_adv.target_pay_for_order == 200.0
    assert complex_adv.resolve_cpo == 200.0


@pytest.mark.unit
def test_apply_inactive_overlay_restores_base_resolve_cpo() -> None:
    """При снятии promo baked CPO возвращается к базовому max CPO."""
    state = CachedShopPromoState(
        updated_at=datetime.now(timezone.utc),
        topup_amount=1000,
        pool_usable=False,
        pool_amount=0,
        pool_fraction=Decimal("0"),
        campaigns={
            11: _campaign(remaining=0, fraction=Decimal("0"), usable=False),
        },
    )
    adv_setting = SimpleNamespace(
        adv_id=11,
        search_adv_id=None,
        raise_plan_on_promobonuses=True,
        plan_for_sales_for_day=10,
        target_price_for_order=50.0,
        max_price_for_order=100.0,
        auto_budget_daily_limit=1000,
        search_auto_budget_daily_limit=0,
        common_budget_daily_limit=None,
    )
    complex_adv = ComplexAdv(
        adv_setting=adv_setting,
        target_pay_for_order=200.0,
        resolve_cpo=200.0,
    )

    apply_cached_state_to_complex_adv(complex_adv, state)

    assert complex_adv.target_pay_for_order == 100.0
    assert complex_adv.resolve_cpo == 100.0
