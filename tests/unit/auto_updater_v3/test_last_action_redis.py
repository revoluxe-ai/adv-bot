"""Unit-тесты Redis-снимка последнего V3-действия."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.last_action_redis import (
    LastV3UpdaterActionRedisCache,
    LastV3UpdaterActionSnapshot,
    build_snapshot_from_applied,
    truncate_keyword_text,
)


@pytest.mark.unit
def test_snapshot_roundtrip_json() -> None:
    ts = datetime(2026, 5, 26, 15, 32, 6, tzinfo=timezone.utc)
    snap = LastV3UpdaterActionSnapshot(
        updated_at=ts,
        action=V3ActionType.UP,
        keyword_text="футболка",
        keyword_setting_id=42,
        from_mode="MIN_CPA",
        to_mode="OPTIMUM",
        reason="up_cost_first_pooled",
        batch_extra_count=2,
    )
    restored = LastV3UpdaterActionSnapshot.from_redis(snap.to_redis())
    assert restored is not None
    assert restored.updated_at == ts
    assert restored.action == V3ActionType.UP
    assert restored.keyword_text == "футболка"
    assert restored.batch_extra_count == 2


@pytest.mark.unit
def test_snapshot_from_redis_invalid_returns_none() -> None:
    assert LastV3UpdaterActionSnapshot.from_redis("not-json") is None
    assert LastV3UpdaterActionSnapshot.from_redis("{}") is None


@pytest.mark.unit
def test_truncate_keyword_text() -> None:
    long = "а" * 50
    assert len(truncate_keyword_text(long, max_len=40)) == 40
    assert truncate_keyword_text(long, max_len=40).endswith("…")


@pytest.mark.unit
def test_build_snapshot_from_applied() -> None:
    snap = build_snapshot_from_applied(
        action=V3ActionType.FORCE_OFF,
        keyword_text="ключ",
        keyword_setting_id=1,
        from_mode=KeywordStrategyMode.OPTIMUM,
        to_mode=KeywordStrategyMode.OFF,
        reason="overspend_max_pfo",
        batch_extra_count=3,
    )
    assert snap.from_mode == "OPTIMUM"
    assert snap.to_mode == "OFF"
    assert snap.batch_extra_count == 3


@pytest.mark.unit
def test_redis_cache_key_prefix() -> None:
    adv = MagicMock()
    adv.adv_id = 999
    cache = LastV3UpdaterActionRedisCache(adv)
    assert cache.key == "LastV3UpdaterAction:999"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_cache_set_calls_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = MagicMock()
    adv.adv_id = 999
    cache = LastV3UpdaterActionRedisCache(adv)
    mock_client = AsyncMock()
    monkeypatch.setattr(
        LastV3UpdaterActionRedisCache,
        "client",
        property(lambda self: mock_client),
    )
    snap = build_snapshot_from_applied(
        action=V3ActionType.UP,
        keyword_text="k",
        keyword_setting_id=1,
        from_mode=KeywordStrategyMode.OFF,
        to_mode=KeywordStrategyMode.MIN_CPA,
        reason="r",
        batch_extra_count=0,
    )
    await cache.set(snap)
    mock_client.set.assert_awaited_once()
    key = mock_client.set.call_args[0][0]
    payload = mock_client.set.call_args[0][1]
    assert key == "LastV3UpdaterAction:999"
    assert "UP" in payload
