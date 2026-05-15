from __future__ import annotations

from datetime import date, datetime

import pytest


class _DummyResult:
    def __init__(self, result_rows: list[tuple]) -> None:
        self.result_rows = result_rows


class _DummyClient:
    def __init__(self, result_rows: list[tuple]) -> None:
        self._result_rows = result_rows

    async def query(self, *_args, **_kwargs):
        return _DummyResult(self._result_rows)


class _DummyClientCM:
    def __init__(self, result_rows: list[tuple]) -> None:
        self._result_rows = result_rows

    async def __aenter__(self):
        return _DummyClient(self._result_rows)

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DummySemaphore:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_get_keywords_clicks_by_days_prefills_full_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import (
        full_wb_adv_stat,
    )

    # ClickHouse returns only day-1 and day-3; day-2 must be present as 0.
    rows = [
        (date(2026, 3, 24), 5),
        (date(2026, 3, 26), 7),
    ]

    monkeypatch.setattr(
        full_wb_adv_stat, "get_clickhouse_client", lambda: _DummyClientCM(rows)
    )
    monkeypatch.setattr(full_wb_adv_stat, "anti_ch_crash_semaphore", _DummySemaphore())

    start = datetime(2026, 3, 24, 10, 0, 0)
    end = datetime(2026, 3, 26, 23, 0, 0)
    result = await full_wb_adv_stat.get_keywords_clicks_by_days([123], start, end)

    assert result == {
        date(2026, 3, 24): 5,
        date(2026, 3, 25): 0,
        date(2026, 3, 26): 7,
    }


@pytest.mark.asyncio
async def test_get_keywords_clicks_by_days_passes_multiple_adv_ids_to_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Запрос к CH должен включать все adv_id (авто + поиск) одним списком."""
    from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import (
        full_wb_adv_stat,
    )

    captured: list[str] = []

    class _CapturingClient:
        async def query(self, query: str, *_args, **_kwargs):
            captured.append(query)
            return _DummyResult([])

    class _CapturingCM:
        async def __aenter__(self):
            return _CapturingClient()

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(
        full_wb_adv_stat, "get_clickhouse_client", lambda: _CapturingCM()
    )
    monkeypatch.setattr(full_wb_adv_stat, "anti_ch_crash_semaphore", _DummySemaphore())

    start = datetime(2026, 3, 24, 10, 0, 0)
    end = datetime(2026, 3, 24, 23, 0, 0)
    await full_wb_adv_stat.get_keywords_clicks_by_days([111, 222], start, end)

    assert len(captured) == 1
    assert "111" in captured[0] and "222" in captured[0]

