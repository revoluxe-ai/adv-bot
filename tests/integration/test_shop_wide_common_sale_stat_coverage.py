"""Integration: shop-wide coverage evidence + production CH writer (destructive_local CH).

Uses ``dedicated_wb_sky_common_sales_clickhouse_client`` — direct connect to
externally provisioned isolated endpoint (127.0.0.1:8124). Does **not** invoke
global ``clickhouse_client`` compose lifecycle.
"""

from __future__ import annotations

import datetime
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from clickhouse_connect import get_async_client

from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
    CommonSaleStatRow,
)
from app.modules.shop_runner.service_manager.services.common_sale_stat_updater import (
    clickhouse_common_stat_manager as ch_common_stat_module,
)
from app.modules.shop_runner.service_manager.services.common_sale_stat_updater.clickhouse_common_stat_manager import (
    ClickHouseCommonStatManager,
)
from app.modules.shop_runner.service_manager.services import (
    clickhouse_freshness_reader as freshness_reader_module,
)
from app.modules.shop_runner.service_manager.services.clickhouse_freshness_reader import (
    ClickHouseStatsFreshnessReader,
)
from app.utils.click_house import client as clickhouse_client_module
from app.modules.shop_runner.service_manager.services.common_sale_stat_updater.common_sale_stat_updater import (
    CommonSaleStatUpdater,
)
from app.modules.shop_runner.service_manager.services.shop_wide_common_sales.collect_types import (
    CollectContext,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from tests.support.destructive_ch_reset import apply_clickhouse_session_ddl
from tests.support.destructive_lifecycle import run_awaitable_from_sync
from tests.support.destructive_clickhouse import (
    ALLOWED_CH_DATABASE,
    create_validated_async_clickhouse_client,
    validate_destructive_clickhouse_endpoint,
)
from tests.support.rewrite_default_db_ch_client import patch_get_clickhouse_client

pytestmark = [pytest.mark.integration]

WB_SKY_OWNED_CH_TASK_ENV = "WB_SKY_OWNED_CH_TASK"
WB_SKY_OWNED_CH_TASK_ID = "WB-SKY-COMMON-SALES-20261005"


def _assert_dedicated_ch_gates() -> None:
    """Fail-closed guard before any destructive CH I/O on dedicated endpoint."""
    if os.environ.get(WB_SKY_OWNED_CH_TASK_ENV) != WB_SKY_OWNED_CH_TASK_ID:
        pytest.skip(
            f"Requires {WB_SKY_OWNED_CH_TASK_ENV}={WB_SKY_OWNED_CH_TASK_ID!r} "
            "for externally owned CH container"
        )
    _ = validate_destructive_clickhouse_endpoint(
        host=os.environ.get("CLICK_HOUSE_HOST"),
        port=os.environ.get("CLICKHOUSE_PORT"),
        database=ALLOWED_CH_DATABASE,
        username=os.environ.get("CLICK_HOUSE_USER"),
    )


@pytest.fixture(scope="session")
def dedicated_wb_sky_common_sales_clickhouse_client() -> Iterator[Any]:
    """
    Session-scoped client for externally provisioned WB-SKY isolated CH.

    No docker-compose / global lifecycle — connects directly after validation.
    """
    _assert_dedicated_ch_gates()

    host = os.environ.get("CLICK_HOUSE_HOST", "127.0.0.1")
    port = int(os.environ.get("CLICKHOUSE_PORT", "8124"))
    user = os.environ.get("CLICK_HOUSE_USER", "default")
    password = os.environ.get("CLICK_HOUSE_PASSWORD", "")

    async def _bootstrap() -> Any:
        client = await create_validated_async_clickhouse_client(
            host=host,
            port=port,
            database=ALLOWED_CH_DATABASE,
            username=user,
            password=password,
            get_async_client_fn=get_async_client,
        )
        await client.command("SELECT 1")
        await apply_clickhouse_session_ddl(client)
        return client

    client = run_awaitable_from_sync(_bootstrap())
    yield client
    client.close()


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_shop_wide_coverage_read_write_roundtrip(
    dedicated_wb_sky_common_sales_clickhouse_client: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production ClickHouseCommonStatManager insert + argMax read-latest roundtrip."""
    _assert_dedicated_ch_gates()
    ch_client = dedicated_wb_sky_common_sales_clickhouse_client
    table = f"{ALLOWED_CH_DATABASE}.wb_common_stat"
    await ch_client.command(f"TRUNCATE TABLE IF EXISTS {table}")

    patch_get_clickhouse_client(
        monkeypatch,
        [
            ch_common_stat_module,
            clickhouse_client_module,
            freshness_reader_module,
        ],
        ch_client,
    )

    manager = ClickHouseCommonStatManager()
    day = datetime.date(2025, 12, 21)

    rows_v1 = [
        CommonSaleStatRow(
            nmid=777,
            day=day,
            open_card=1,
            add_to_cart=1,
            orders=1,
            orders_sum=10.25,
            buy_outs=1,
            buyouts_sum_rub=5.75,
        )
    ]
    await manager.insert(rows_v1)

    rows_v2 = [
        CommonSaleStatRow(
            nmid=777,
            day=day,
            open_card=99,
            add_to_cart=99,
            orders=99,
            orders_sum=990.55,
            buy_outs=99,
            buyouts_sum_rub=50.33,
        )
    ]
    await manager.insert(rows_v2)

    complex_adv = SimpleNamespace(main_nmid=777)
    reader = ClickHouseStatsFreshnessReader()
    common_updated_at = await reader.get_common_updated_at(complex_adv)
    assert common_updated_at is not None

    async with anti_ch_crash_semaphore:
        result = await ch_client.query(
            f"""
            SELECT
                nmid,
                date,
                argMax(open_card, version) AS open_card,
                argMax(orders_sum, version) AS orders_sum,
                argMax(buyouts_sum_rub, version) AS buyouts_sum_rub
            FROM {table}
            WHERE nmid = 777 AND date = '2025-12-21'
            GROUP BY nmid, date
            """
        )

    assert result is not None
    assert len(result.result_rows) == 1
    _nmid, _date, open_card, orders_sum, buyouts_sum_rub = result.result_rows[0]
    assert open_card == 99
    assert orders_sum == 990.55
    assert buyouts_sum_rub == 50.33


@pytest.mark.destructive_local
@pytest.mark.asyncio
async def test_collect_by_nmids_uses_production_writer(
    dedicated_wb_sky_common_sales_clickhouse_client: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """collect_by_nmids → ClickHouseCommonStatManager.insert (not manual INSERT)."""
    _assert_dedicated_ch_gates()
    ch_client = dedicated_wb_sky_common_sales_clickhouse_client
    table = f"{ALLOWED_CH_DATABASE}.wb_common_stat"
    await ch_client.command(f"TRUNCATE TABLE IF EXISTS {table}")

    patch_get_clickhouse_client(
        monkeypatch,
        [ch_common_stat_module, clickhouse_client_module],
        ch_client,
    )

    start = datetime.date(2025, 12, 15)
    end = datetime.date(2025, 12, 21)
    rows = [
        CommonSaleStatRow(
            nmid=888,
            day=start + datetime.timedelta(days=i),
            open_card=1,
            add_to_cart=1,
            orders=1,
            orders_sum=10.0,
            buy_outs=1,
            buyouts_sum_rub=5.0,
        )
        for i in range(7)
    ]
    wb_data = SimpleNamespace(
        get_sales_funnel_products_history=AsyncMock(return_value=rows),
    )
    updater = CommonSaleStatUpdater(
        SimpleNamespace(wb_data_manager=wb_data),
        ClickHouseCommonStatManager(),
    )
    ctx = CollectContext(
        attempted_nmids=frozenset({888}),
        window_start=start,
        window_end=end,
    )
    result = await updater.collect_by_nmids([888], collect_context=ctx)
    assert 888 in result.updated_nmids
    assert len(result.persisted_pairs) == 7

    async with anti_ch_crash_semaphore:
        got = await ch_client.query(
            f"SELECT count() FROM {table} WHERE nmid = 888"
        )
    assert got.result_rows[0][0] == 7
