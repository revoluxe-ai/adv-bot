"""PBH-004 RED: empty latch + started legs → preview must not bill 0.

Invariant: preview with latch read MUST use max(latch_read, instant) per slot
without persisting to Redis. Empty Redis must not hide currently started legs.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest
from fakeredis.aioredis import FakeRedis

from app.modules.billing.leg_latch import LegLatchManager
from app.modules.billing.leg_metering import (
    compute_anchor_billables,
    resolve_metering_anchors,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _adv(
    *,
    id_: int,
    adv_id: int | None,
    bot_active: bool = False,
    search_adv_id: int | None = None,
    active_status: str = "paused",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id_,
        adv_id=adv_id,
        bot_active=bot_active,
        search_adv_id=search_adv_id,
        active_status=active_status,
    )


async def test_empty_latch_started_legs_match_instant_not_zero() -> None:
    """PBH-004 / TEST-PBH-004-001: empty latch + started anchor+search → total >= 1.0."""
    utc_day = date(2024, 6, 16)
    latch = LegLatchManager(FakeRedis())

    advs = [
        _adv(
            id_=1,
            adv_id=100,
            bot_active=True,
            search_adv_id=200,
            active_status="started",
        ),
        _adv(id_=2, adv_id=200, bot_active=False, active_status="started"),
    ]
    anchors = resolve_metering_anchors(advs)

    billables = await compute_anchor_billables(
        anchors,
        latch=latch,
        utc_date=utc_day,
    )

    assert len(billables) == 1
    assert billables[0].auto_weight == pytest.approx(0.5)
    assert billables[0].search_weight == pytest.approx(0.5)
    assert billables[0].total >= 1.0
