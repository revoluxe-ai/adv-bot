"""Integration: ``_load_factual_positions`` injectable keywords_loader + CH fixture.

Full production keyboard path (``get_keywords_for_keyboard`` → phrases/CH/PG)
needs multi-store bootstrap beyond this gap. Here we prove:

1. live ``clickhouse_client`` fixture is reachable;
2. injectable ``keywords_loader`` drives factual positions without AdvSetting
   phantom columns;
3. optional CH seed of ``avr_pos`` is readable from test DB (wiring proof).

Live run requires ``AUTHORIZE_ONE_LIVE_RUN`` + independent re-audit.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    confirm_handlers,
)
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
async def test_load_factual_positions_injectable_loader_with_live_ch_fixture(
    clickhouse_client,
) -> None:
    """Injectable loader + live CH fixture; positions from loader, not AdvSetting."""
    ping = await clickhouse_client.query("SELECT 1")
    assert ping.result_rows == [(1,)]

    await clickhouse_client.command(
        "TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.clusters_adv_stats"
    )
    record = ClustersAdvStatsFactory.build(
        adv_id=88_001,
        nmid=8_002_002,
        norm_query="factual_pos_kw",
        wb_category="test_cat",
        views=50,
        clicks=5,
        avr_pos=14.4,
        date=date.today(),
        timestamp=datetime.now(timezone.utc),
    )
    await clickhouse_client.insert(
        "test_adv_bot_clickhouse.clusters_adv_stats",
        build_clusters_adv_stats_rows([record]),
        column_names=CLUSTERS_ADV_STATS_COLUMNS,
    )
    re_read = await clickhouse_client.query(
        """
        SELECT avr_pos
        FROM test_adv_bot_clickhouse.clusters_adv_stats
        WHERE norm_query = {q:String}
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        parameters={"q": "factual_pos_kw"},
    )
    assert float(re_read.result_rows[0][0]) == pytest.approx(14.4)

    adv = SimpleNamespace(
        id=1,
        card_ab_hold_factual_positions_json={"factual_pos_kw": 99.0},
    )

    async def _loader_from_ch_seed(_adv: object) -> list[SimpleNamespace]:
        """CH-backed loader: position taken from persisted ``avr_pos`` row."""
        pos = float(re_read.result_rows[0][0])
        return [
            SimpleNamespace(
                text="factual_pos_kw",
                cluster_stat=SimpleNamespace(position=pos),
            )
        ]

    positions = await confirm_handlers._load_factual_positions(
        adv, keywords_loader=_loader_from_ch_seed
    )
    assert positions == {"factual_pos_kw": 14.4}
    assert positions["factual_pos_kw"] != 99.0
