"""Integration: default factual loader path plus a live CH read fixture.

The test-side keyboard boundary returns production-shaped rows whose positions
come from a persisted ClickHouse ``avr_pos`` re-read. This proves the default
``_load_factual_positions`` request/return/empty wiring without fabricating an
AdvSetting factual-position field; the full provider certification remains
destructive-local.

Live run requires ``AUTHORIZE_ONE_LIVE_RUN`` + independent re-audit.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    confirm_handlers,
)
from tests.factories.clickhouse_factory import (
    CLUSTERS_ADV_STATS_COLUMNS,
    ClustersAdvStatsFactory,
    build_clusters_adv_stats_rows,
)
from tests.unit.auto_updater_v3.card_ab_hold.confirmation_contract import (
    CAH_TP_FIELD_SEPARATION_001,
    CAH_TP_MISSING_001,
    CAH_TP_POSITIVE_001,
    production_factual_rows,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.destructive_local,
]


@pytest.mark.integration
@pytest.mark.parametrize(
    "case",
    [CAH_TP_POSITIVE_001, CAH_TP_FIELD_SEPARATION_001],
    ids=lambda case: case.case_id,
)
async def test_load_factual_positions_default_keyboard_loader_with_live_ch_fixture(
    clickhouse_client,
    case,
) -> None:
    """Default loader consumes shared rows backed by a live CH read."""
    keyword, position = next(iter(case.positions.items()))
    ping = await clickhouse_client.query("SELECT 1")
    assert ping.result_rows == [(1,)]

    await clickhouse_client.command(
        "TRUNCATE TABLE IF EXISTS test_adv_bot_clickhouse.clusters_adv_stats"
    )
    record = ClustersAdvStatsFactory.build(
        adv_id=88_001,
        nmid=8_002_002,
        norm_query=keyword,
        wb_category="test_cat",
        views=50,
        clicks=5,
        avr_pos=position,
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
        parameters={"q": keyword},
    )
    assert float(re_read.result_rows[0][0]) == pytest.approx(position)

    adv = SimpleNamespace(
        id=1,
        card_ab_hold_factual_positions_json={keyword: 99.0},
    )

    async def _keyboard_rows_from_ch(_adv: object) -> list[SimpleNamespace]:
        """Production-shaped keyboard rows sourced from the CH re-read."""
        pos = float(re_read.result_rows[0][0])
        rows = production_factual_rows(case)
        rows[0].cluster_stat.position = pos
        return rows

    keyboard_loader = AsyncMock(side_effect=_keyboard_rows_from_ch)
    with patch(
        "app.client_bot.utils.get_keywords_for_keyboard",
        new=keyboard_loader,
    ):
        positions = await confirm_handlers._load_factual_positions(adv)

    keyboard_loader.assert_awaited_once_with(adv)
    assert positions == {keyword: position}
    assert positions[keyword] != 99.0


@pytest.mark.integration
async def test_missing_factual_position_boundary_excludes_keyword_from_w3(
    clickhouse_client,
) -> None:
    """CH empty read + W3 validator preserves missing-position semantics."""
    case = CAH_TP_MISSING_001
    keyword, reason = case.expected_exclusions[0]
    missing = await clickhouse_client.query(
        """
        SELECT norm_query, avr_pos
        FROM test_adv_bot_clickhouse.clusters_adv_stats
        WHERE norm_query = {q:String}
        LIMIT 1
        """,
        parameters={"q": keyword},
    )
    assert missing.result_rows == []

    adv = SimpleNamespace(
        id=88_002,
        card_ab_hold_confirmed_keywords_json=[keyword],
        card_ab_hold_confirmed_target_places_json={},
    )
    keyboard_loader = AsyncMock(return_value=[])
    with patch(
        "app.client_bot.utils.get_keywords_for_keyboard",
        new=keyboard_loader,
    ):
        positions = await confirm_handlers._load_factual_positions(adv)
    rows, exclusions = confirm_handlers._tp_rows_and_exclusions(adv, positions)

    keyboard_loader.assert_awaited_once_with(adv)
    assert positions == {}
    assert rows == []
    assert exclusions == [
        (keyword, reason)
    ]
