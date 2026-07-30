"""Integration: CTR CH seam reads persisted ``mv_clusters_daily_agg``.

Live run requires ``AUTHORIZE_ONE_LIVE_RUN`` + independent re-audit.
Authored for ``clickhouse_client`` fixture; do not run without live auth.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.client_bot.user_interface.handlers.keyword_settings import (
    apply_keyword_ctr_boost_with_client,
)
from app.modules.wb_adv_updater import data_manager
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from tests.factories.clickhouse_factory import (
    CLUSTERS_ADV_STATS_COLUMNS,
    ClustersAdvStatsFactory,
    build_clusters_adv_stats_rows,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


@pytest.mark.integration
async def test_apply_keyword_ctr_boost_with_client_reads_persisted_ch(
    clickhouse_client,
) -> None:
    """Seed clusters → MV; child seam reads CH and mutates ``added_clicks``.

    Assert re-reads persisted clicks/views from CH (not only mock args).
    """
    await clickhouse_client.command(
        "TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.clusters_adv_stats"
    )
    # Materialized view target may need truncate depending on engine; best-effort.
    try:
        await clickhouse_client.command(
            "TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.mv_clusters_daily_agg"
        )
    except Exception:
        pass

    adv_id = 77_001
    norm_query = "ctr_boost_seam_kw"
    nmid = 9_001_001
    base_date = date.today()
    now_dt = datetime.now(timezone.utc)

    records = [
        ClustersAdvStatsFactory.build(
            adv_id=adv_id,
            nmid=nmid,
            norm_query=norm_query,
            wb_category="test_cat",
            views=200,
            clicks=10,
            cpm=100.0,
            cpc=5.0,
            avr_pos=2.0,
            date=base_date,
            timestamp=now_dt,
        ),
        ClustersAdvStatsFactory.build(
            adv_id=adv_id,
            nmid=nmid,
            norm_query=norm_query,
            wb_category="test_cat",
            views=100,
            clicks=5,
            cpm=90.0,
            cpc=4.0,
            avr_pos=3.0,
            date=base_date - timedelta(days=1),
            timestamp=now_dt - timedelta(hours=1),
        ),
    ]
    rows = build_clusters_adv_stats_rows(records)
    await clickhouse_client.insert(
        "test_adv_bot_clickhouse.clusters_adv_stats",
        rows,
        column_names=CLUSTERS_ADV_STATS_COLUMNS,
    )

    async with anti_ch_crash_semaphore:
        ch_clicks, ch_views, _ = await data_manager.get_keyword_statistic_clickhouse(
            clickhouse_client,
            norm_query,
            {adv_id},
        )

    assert ch_clicks == 15
    assert ch_views == 300

    keyword = SimpleNamespace(added_clicks=None, added_views=None)
    added = await apply_keyword_ctr_boost_with_client(
        clickhouse_client,
        keyword_setting=keyword,
        keyword_text=norm_query,
        adv_ids={adv_id},
        min_ctr=0.10,
        boost_percent=10,
    )

    # new_ctr=0.11; 0.11*300 - 15 = 18
    assert added == 18
    assert keyword.added_clicks == 18

    # Re-read store: CH totals unchanged by CTR mutate (mutate is on ORM entity).
    async with anti_ch_crash_semaphore:
        again_clicks, again_views, _ = await data_manager.get_keyword_statistic_clickhouse(
            clickhouse_client,
            norm_query,
            {adv_id},
        )
    assert again_clicks == ch_clicks
    assert again_views == ch_views
