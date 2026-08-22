"""Контекст latch-backed tariff preview (parity с shop_menu и billing charge).

Единая точка резолва ``leg_latch`` + ``utc_date`` для read-only превью тарифа.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.modules.billing.leg_latch import LegLatchManager
from app.modules.billing.redis_manager import RedisManager


def get_billing_redis_manager() -> RedisManager:
    """Billing Redis manager для preview latch (DI или lazy fallback без контекста)."""
    try:
        from app.modules.billing.di import BillingContainer

        return BillingContainer.redis_manager()
    except Exception:
        from app.modules.cluster_bids_redis.redis_client_provider import (
            get_redis_client,
        )

        return RedisManager(redis_client=get_redis_client())


def resolve_tariff_preview_latch_context(
    *,
    leg_latch: LegLatchManager | None = None,
    utc_date: date | None = None,
) -> tuple[LegLatchManager, date]:
    """Вернуть latch и UTC-день для latch-backed preview (mirror shop_menu)."""
    if leg_latch is None:
        leg_latch = get_billing_redis_manager().leg_latch()
    if utc_date is None:
        utc_date = datetime.now(timezone.utc).date()
    return leg_latch, utc_date
