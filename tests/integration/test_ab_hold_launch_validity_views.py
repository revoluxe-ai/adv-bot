"""Integration (CH aggregate path): объём показов кандидатов за 24ч (§2c / 13.1).

Проверяет, что launch-validity soft-gate агрегирует показы ключей-кандидатов через
реюз ``full_wb_adv_stat.get_keywords_views_by_days`` (MV ``mv_clusters_daily_agg``)
и сравнивает с порогом ``AB_HOLD_MIN_TOTAL_VIEWS_24H``. ClickHouse-клиент подменён
контролируемым dummy, чтобы прогнать реальный путь построения/парсинга запроса без
docker-CH; граничные значения вокруг 1000.

Класс: integration (path CH). Регрессия — неверная агрегация окна 24ч / порога.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold import (
    launch_validity_gate as gate,
)
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import (
    full_wb_adv_stat,
)


class _DummyResult:
    def __init__(self, rows: list[tuple]) -> None:
        self.result_rows = rows


class _DummyClient:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    async def query(self, *_args, **_kwargs):
        return _DummyResult(self._rows)


class _DummyClientCM:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    async def __aenter__(self):
        return _DummyClient(self._rows)

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _DummySemaphore:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("total_views", "expected_sufficient"),
    [(999, False), (1000, True), (1001, True)],
)
async def test_launch_view_volume_aggregate_boundary_over_ch(
    monkeypatch: pytest.MonkeyPatch,
    total_views: int,
    expected_sufficient: bool,
) -> None:
    """13.1: агрегат за 24ч из mv_clusters_daily_agg; граница порога 1000."""
    now = datetime(2026, 7, 15, 12, 0, 0)
    rows = [(date(2026, 7, 15), total_views)]

    monkeypatch.setattr(
        full_wb_adv_stat,
        "get_clickhouse_client",
        lambda: _DummyClientCM(rows),
    )
    monkeypatch.setattr(
        full_wb_adv_stat, "anti_ch_crash_semaphore", _DummySemaphore()
    )

    class _Adv:
        adv_id = 4242
        search_adv_id = None

    sufficient, total = await gate.evaluate_ab_hold_launch_view_volume(
        _Adv(), now=now
    )
    assert total == total_views
    assert sufficient is expected_sufficient
