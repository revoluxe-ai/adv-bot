"""Read-only integration test for rec system bid debug entrypoint.

Требует ``destructive_local`` + CH opt-in. Не использует production ``default_db``.
"""

from __future__ import annotations

import os
from datetime import datetime

import pytest
from clickhouse_connect.driver.exceptions import DatabaseError

from app.domain.rec_system_bid_math.plan_ranker import PlanContext
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_recommendation_read_service import (
    AutoShelfBidRecommendationReadService,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_increment_manager.auto_shelf_bid_repository import (
    AutoShelfBidRepository,
)
from tests.support.destructive_clickhouse import ALLOWED_CH_DATABASE

pytestmark = pytest.mark.destructive_local


def _parse_dt(name: str) -> datetime:
    """Прочитать ISO datetime из env или skip."""
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} is not set")
    return datetime.fromisoformat(value)


def _debug_integration_enabled() -> bool:
    """Проверить явный opt-in флаг для живого ClickHouse debug-прогона."""
    return os.environ.get("REC_BID_DEBUG_INTEGRATION_ENABLED", "").lower() == "true"


async def _ensure_debug_table_exists(clickhouse_client) -> None:
    """Убедиться, что debug-таблица доступна в test ClickHouse DB.

    Тест не создаёт schema сам и остаётся read-only: если таблицы нет,
    debug-прогон пропускается вместо падения на UNKNOWN_TABLE.
    """
    try:
        result = await clickhouse_client.query(
            f"""
            SELECT count()
            FROM system.tables
            WHERE database = '{ALLOWED_CH_DATABASE}'
              AND name = 'auto_shelf_bid_intervals'
            """
        )
    except DatabaseError as exc:
        pytest.skip(f"ClickHouse debug integration is unavailable: {exc}")

    row_count = int(result.result_rows[0][0]) if result.result_rows else 0
    if row_count == 0:
        pytest.skip("auto_shelf_bid_intervals table is not available")


@pytest.mark.asyncio
async def test_debug_fetch_and_rank_rec_system_bids_for_nmid(
    clickhouse_client,
) -> None:
    """Run the debug ranking flow only when explicitly enabled."""
    if not _debug_integration_enabled():
        pytest.skip("REC_BID_DEBUG_INTEGRATION_ENABLED is not set to true")

    nmid_value = os.environ.get("REC_BID_DEBUG_NMID")
    if not nmid_value:
        pytest.skip("REC_BID_DEBUG_NMID is not set")

    nmid = int(nmid_value)
    mode = os.environ.get("REC_BID_DEBUG_MODE", "main")
    date_from = _parse_dt("REC_BID_DEBUG_DATE_FROM")
    date_to = _parse_dt("REC_BID_DEBUG_DATE_TO")

    repository = AutoShelfBidRepository(wb_manager_hub=None)  # type: ignore[arg-type]
    service = AutoShelfBidRecommendationReadService(repository)

    await _ensure_debug_table_exists(clickhouse_client)

    diagnostics = await service.fetch_bid_hour_observation_diagnostics(
        nmid=nmid,
        mode=mode,
        date_from=date_from,
        date_to=date_to,
    )

    buckets = await repository.fetch_rec_bid_bucket_observations_for_nmid(
        nmid=nmid,
        mode=mode,
        date_from=date_from,
        date_to=date_to,
    )
    ctr_by_bid = {bucket.bid: 0.02 for bucket in buckets}

    result = await service.debug_fetch_and_rank_rec_system_bids_for_nmid(
        nmid=nmid,
        mode=mode,
        date_from=date_from,
        date_to=date_to,
        plan_context=PlanContext(
            sales_plan=100.0,
            current_fact_sales=10.0,
            current_sales_forecast=90.0,
            target_order_cost=100.0,
            max_order_cost=120.0,
            click_to_order_cr_7d=0.1,
        ),
        ctr_by_bid=ctr_by_bid,
    )

    assert diagnostics["raw_rows_count"] >= 0
    assert diagnostics["distinct_bids"] >= 0
    assert "bid_result" in result
    assert "plan_ranked" in result
