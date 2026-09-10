"""Unit: promo ledger windows, UPD filter, leftover lookback overlay usable."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList

from app.modules.auto_budget_manager.promo_ledger import (
    PROMO_LOOKBACK_DAYS,
    iter_promo_upd_items,
    load_campaign_ledgers,
    load_oldest_live_allocation_at,
)
from app.modules.auto_budget_manager.promo_state_service import (
    _UPD_LOOKBACK_DAYS,
    _resolve_upd_from_date,
)
from app.modules.auto_budget_manager.redis_promo_state_manager import (
    CachedCampaignPromoState,
    CachedShopPromoState,
)
from app.shared.domains.wb.utils.promo_accounting import resolve_promo_availability
from app.shared.domains.wb.utils.promo_overlay import fraction_from_cached_state


@pytest.mark.unit
def test_allocation_and_spend_windows_are_aligned() -> None:
    """Приход и расход должны учитываться за одно окно (иначе remaining завышен)."""
    assert _UPD_LOOKBACK_DAYS == PROMO_LOOKBACK_DAYS


@pytest.mark.unit
def test_upd_ingest_uses_recovery_window_then_daily_overlap() -> None:
    """Первый ingest читает 90 дней, следующий — день watermark без потери строк."""
    now = datetime(2026, 9, 7, 10, tzinfo=timezone.utc)

    assert _resolve_upd_from_date(now=now, last_successful_ingest_at=None) == (
        now - timedelta(days=PROMO_LOOKBACK_DAYS)
    ).date()
    assert _resolve_upd_from_date(
        now=now,
        last_successful_ingest_at=datetime(2026, 9, 6, 23, 59, tzinfo=timezone.utc),
    ) == datetime(2026, 9, 6, tzinfo=timezone.utc).date()


@pytest.mark.unit
def test_iter_promo_upd_items_keeps_only_cashback() -> None:
    items = [
        SimpleNamespace(
            advert_id=1,
            upd_num=10,
            upd_time="2026-01-01T00:00:00Z",
            upd_sum=50,
            payment_type="Keshbek",
        ),
        SimpleNamespace(
            advert_id=1,
            upd_num=11,
            upd_time="2026-01-02T00:00:00Z",
            upd_sum=80,
            payment_type="Balans",
        ),
        {"advertId": 2, "updNum": 12, "updTime": "t", "updSum": 30, "paymentType": "Кэшбэк"},
    ]
    parsed = iter_promo_upd_items(items)
    assert len(parsed) == 2
    assert parsed[0]["advert_id"] == 1
    assert parsed[0]["upd_sum"] == 50
    assert parsed[1]["advert_id"] == 2


@pytest.mark.unit
def test_iter_promo_upd_items_distinguishes_duplicate_rows_without_upd_num() -> None:
    """Два одинаковых WB payload без updNum не должны схлопнуться в один ключ."""
    items = [
        {
            "advertId": 2,
            "updTime": "2026-01-02T00:00:00Z",
            "updSum": 30,
            "paymentType": "Кэшбэк",
        },
        {
            "advertId": 2,
            "updTime": "2026-01-02T00:00:00Z",
            "updSum": 30,
            "paymentType": "Кэшбэк",
        },
    ]

    parsed = iter_promo_upd_items(items)

    assert [row["_missing_upd_index"] for row in parsed] == [0, 1]


def _clause_literal(value: object) -> object:
    """Unwrap SQLAlchemy bind/literal to a Python value."""
    effective = getattr(value, "effective_value", None)
    if effective is not None:
        return effective
    if hasattr(value, "value"):
        return value.value
    return value


def _column_key(expr: object) -> str | None:
    """Имя колонки из SQLAlchemy ColumnElement."""
    key = getattr(expr, "key", None)
    if isinstance(key, str):
        return key
    name = getattr(expr, "name", None)
    if isinstance(name, str):
        return name
    return None


def _created_at_ge_cutoff(where: object) -> datetime | None:
    """Вернуть cutoff, если ``created_at >=`` — top-level AND-конъюнкт (как в текущем SQL)."""
    if where is None:
        return None
    if isinstance(where, BooleanClauseList) and where.operator is operators.and_:
        conjuncts: list[object] = list(where.clauses)
    else:
        conjuncts = [where]
    for clause in conjuncts:
        if not isinstance(clause, BinaryExpression):
            continue
        if clause.operator is not operators.ge:
            continue
        if _column_key(clause.left) != "created_at":
            continue
        raw = _clause_literal(clause.right)
        if isinstance(raw, datetime):
            return raw
    return None


class _FakeScalars:
    """SQLAlchemy ``Result.scalars()`` stand-in."""

    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return list(self._rows)


class _FakeResult:
    """Минимальный result для ``session.execute`` → ``scalars().all()``."""

    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._rows)


class _LookbackHonoringSession:
    """PG-like session: применяет ``created_at >= cutoff`` из реального statement.

    Не подменяет ``load_campaign_ledgers`` / ``load_success_tranches``: cutoff
    берётся из SQL, который строит production. Spend-запросы пустые.
    """

    def __init__(self, topup_rows: list[object]) -> None:
        self._topup_rows = topup_rows

    async def execute(self, stmt: object) -> _FakeResult:
        sql = str(stmt).lower()
        if "wbcampaignpromospend" in sql:
            return _FakeResult([])
        if "wbautobudgettopup" not in sql:
            return _FakeResult([])
        rows = list(self._topup_rows)
        cutoff = _created_at_ge_cutoff(getattr(stmt, "whereclause", None))
        if cutoff is not None:
            rows = [
                row
                for row in rows
                if getattr(row, "created_at", None) is not None
                and row.created_at >= cutoff
            ]
        return _FakeResult(rows)


def _leftover_topup_row(
    *,
    advert_id: int,
    created_at: datetime,
    expires_at: datetime,
    promo_amount: int,
) -> SimpleNamespace:
    """In-memory success-tranche с shape полей, которые читает ``load_success_tranches``."""
    return SimpleNamespace(
        id=101,
        adv_id=advert_id,
        promo_amount=promo_amount,
        amount=1000,
        created_at=created_at,
        promo_expires_at=expires_at,
        budget_after=1000,
        status="success",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_leftover_older_than_lookback_keeps_campaign_usable_when_pool_zero() -> None:
    """Живой leftover старше 90d при pool=0 не должен AND-stop overlay.

    Regression ROOT-001: ``load_campaign_ledgers`` режет allocation
    ``created_at >= now-90d`` → remaining=0 → campaign_usable=false → overlay OFF,
    хотя leftover remaining>0 и не expired.
    """
    now = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)
    advert_id = 4242
    leftover_created = now - timedelta(days=PROMO_LOOKBACK_DAYS + 1)
    leftover_expires = now + timedelta(days=21)
    assert leftover_created < now - timedelta(days=PROMO_LOOKBACK_DAYS)

    session = _LookbackHonoringSession(
        [
            _leftover_topup_row(
                advert_id=advert_id,
                created_at=leftover_created,
                expires_at=leftover_expires,
                promo_amount=250,
            )
        ]
    )
    ledgers = await load_campaign_ledgers(session, [advert_id], now=now)
    availability = resolve_promo_availability(
        pool_response=SimpleNamespace(cashbacks=[]),
        topup_amount=1000,
        campaign_ledger=ledgers[advert_id],
        now=now,
    )
    campaign = CachedCampaignPromoState(
        remaining=availability.campaign_remaining,
        fraction=availability.campaign_fraction,
        expires_at=(
            availability.campaign_expires_at.isoformat()
            if availability.campaign_expires_at is not None
            else None
        ),
        usable=availability.usable,
        effective_fraction=availability.fraction,
        pool_usable=availability.pool_usable,
        campaign_usable=availability.campaign_usable,
    )
    overlay_state = CachedShopPromoState(
        updated_at=datetime.now(timezone.utc),
        topup_amount=1000,
        pool_usable=False,
        pool_amount=0,
        pool_fraction=Decimal("0"),
        campaigns={advert_id: campaign},
    )

    assert availability.campaign_usable is True
    assert availability.usable is True
    assert availability.stop_on_exhaustion is False
    assert campaign.usable is True
    assert fraction_from_cached_state(overlay_state, advert_id) > Decimal("0")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_oldest_live_allocation_uses_real_success_tranche_query() -> None:
    """Recovery boundary comes from non-expired success rows, not test input alone."""
    now = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)
    session = _LookbackHonoringSession(
        [
            _leftover_topup_row(
                advert_id=4242,
                created_at=now - timedelta(days=180),
                expires_at=now + timedelta(days=21),
                promo_amount=250,
            ),
            _leftover_topup_row(
                advert_id=4242,
                created_at=now - timedelta(days=200),
                expires_at=now - timedelta(days=1),
                promo_amount=250,
            ),
        ]
    )

    oldest = await load_oldest_live_allocation_at(session, [4242], now=now)

    assert oldest == now - timedelta(days=180)
