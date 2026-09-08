"""Unit: FEFO remaining, OR-active/AND-stop, payment type filter."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.shared.domains.wb.utils.promo_accounting import (
    CampaignPromoLedger,
    PromoAllocationTranche,
    PromoSpendRow,
    apply_spend_fefo,
    campaign_ledger_from_rows,
    is_promo_payment_type,
    resolve_promo_availability,
    spend_fingerprint,
)
from app.shared.domains.wb.utils.promo_plan_multiplier import promo_multiplier


def _dt(days: int) -> datetime:
    return datetime(2026, 9, 6, tzinfo=timezone.utc) + timedelta(days=days)


NOW = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)


@pytest.mark.unit
def test_payment_type_keshbek_and_cyrillic() -> None:
    assert is_promo_payment_type("Keshbek")
    assert is_promo_payment_type(" kEsHbEk ")
    assert is_promo_payment_type("Кэшбэк")
    assert not is_promo_payment_type("cashback")
    assert not is_promo_payment_type("кешбек")
    assert not is_promo_payment_type("Карта")
    assert not is_promo_payment_type(None)


@pytest.mark.unit
def test_fefo_spend_and_expired_tranche_unusable() -> None:
    """Spend обязан бить live leftover, не expired leftover; remaining 150."""
    tranches = [
        PromoAllocationTranche(
            topup_id=1,
            advert_id=10,
            promo_amount=300,
            amount=1000,
            expires_at=_dt(-1),
            created_at=_dt(-10),
            budget_after=1000,
        ),
        PromoAllocationTranche(
            topup_id=2,
            advert_id=10,
            promo_amount=200,
            amount=1000,
            expires_at=_dt(5),
            created_at=_dt(-2),
            budget_after=1200,
        ),
    ]
    spends = [PromoSpendRow("fp", 10, 50, NOW)]
    allocated, spent, remaining, expires_at, _budget = apply_spend_fefo(
        tranches, spends, now=NOW
    )
    assert allocated == 500
    assert spent == 50
    assert remaining == 150
    assert expires_at == _dt(5)


@pytest.mark.unit
def test_fefo_spend_hits_live_leftover_not_expired() -> None:
    """Spend 50 при expired leftover 300 + live leftover 200 даёт remaining 150.

    FEFO обязан списывать spend с live leftover. Expired leftover не usable
    и не должен поглощать spend (иначе remaining раздувается до 200).
    """
    tranches = [
        PromoAllocationTranche(
            topup_id=1,
            advert_id=10,
            promo_amount=300,
            amount=1000,
            expires_at=_dt(-1),
            created_at=_dt(-10),
            budget_after=1000,
        ),
        PromoAllocationTranche(
            topup_id=2,
            advert_id=10,
            promo_amount=200,
            amount=1000,
            expires_at=_dt(5),
            created_at=_dt(-2),
            budget_after=1200,
        ),
    ]
    spends = [PromoSpendRow("fp", 10, 50, NOW)]
    allocated, spent, remaining, expires_at, _budget = apply_spend_fefo(
        tranches, spends, now=NOW
    )
    assert allocated == 500
    assert spent == 50
    assert remaining == 150
    assert expires_at == _dt(5)


@pytest.mark.unit
def test_or_active_and_stop() -> None:
    ledger = CampaignPromoLedger(
        advert_id=1,
        allocated=200,
        spent=0,
        remaining=200,
        expires_at=_dt(3),
        reference_budget=1000,
        fraction=Decimal("0.2"),
        usable=True,
    )
    pool = SimpleNamespace(
        cashbacks=[
            {"sum": 0, "percent": 50, "expiration_date": "2026-12-01T00:00:00+00:00"}
        ]
    )
    availability = resolve_promo_availability(
        pool_response=pool,
        topup_amount=1000,
        campaign_ledger=ledger,
        now=NOW,
    )
    assert availability.usable is True
    assert availability.stop_on_exhaustion is False
    assert availability.fraction == Decimal("0.2")

    empty = resolve_promo_availability(
        pool_response=SimpleNamespace(cashbacks=[]),
        topup_amount=1000,
        campaign_ledger=None,
        now=NOW,
    )
    assert empty.usable is False
    assert empty.stop_on_exhaustion is True
    assert empty.fraction == Decimal("0")


@pytest.mark.unit
def test_pool_is_unusable_when_ordinary_remainder_is_unfunded() -> None:
    """Пакет не активирует pool без ordinary-покрытия остатка top-up."""
    pool = SimpleNamespace(
        balance=799,
        net=0,
        bonus=0,
        cashbacks=[
            {
                "sum": 200,
                "percent": 20,
                "expiration_date": "2026-12-01T00:00:00+00:00",
            }
        ],
    )

    availability = resolve_promo_availability(
        pool_response=pool,
        topup_amount=1000,
        campaign_ledger=None,
        now=NOW,
    )

    assert availability.pool_usable is False
    assert availability.pool_amount == 0
    assert availability.pool_fraction == Decimal("0")
    assert availability.usable is False


@pytest.mark.unit
def test_pool_is_usable_when_ordinary_remainder_is_funded() -> None:
    """Pool использует cashback 200 и ordinary remainder 800."""
    pool = SimpleNamespace(
        balance=800,
        net=0,
        bonus=0,
        cashbacks=[
            {
                "sum": 200,
                "percent": 20,
                "expiration_date": "2026-12-01T00:00:00+00:00",
            }
        ],
    )

    availability = resolve_promo_availability(
        pool_response=pool,
        topup_amount=1000,
        campaign_ledger=None,
        now=NOW,
    )

    assert availability.pool_usable is True
    assert availability.pool_amount == 200
    assert availability.pool_fraction == Decimal("0.2")
    assert availability.fraction == Decimal("0.2")


@pytest.mark.unit
def test_campaign_leftover_stays_active_when_pool_pairing_fails() -> None:
    """Campaign leftover сохраняет OR-active при неуспешном pool pairing."""
    pool = SimpleNamespace(
        balance=799,
        net=0,
        bonus=0,
        cashbacks=[
            {
                "sum": 200,
                "percent": 20,
                "expiration_date": "2026-12-01T00:00:00+00:00",
            }
        ],
    )
    ledger = CampaignPromoLedger(
        advert_id=1,
        allocated=200,
        spent=0,
        remaining=200,
        expires_at=_dt(3),
        reference_budget=1000,
        fraction=Decimal("0.2"),
        usable=True,
    )

    availability = resolve_promo_availability(
        pool_response=pool,
        topup_amount=1000,
        campaign_ledger=ledger,
        now=NOW,
    )

    assert availability.pool_usable is False
    assert availability.campaign_usable is True
    assert availability.usable is True
    assert availability.stop_on_exhaustion is False


@pytest.mark.unit
def test_campaign_ledger_fraction_uses_remaining_not_ceiling() -> None:
    tranche = PromoAllocationTranche(
        topup_id=1,
        advert_id=7,
        promo_amount=200,
        amount=1000,
        expires_at=_dt(4),
        created_at=_dt(-1),
        budget_after=1000,
    )
    ledger = campaign_ledger_from_rows(
        7,
        [tranche],
        [],
        now=NOW,
        campaign_budget_total=1000,
    )
    assert ledger.remaining == 200
    assert ledger.fraction == Decimal("0.2")


@pytest.mark.unit
def test_campaign_ledger_leftover_fraction_uses_tranche_amount_not_budget_after() -> None:
    """Leftover remaining 200 / amount 1000 is f=0.2 (M=1.25), not 200/budget_after.

    Existing test_campaign_ledger_fraction_uses_remaining_not_ceiling uses
    amount=budget_after=campaign_budget_total=1000 and cannot catch collapse
    when leftover << campaign ceiling. This vector keeps amount=1000 and
    sets budget_after=campaign_budget_total=12000.
    """
    tranche = PromoAllocationTranche(
        topup_id=1,
        advert_id=7,
        promo_amount=200,
        amount=1000,
        expires_at=_dt(4),
        created_at=_dt(-1),
        budget_after=12000,
    )
    ledger = campaign_ledger_from_rows(
        7,
        [tranche],
        [],
        now=NOW,
        campaign_budget_total=12000,
    )
    assert ledger.remaining == 200
    assert ledger.fraction == Decimal("0.2")
    assert promo_multiplier(ledger.fraction) == Decimal("1.250000")


@pytest.mark.unit
def test_campaign_ledger_multi_tranche_fraction_uses_package_percent_not_leftover_over_last_tranche() -> (
    None
):
    """Два success top-up 1000 с promo 500 каждый, spend 0.

    Неверно: summed leftover 1000 / last tranche.amount 1000 → f≈1 → M ~1e6.
    Верно: package percent 500/1000 = 50% → f=0.5, multiplier=2 (не leftover mix).
    """
    tranches = [
        PromoAllocationTranche(
            topup_id=1,
            advert_id=10,
            promo_amount=500,
            amount=1000,
            expires_at=_dt(5),
            created_at=_dt(-2),
            budget_after=1000,
        ),
        PromoAllocationTranche(
            topup_id=2,
            advert_id=10,
            promo_amount=500,
            amount=1000,
            expires_at=_dt(10),
            created_at=_dt(-1),
            budget_after=2000,
        ),
    ]
    ledger = campaign_ledger_from_rows(10, tranches, [], now=NOW)
    assert ledger.remaining == 1000
    assert ledger.fraction == Decimal("0.5")
    assert promo_multiplier(ledger.fraction) == Decimal("2.000000")
    assert ledger.fraction < Decimal("0.9")


@pytest.mark.unit
def test_spend_fingerprint_stable() -> None:
    first = spend_fingerprint(
        advert_id=1,
        upd_num=10,
        upd_time="2026-01-01",
        upd_sum=50,
        payment_type="Keshbek",
    )
    second = spend_fingerprint(
        advert_id=1,
        upd_num=10,
        upd_time="2026-01-01",
        upd_sum=50,
        payment_type="Keshbek",
    )
    assert first == second
    assert "1|10|" in first


@pytest.mark.unit
def test_spend_fingerprint_distinguishes_missing_upd_num_duplicates() -> None:
    """Fallback index сохраняет две одинаковые строки без updNum отдельно."""
    first = spend_fingerprint(
        advert_id=1,
        upd_num=None,
        upd_time="2026-01-01",
        upd_sum=50,
        payment_type="Кэшбэк",
        duplicate_index=0,
    )
    second = spend_fingerprint(
        advert_id=1,
        upd_num=None,
        upd_time="2026-01-01",
        upd_sum=50,
        payment_type="Кэшбэк",
        duplicate_index=1,
    )

    assert first != second
    assert first == spend_fingerprint(
        advert_id=1,
        upd_num=None,
        upd_time="2026-01-01",
        upd_sum=50,
        payment_type="Кэшбэк",
        duplicate_index=0,
    )
