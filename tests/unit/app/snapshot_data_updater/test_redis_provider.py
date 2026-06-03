"""Unit-тесты RedisSnapshotProviderLive (malformed mget)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.snapshot_data_updater.dto import AdvSettingsSnapshotDTO
from app.snapshot_data_updater.providers.redis_provider import (
    RedisSnapshotProviderLive,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_live_min_bids_skips_malformed_mget_values() -> None:
    """Пустые и битые JSON в mget не роняют batch — coverage < 1."""
    settings = AdvSettingsSnapshotDTO(
        adv_id=10,
        shop_id="s1",
        nm_id=100,
        search_adv_id=11,
    )
    cache = MagicMock()
    client = MagicMock()
    cache.client = client
    # auto + search cells
    client.mget = AsyncMock(return_value=[b'{"cpm": 50}', "not-json"])
    provider = RedisSnapshotProviderLive(keywords_cache=cache)
    result = await provider.fetch_min_bids_for_settings([settings])
    assert 10 in result
    mb = result[10]
    assert mb.hit_cells >= 1
    assert mb.coverage_ratio < 1.0 or mb.missing_cells
