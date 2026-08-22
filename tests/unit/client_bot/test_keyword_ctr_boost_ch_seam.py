"""CTR CH seam: stats read → mutate ``added_clicks`` without guarded live CH.

Live guarded client forbids ``default_db`` in SQL (destructive fixture).
Production issued SQL MUST keep ``default_db.mv_clusters_daily_agg``
(see ``test_get_keyword_statistic_clickhouse_sql_contract``). This module
exercises the seam via a fake ``client.query`` that returns persisted-like
aggregates — no GuardedClickHouseClient, no ``default_db`` round-trip.

Replaces the former impossible live wiring under
``tests/integration/client_bot/test_keyword_ctr_boost_ch_seam.py`` (seeded
``test_adv_bot_clickhouse`` while production SQL addresses ``default_db``).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.client_bot.user_interface.handlers.keyword_settings import (
    apply_keyword_ctr_boost_with_client,
)
from app.modules.wb_adv_updater import data_manager

pytestmark = [
    pytest.mark.asyncio,
]


class _PersistedStatsQueryClient:
    """Fake CH client: accepts production SQL, returns fixed aggregates.

    Simulates a successful read of persisted keyword stats without a live
    ClickHouse or destructive guard. Does not rewrite SQL.
    """

    def __init__(self, *, clicks: int, views: int, spend: float = 0.0) -> None:
        self.clicks = clicks
        self.views = views
        self.spend = spend
        self.queries: list[str] = []

    async def query(self, query: str, *args: object, **kwargs: object) -> SimpleNamespace:
        """Record issued SQL and return configured aggregate row."""
        self.queries.append(query)
        return SimpleNamespace(result_rows=[(self.clicks, self.views, self.spend)])


@pytest.mark.unit
async def test_apply_keyword_ctr_boost_with_client_reads_persisted_ch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Seam: real ``get_keyword_statistic_clickhouse`` → mutate ``added_clicks``.

    Uses a fake query client (not GuardedClickHouseClient) so production
    ``default_db`` qualification in issued SQL does not trip the destructive
    guard. SQL-contract for ``default_db.mv_clusters_daily_agg`` remains in
    the dedicated unit contract test — not re-asserted as a full contract here;
    a single containment check proves the live data_manager path ran (not mocked away).
    """

    class _DummySemaphore:
        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, *args: object) -> bool:
            return False

    monkeypatch.setattr(data_manager, "anti_ch_crash_semaphore", _DummySemaphore())

    # Persisted-like totals: clicks=15, views=300 → boost adds 18.
    client = _PersistedStatsQueryClient(clicks=15, views=300)
    keyword = SimpleNamespace(added_clicks=None, added_views=None)
    adv_id = 77_001
    norm_query = "ctr_boost_seam_kw"

    added = await apply_keyword_ctr_boost_with_client(
        client,
        keyword_setting=keyword,
        keyword_text=norm_query,
        adv_ids={adv_id},
        min_ctr=0.10,
        boost_percent=10,
    )

    # new_ctr=0.11; 0.11*300 - 15 = 18
    assert added == 18
    assert keyword.added_clicks == 18
    assert len(client.queries) == 1
    # Production path issued SQL (guard would reject this on live client).
    assert "default_db.mv_clusters_daily_agg" in client.queries[0]

    # Second read through the same seam path: mutate is ORM-only; CH totals
    # from the fake store are unchanged across re-query.
    again_clicks, again_views, _ = await data_manager.get_keyword_statistic_clickhouse(
        client,
        norm_query,
        {adv_id},
    )
    assert again_clicks == 15
    assert again_views == 300
    assert keyword.added_clicks == 18
