"""Unit: failed promo refreshes publish an untrusted Redis snapshot."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.modules.auto_budget_manager.promo_state_service import (
    UPD_API_MAX_WINDOW_DAYS,
    PromoStateService,
    _iter_upd_date_ranges,
)
from app.modules.auto_budget_manager.redis_promo_state_manager import (
    CachedCampaignPromoState,
    CachedShopPromoState,
)
from app.shared.domains.wb.utils.promo_overlay import fraction_from_cached_state


class _CapturingPromoRedis:
    """Test double RedisPromoStateManager: фиксирует set(), без реального Redis."""

    def __init__(self) -> None:
        self.set_calls: list[dict[str, Any]] = []
        self.get_state: CachedShopPromoState | None = None

    async def get(self, shop_id: str | int) -> CachedShopPromoState | None:
        """Вернуть заранее заданный cache miss/hit."""
        _ = shop_id
        return self.get_state

    async def set(self, shop_id: str | int, **kwargs: Any) -> None:
        """Зафиксировать derived snapshot, который production пытается записать."""
        self.set_calls.append({"shop_id": shop_id, **kwargs})


class _FakeSessionMaker:
    """Async CM, совместимый с `async with sm(read_only=...) as session:`."""

    def __call__(self, read_only: bool = False) -> "_FakeSessionMaker":
        _ = read_only
        return self

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *args: object) -> None:
        return None


def _snapshot_from_set_call(call: dict[str, Any]) -> CachedShopPromoState:
    """Собрать CachedShopPromoState из kwargs RedisPromoStateManager.set."""
    campaigns_raw = call.get("campaigns") or {}
    campaigns: dict[int, CachedCampaignPromoState] = {}
    if isinstance(campaigns_raw, dict):
        for adv_id, state in campaigns_raw.items():
            campaigns[int(adv_id)] = state
    return CachedShopPromoState(
        updated_at=datetime.now(timezone.utc),
        topup_amount=int(call.get("topup_amount") or 0),
        pool_usable=bool(call.get("pool_usable")),
        pool_amount=int(call.get("pool_amount") or 0),
        pool_fraction=call.get("pool_fraction") or Decimal("0"),
        campaigns=campaigns,
        upd_ingested_at=call.get("upd_ingested_at"),
        upd_coverage_from=call.get("upd_coverage_from"),
        overlay_trusted=bool(call.get("overlay_trusted", True)),
    )


def _assert_windows_contiguous(
    windows: list[tuple[date, date]],
    *,
    first: date,
    last: date,
) -> None:
    """Проверить покрытие диапазона без дыр и перекрытий."""
    assert windows[0][0] == first
    assert windows[-1][1] == last
    assert all(
        previous_end + timedelta(days=1) == current_start
        for (_, previous_end), (current_start, _) in zip(windows, windows[1:])
    )
    assert all(
        (end - start).days + 1 <= UPD_API_MAX_WINDOW_DAYS for start, end in windows
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_marks_snapshot_untrusted_when_balance_fetch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Сбой live pool инвалидирует прежний raised overlay и сохраняет cursors."""
    redis = _CapturingPromoRedis()
    redis.get_state = CachedShopPromoState(
        updated_at=datetime.now(timezone.utc),
        topup_amount=1000,
        pool_usable=True,
        pool_amount=500,
        pool_fraction=Decimal("0.5"),
        campaigns={
            101: CachedCampaignPromoState(
                remaining=500,
                fraction=Decimal("0.5"),
                expires_at=None,
                usable=True,
                effective_fraction=Decimal("0.5"),
                pool_usable=True,
                campaign_usable=False,
            )
        },
        upd_ingested_at=datetime.now(timezone.utc) - timedelta(hours=1),
        upd_coverage_from=datetime.now(timezone.utc) - timedelta(days=1),
    )
    wb_modifier = SimpleNamespace(
        get_campaign_balance=AsyncMock(
            side_effect=RuntimeError("WB get_campaign_balance failed")
        ),
        get_costs_history=AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.sm",
        _FakeSessionMaker(),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.ingest_promo_upd_items",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.load_campaign_ledgers",
        AsyncMock(return_value={}),
    )
    adv = SimpleNamespace(
        adv_setting=SimpleNamespace(adv_id=101, search_adv_id=None),
    )
    service = PromoStateService(redis)

    await service.refresh(shop_id="shop-1", advs=[adv], wb_modifier=wb_modifier)

    wb_modifier.get_campaign_balance.assert_awaited()
    assert len(redis.set_calls) == 1
    call = redis.set_calls[0]
    assert call["pool_usable"] is False
    snapshot = _snapshot_from_set_call(call)
    assert snapshot.is_stale is False
    assert snapshot.overlay_trusted is False
    assert fraction_from_cached_state(snapshot, 101) == Decimal("0")


