import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
    CommonSaleStatRow,
)
from app.modules.shop_runner.service_manager.services.common_sale_stat_updater.common_sale_stat_updater import (
    CommonSaleStatUpdater,
)


@pytest.mark.asyncio
async def test_common_sale_stat_updater_chunks_and_inserts():
    wb_data_manager = SimpleNamespace()
    wb_data_manager.get_sales_funnel_products_history = AsyncMock(
        side_effect=[
            [
                CommonSaleStatRow(
                    nmid=1,
                    day=datetime.date(2025, 12, 21),
                    open_card=1,
                    add_to_cart=1,
                    orders=1,
                    orders_sum=10.0,
                    buy_outs=1,
                    buyouts_sum_rub=5.0,
                )
            ],
            [
                CommonSaleStatRow(
                    nmid=21,
                    day=datetime.date(2025, 12, 21),
                    open_card=2,
                    add_to_cart=2,
                    orders=2,
                    orders_sum=20.0,
                    buy_outs=2,
                    buyouts_sum_rub=7.0,
                )
            ],
        ]
    )
    wb_manager_hub = SimpleNamespace(wb_data_manager=wb_data_manager)

    clickhouse_manager = SimpleNamespace()
    clickhouse_manager.insert = AsyncMock()

    updater = CommonSaleStatUpdater(
        wb_manager_hub=wb_manager_hub,
        clickhouse_manager=clickhouse_manager,
    )

    advs = [SimpleNamespace(main_nmid=i) for i in range(1, 26)]

    updated = await updater.update_last_week_stats(advs)

    assert wb_data_manager.get_sales_funnel_products_history.await_count == 2
    clickhouse_manager.insert.assert_awaited_once()
    inserted_rows = clickhouse_manager.insert.call_args.args[0]
    assert len(inserted_rows) == 2
    assert updated == {1, 21}


@pytest.mark.asyncio
async def test_common_sale_stat_updater_full_partition_500_120_380():
    """S06: E=120 (6 batches) + U=380 (19 batches) = 25 funnel API calls."""
    call_batches: list[list[int]] = []

    async def _history(*, nmids: list[int], start, end):
        call_batches.append(list(nmids))
        return [
            CommonSaleStatRow(
                nmid=nmids[0],
                day=datetime.date(2025, 12, 21),
                open_card=1,
                add_to_cart=1,
                orders=1,
                orders_sum=10.0,
                buy_outs=1,
                buyouts_sum_rub=5.0,
            )
        ]

    wb_data_manager = SimpleNamespace(
        get_sales_funnel_products_history=AsyncMock(side_effect=_history)
    )
    wb_manager_hub = SimpleNamespace(wb_data_manager=wb_data_manager)
    clickhouse_manager = SimpleNamespace(insert=AsyncMock())
    updater = CommonSaleStatUpdater(
        wb_manager_hub=wb_manager_hub,
        clickhouse_manager=clickhouse_manager,
    )

    e_nmids = list(range(1, 121))
    u_nmids = list(range(121, 501))
    start = datetime.date(2025, 12, 15)
    end = datetime.date(2025, 12, 21)
    from app.modules.shop_runner.service_manager.services.shop_wide_common_sales.collect_types import (
        CollectContext,
    )

    ctx = CollectContext(
        attempted_nmids=frozenset(e_nmids + u_nmids),
        window_start=start,
        window_end=end,
    )
    _ = await updater.collect_by_nmids(
        e_nmids,
        collect_context=ctx,
    )
    e_calls = len(call_batches)
    _ = await updater.collect_by_nmids(
        u_nmids,
        collect_context=ctx,
    )
    total_calls = len(call_batches)
    assert e_calls == 6
    assert total_calls == 25
    e_set = set(n for batch in call_batches[:6] for n in batch)
    u_set = set(n for batch in call_batches[6:] for n in batch)
    assert e_set.isdisjoint(u_set)
    assert len(e_set) == 120
    assert len(u_set) == 380


@pytest.mark.asyncio
async def test_legacy_second_chunk_failure_raises_no_insert():
    """F6: legacy wrapper raises on 2nd chunk fail before any CH insert."""
    wb_data_manager = SimpleNamespace()
    wb_data_manager.get_sales_funnel_products_history = AsyncMock(
        side_effect=[
            [
                CommonSaleStatRow(
                    nmid=1,
                    day=datetime.date(2025, 12, 21),
                    open_card=1,
                    add_to_cart=1,
                    orders=1,
                    orders_sum=10.0,
                    buy_outs=1,
                    buyouts_sum_rub=5.0,
                )
            ],
            RuntimeError("api down"),
        ]
    )
    clickhouse_manager = SimpleNamespace(insert=AsyncMock())
    updater = CommonSaleStatUpdater(
        wb_manager_hub=SimpleNamespace(wb_data_manager=wb_data_manager),
        clickhouse_manager=clickhouse_manager,
    )
    advs = [SimpleNamespace(main_nmid=i) for i in range(1, 26)]

    with pytest.raises(RuntimeError, match="api down"):
        await updater.update_last_week_stats(advs)

    clickhouse_manager.insert.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_returns_set_including_valid_rows():
    """F6: legacy return set matches rows inserted (old semantics)."""
    row = CommonSaleStatRow(
        nmid=7,
        day=datetime.date(2025, 12, 21),
        open_card=1,
        add_to_cart=1,
        orders=1,
        orders_sum=10.0,
        buy_outs=1,
        buyouts_sum_rub=5.0,
    )
    wb_data_manager = SimpleNamespace(
        get_sales_funnel_products_history=AsyncMock(return_value=[row])
    )
    clickhouse_manager = SimpleNamespace(insert=AsyncMock())
    updater = CommonSaleStatUpdater(
        wb_manager_hub=SimpleNamespace(wb_data_manager=wb_data_manager),
        clickhouse_manager=clickhouse_manager,
    )
    updated = await updater.update_last_week_stats([SimpleNamespace(main_nmid=7)])
    assert updated == {7}


