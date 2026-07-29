"""Integration (CH aggregate path): campaign-level proxy Σ (§2c / 13.1).

Проверяет launch-validity soft-gate через реюз
``full_wb_adv_stat.get_keywords_views_by_days`` (MV ``mv_clusters_daily_agg``)
и порог ``AB_HOLD_MIN_TOTAL_VIEWS_24H``. ClickHouse-клиент подменён dummy;
граничные значения вокруг 1000.

Класс: integration (path CH). Регрессия — неверная агрегация calendar-day cover.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold import (
    launch_validity_gate as gate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.launch_validity_gate import (
    LaunchViewVolumeOutcome,
)
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import (
    full_wb_adv_stat,
)

pytestmark = pytest.mark.integration


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

    result = await gate.evaluate_ab_hold_launch_view_volume(
        _Adv(), now=now
    )
    assert result.total_views == total_views
    assert result.is_sufficient is expected_sufficient
    if expected_sufficient:
        assert result.outcome == LaunchViewVolumeOutcome.SUFFICIENT
    else:
        assert result.outcome == LaunchViewVolumeOutcome.LOW
