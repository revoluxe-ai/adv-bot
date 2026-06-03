"""Unit: V3TickReport Redis roundtrip."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3PhaseStats,
    V3TickReportSnapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report_redis import (
    V3TickReportRedisCache,
    persist_v3_tick_report,
)


@pytest.mark.unit
def test_snapshot_json_roundtrip_fields() -> None:
    snap = V3TickReportSnapshot(
        tick_at=datetime(2026, 6, 3, 10, 30, 0, tzinfo=UTC),
        adv_id=42,
        adv_name="RK",
        campaign_mode="NORMAL",
        total_keywords=100,
        operable_keywords=80,
        phases=[
            V3PhaseStats(
                phase_id="filter",
                title_ru="filter",
                extra={"total": 100, "operable": 80},
            )
        ],
        aggression_score_before=10,
        aggression_score_after=12,
        aggression_delta=2,
    )
    raw = snap.model_dump_json()
    restored = V3TickReportSnapshot.model_validate_json(raw)
    assert restored.adv_id == 42
    assert restored.aggression_delta == 2
    assert restored.phases[0].phase_id == "filter"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_cache_set_get() -> None:
    adv = MagicMock()
    adv.adv_id = 777
    snap = V3TickReportSnapshot(
        tick_at=datetime(2026, 6, 3, 10, 0, 0, tzinfo=UTC),
        adv_id=777,
        campaign_mode="NO_DATA",
    )
    cache = V3TickReportRedisCache(adv)
    assert cache.key == "V3TickReport:777"
    mock_client = AsyncMock()
    stored: dict[str, str] = {}

    async def _set(key: str, val: str, ex: int | None = None) -> None:
        _ = key, ex
        stored["v"] = val

    async def _get(key: str) -> str | None:
        _ = key
        return stored.get("v")

    mock_client.set = _set
    mock_client.get = _get
    with patch.object(V3TickReportRedisCache, "client", mock_client):
        await cache.set(snap)
        got = await cache.get()
    assert got is not None
    assert got.campaign_mode == "NO_DATA"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_v3_tick_report_delegates() -> None:
    adv = MagicMock()
    adv.adv_id = 1
    snap = V3TickReportSnapshot(
        tick_at=datetime(2026, 1, 1, tzinfo=UTC),
        adv_id=1,
        campaign_mode="NORMAL",
    )
    with patch.object(
        V3TickReportRedisCache,
        "set",
        new_callable=AsyncMock,
    ) as mock_set:
        await persist_v3_tick_report(adv, snap)
        mock_set.assert_awaited_once()
