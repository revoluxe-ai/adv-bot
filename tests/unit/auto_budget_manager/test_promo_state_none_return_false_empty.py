"""Unit: a None pool response creates an untrusted Redis snapshot.

Проверяется durable trust marker после ``get_campaign_balance=None``.
Trust marker сохраняет консервативный ``M=1`` даже при свежем timestamp.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.modules.auto_budget_manager.promo_state_service import PromoStateService
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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_marks_snapshot_untrusted_when_balance_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """None от live pool не может оставить доверенным raised overlay."""
    redis = _CapturingPromoRedis()
    wb_modifier = SimpleNamespace(
        get_campaign_balance=AsyncMock(return_value=None),
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