@pytest.mark.unit
def test_upd_recovery_starts_at_oldest_live_allocation() -> None:
    """Initial recovery must cover a live allocation older than 90 days."""
    from app.modules.auto_budget_manager.promo_state_service import (
        _resolve_upd_from_date,
    )

    now = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)
    oldest_live = now - timedelta(days=180)

    assert _resolve_upd_from_date(
        now=now,
        last_successful_ingest_at=None,
        oldest_live_allocation_at=oldest_live,
    ) == oldest_live.date()


@pytest.mark.unit
def test_upd_backfill_90_day_range_splits_into_three_api_windows() -> None:
    """WB /adv/v1/upd accepts at most one month per request."""
    first = date(2026, 6, 12)
    last = date(2026, 9, 9)
    windows = list(_iter_upd_date_ranges(from_date=first, to_date=last))

    assert len(windows) == 3
    assert windows == [
        (date(2026, 6, 12), date(2026, 7, 11)),
        (date(2026, 7, 12), date(2026, 8, 10)),
        (date(2026, 8, 11), date(2026, 9, 9)),
    ]
    _assert_windows_contiguous(windows, first=first, last=last)


@pytest.mark.unit
def test_upd_backfill_short_range_stays_single_window() -> None:
    """Диапазон ≤30 дней не дробится."""
    first = date(2026, 8, 1)
    last = date(2026, 8, 20)
    windows = list(_iter_upd_date_ranges(from_date=first, to_date=last))

    assert windows == [(first, last)]
    _assert_windows_contiguous(windows, first=first, last=last)


@pytest.mark.unit
def test_upd_backfill_exact_30_day_window_stays_single_chunk() -> None:
    """Ровно 30 inclusive дней — одно API-окно."""
    first = date(2026, 1, 1)
    last = date(2026, 1, 30)
    windows = list(_iter_upd_date_ranges(from_date=first, to_date=last))

    assert windows == [(first, last)]
    assert (last - first).days + 1 == UPD_API_MAX_WINDOW_DAYS


@pytest.mark.unit
def test_upd_backfill_31_days_splits_at_month_boundary() -> None:
    """31-й день открывает второе окно без overlap."""
    first = date(2026, 1, 1)
    last = date(2026, 1, 31)
    windows = list(_iter_upd_date_ranges(from_date=first, to_date=last))

    assert windows == [
        (date(2026, 1, 1), date(2026, 1, 30)),
        (date(2026, 1, 31), date(2026, 1, 31)),
    ]
    _assert_windows_contiguous(windows, first=first, last=last)


