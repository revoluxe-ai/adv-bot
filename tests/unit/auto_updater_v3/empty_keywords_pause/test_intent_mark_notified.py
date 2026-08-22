"""Unit: EmptyKeywordsPauseIntentManager.mark_notified Redis NX debounce (fakeredis).

Protects once-per-TTL notify debounce: first SET NX succeeds, second returns False.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fakeredis.aioredis import FakeRedis

from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.intent import (
    EmptyKeywordsPauseIntentManager,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_notified_first_true_second_false(fake_redis: FakeRedis) -> None:
    """SET NX: первое уведомление True, повтор в окне TTL — False."""
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        mgr = EmptyKeywordsPauseIntentManager()
        assert await mgr.mark_notified(9001) is True
        assert await mgr.mark_notified(9001) is False

        key = mgr._notify_key(9001)
        assert key == "empty-keywords-pause-notified:9001"
        assert await fake_redis.get(key) == "1"
        ttl = await fake_redis.ttl(key)
        assert 0 < ttl <= EmptyKeywordsPauseIntentManager._NOTIFY_TTL


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_notified_independent_per_adv_id(fake_redis: FakeRedis) -> None:
    """Debounce ключ изолирован по adv_id."""
    with patch.object(EmptyKeywordsPauseIntentManager, "_client", fake_redis):
        mgr = EmptyKeywordsPauseIntentManager()
        assert await mgr.mark_notified(1) is True
        assert await mgr.mark_notified(2) is True
        assert await mgr.mark_notified(1) is False
        assert await mgr.mark_notified(2) is False
