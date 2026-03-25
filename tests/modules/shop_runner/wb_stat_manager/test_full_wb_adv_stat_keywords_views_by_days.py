from __future__ import annotations

from datetime import datetime

import pytest


class _DummyResult:
    result_rows: list[tuple] = []


class _DummyClient:
    async def query(self, *_args, **_kwargs):
        return _DummyResult()


class _DummyClientCM:
    async def __aenter__(self):
        return _DummyClient()

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DummySemaphore:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_get_keywords_views_by_days_never_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat

    monkeypatch.setattr(full_wb_adv_stat, "get_clickhouse_client", lambda: _DummyClientCM())
    monkeypatch.setattr(full_wb_adv_stat, "anti_ch_crash_semaphore", _DummySemaphore())

    start = datetime(2026, 3, 24, 10, 0, 0)
    end = datetime(2026, 3, 24, 23, 0, 0)
    result = await full_wb_adv_stat.get_keywords_views_by_days([123], start, end)

    assert isinstance(result, dict)
    assert result  # should include the date with 0