@pytest.mark.unit
def test_upd_backfill_windows_have_no_gaps() -> None:
    """Длинный backfill покрывается contiguous окнами ≤30 дней."""
    first = date(2026, 1, 1)
    last = date(2026, 9, 8)
    windows = list(_iter_upd_date_ranges(from_date=first, to_date=last))

    _assert_windows_contiguous(windows, first=first, last=last)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_backfills_until_oldest_live_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A legacy Redis snapshot without coverage marker triggers historical backfill."""
    redis = _CapturingPromoRedis()
    now = datetime.now(timezone.utc)
    oldest_live = now - timedelta(days=180)
    wb_modifier = SimpleNamespace(
        get_campaign_balance=AsyncMock(return_value=SimpleNamespace(cashbacks=[])),
        get_costs_history=AsyncMock(return_value=[]),
    )
    sessions = _FakeSessionMaker()
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.sm",
        sessions,
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.load_oldest_live_allocation_at",
        AsyncMock(return_value=oldest_live),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.ingest_promo_upd_items",
        AsyncMock(return_value=0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.load_campaign_ledgers",
        AsyncMock(return_value={}),
    )
    adv = SimpleNamespace(
        adv_setting=SimpleNamespace(adv_id=101, search_adv_id=None),
    )

    await PromoStateService(redis).refresh(
        shop_id="shop-1",
        advs=[adv],
        wb_modifier=wb_modifier,
    )

    calls = wb_modifier.get_costs_history.await_args_list
    assert calls
    assert calls[0].kwargs["from_date"] == oldest_live.date()
    assert calls[-1].kwargs["to_date"] == now.date()
    assert len(calls) >= 6
    assert redis.set_calls[0]["upd_coverage_from"].date() == oldest_live.date()
    assert redis.set_calls[0]["overlay_trusted"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_does_not_publish_snapshot_after_incomplete_upd_ingest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Partial/failed UPD history publishes only an untrusted snapshot."""
    redis = _CapturingPromoRedis()
    wb_modifier = SimpleNamespace(
        get_campaign_balance=AsyncMock(return_value=SimpleNamespace(cashbacks=[])),
        get_costs_history=AsyncMock(side_effect=RuntimeError("UPD unavailable")),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.sm",
        _FakeSessionMaker(),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.load_oldest_live_allocation_at",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.load_campaign_ledgers",
        AsyncMock(return_value={}),
    )
    adv = SimpleNamespace(
        adv_setting=SimpleNamespace(adv_id=101, search_adv_id=None),
    )

    await PromoStateService(redis).refresh(
        shop_id="shop-1",
        advs=[adv],
        wb_modifier=wb_modifier,
    )

    assert len(redis.set_calls) == 1
    snapshot = _snapshot_from_set_call(redis.set_calls[0])
    assert snapshot.overlay_trusted is False
    assert fraction_from_cached_state(snapshot, 101) == Decimal("0")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_does_not_advance_watermark_on_second_window_fetch_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Сбой во 2-м API-окне не двигает upd_ingested_at и coverage."""
    previous_ingest = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
    redis = _CapturingPromoRedis()
    redis.get_state = CachedShopPromoState(
        updated_at=previous_ingest,
        topup_amount=1000,
        pool_usable=True,
        pool_amount=500,
        pool_fraction=Decimal("0.5"),
        campaigns={},
        upd_ingested_at=previous_ingest,
        upd_coverage_from=None,
    )
    now = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    call_count = 0

    async def _get_costs_history(**kwargs: object) -> list[object]:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("WB interval rejected")
        return []

    wb_modifier = SimpleNamespace(
        get_campaign_balance=AsyncMock(return_value=SimpleNamespace(cashbacks=[])),
        get_costs_history=AsyncMock(side_effect=_get_costs_history),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.sm",
        _FakeSessionMaker(),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.datetime",
        SimpleNamespace(
            datetime=datetime,
            timezone=timezone,
            timedelta=timedelta,
            now=lambda tz=None: now,
        ),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.load_oldest_live_allocation_at",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.ingest_promo_upd_items",
        AsyncMock(return_value=0),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.load_campaign_ledgers",
        AsyncMock(return_value={}),
    )
    adv = SimpleNamespace(
        adv_setting=SimpleNamespace(adv_id=101, search_adv_id=None),
    )

    await PromoStateService(redis).refresh(
        shop_id="shop-1",
        advs=[adv],
        wb_modifier=wb_modifier,
    )

    assert call_count == 2
    snapshot = _snapshot_from_set_call(redis.set_calls[0])
    assert snapshot.upd_ingested_at == previous_ingest
    assert snapshot.upd_coverage_from is None
    assert snapshot.overlay_trusted is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_does_not_advance_watermark_on_third_window_ingest_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Сбой PG ingest в 3-м окне не помечает backfill успешным."""
    previous_ingest = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    redis = _CapturingPromoRedis()
    redis.get_state = CachedShopPromoState(
        updated_at=previous_ingest,
        topup_amount=1000,
        pool_usable=True,
        pool_amount=500,
        pool_fraction=Decimal("0.5"),
        campaigns={},
        upd_ingested_at=previous_ingest,
        upd_coverage_from=None,
    )
    now = datetime(2026, 9, 9, 12, 0, tzinfo=timezone.utc)
    ingest_calls = 0

    async def _ingest(*_args: object, **_kwargs: object) -> int:
        nonlocal ingest_calls
        ingest_calls += 1
        if ingest_calls == 3:
            raise RuntimeError("PG ingest failed")
        return 0

    wb_modifier = SimpleNamespace(
        get_campaign_balance=AsyncMock(return_value=SimpleNamespace(cashbacks=[])),
        get_costs_history=AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.sm",
        _FakeSessionMaker(),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.datetime",
        SimpleNamespace(
            datetime=datetime,
            timezone=timezone,
            timedelta=timedelta,
            now=lambda tz=None: now,
        ),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.load_oldest_live_allocation_at",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.ingest_promo_upd_items",
        AsyncMock(side_effect=_ingest),
    )
    monkeypatch.setattr(
        "app.modules.auto_budget_manager.promo_state_service.load_campaign_ledgers",
        AsyncMock(return_value={}),
    )
    adv = SimpleNamespace(
        adv_setting=SimpleNamespace(adv_id=101, search_adv_id=None),
    )

    await PromoStateService(redis).refresh(
        shop_id="shop-1",
        advs=[adv],
        wb_modifier=wb_modifier,
    )

    assert ingest_calls == 3
    assert wb_modifier.get_costs_history.await_count == 3
    snapshot = _snapshot_from_set_call(redis.set_calls[0])
    assert snapshot.upd_ingested_at == previous_ingest
    assert snapshot.upd_coverage_from is None
    assert snapshot.overlay_trusted is False
