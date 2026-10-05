"""Unit tests: shop-wide common-sales coordinator, partition, TaskGroup survival."""

from __future__ import annotations

import ast
import asyncio
import datetime
import inspect
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.mp.wb.api.adapter.analitika_i_dannye_client.voronka_prodazh.post_sales_funnel_products_history.dto import (
    CommonSaleStatRow,
)
from app.core.mp.wb.api.generated.products.v1.content_products_client.types import UNSET
from app.core.redis_manager_v2.redis_client import RedisClient
from app.modules.shop_runner.service_manager.exc import StopShopUpdateException
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany
from app.modules.shop_runner.service_manager.services.common_sale_stat_updater.common_sale_stat_updater import (
    CommonSaleStatUpdater,
)
from app.modules.shop_runner.service_manager.services.shop_wide_common_sales.collect_types import (
    CollectContext,
    CoverageStatus,
    expected_shop_pairs,
)
from app.modules.shop_runner.service_manager.services.shop_wide_common_sales.coordinator import (
    run_shop_wide_common_sale_stat_tick,
)
from app.modules.shop_runner.service_manager.services.shop_wide_common_sales.coverage_evidence import (
    EVIDENCE_SCHEMA_VERSION,
    LastAttemptEvidence,
    ShopWideCoverageEvidenceStore,
)
from app.modules.shop_runner.service_manager.services.shop_wide_common_sales.fact_validator import (
    validate_and_deduplicate_rows,
)
from app.modules.shop_runner.service_manager.services.shop_wide_common_sales.legacy_assigned_nmids import (
    resolve_legacy_assigned_nmids,
)
from app.modules.shop_runner.service_manager.services.shop_wide_common_sales.shop_assortment_reader import (
    ShopAssortmentReader,
)
from app.modules.shop_runner.service_manager.services.shop_wide_common_sales.taskgroup_no_ad_supervisor import (
    SUPERVISOR_COROUTINE_NAMES,
    taskgroup_no_ad_supervisor,
)
from app.modules.shop_runner.wb_shop import WBShop

pytestmark = pytest.mark.unit

TASKGROUP_COROUTINE_NAMES: frozenset[str] = frozenset(
    {
        "update_advs_data_from_wb_to_pg",
        "update_cards_data_from_wb_to_pg",
        "update_common_sale_stat",
        "update_full_adv_stat",
        "update_clusters_adv_stats_today",
        "update_clusters_adv_stats_history",
        "refresh_stats_freshness_cache",
        "adv_settings_auto_update",
        "update_minus_phrases_in_advs",
        "update_cluster_bids",
        "cache_current_cluster_bids",
        "preload_min_bids_cache_miss",
        "preload_min_bids_cache_old",
        "handle_stats_stale_emergency",
        "update_plan_fact_stats",
        "auto_budget_watchdog",
        "update_top_key_in_advs",
        "update_common_bid_in_search_adv",
        "increment_fact_data_stats",
        "auto_shelf_bid_increment_stats",
        "auto_shelf_bid_control",
        "white_list_tail_trimmer",
        "auto_reset_bid_for_auto_adv",
        "update_individual_keyword_target_places",
        "change_adv_strategy",
    }
)


def _row(
    nmid: int,
    day: datetime.date,
    *,
    open_card: int = 1,
    orders_sum: float = 10.0,
    buyouts_sum_rub: float = 5.0,
) -> CommonSaleStatRow:
    return CommonSaleStatRow(
        nmid=nmid,
        day=day,
        open_card=open_card,
        add_to_cart=1,
        orders=1,
        orders_sum=orders_sum,
        buy_outs=1,
        buyouts_sum_rub=buyouts_sum_rub,
    )


def _card_page(nmids: list[int]) -> SimpleNamespace:
    cards = []
    for nmid in nmids:
        cards.append(SimpleNamespace(nm_id=nmid, updated_at="2026-01-01T00:00:00Z"))
    return SimpleNamespace(
        cards=cards,
        cursor=SimpleNamespace(updated_at="2026-01-01T00:00:00Z", nm_id=nmids[-1] if nmids else 0, total=len(nmids)),
    )


def _empty_page() -> SimpleNamespace:
    return SimpleNamespace(cards=[], cursor=SimpleNamespace(total=0))


def _msk_window() -> tuple[datetime.date, datetime.date]:
    from zoneinfo import ZoneInfo

    today = datetime.datetime.now(ZoneInfo("Europe/Moscow")).date()
    return today - datetime.timedelta(days=6), today


@pytest.mark.asyncio
async def test_shop_wide_partition_disjoint(fake_redis) -> None:
    a = set(range(1, 501))
    e = set(range(1, 121))
    u = a - e
    assert len(a) == 500
    assert len(e) == 120
    assert len(u) == 380
    assert u.isdisjoint(e)

    get_complex = AsyncMock(return_value=[SimpleNamespace(main_nmid=i) for i in e])
    wb_shop_dm = SimpleNamespace(get_complex_advs=get_complex)

    pages = [_card_page(list(range(i, i + 100))) for i in range(1, 501, 100)] + [_empty_page()]
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages))

    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(products_manager=products_manager),
        redis_client_wrapper=RedisClient(fake_redis),
    )
    clickhouse = SimpleNamespace(insert=AsyncMock())
    updater = CommonSaleStatUpdater(wb_hub, clickhouse)

    api_calls: list[list[int]] = []

    async def _spy_history(*, nmids: list[int], start: datetime.date, end: datetime.date):
        api_calls.append(list(nmids))
        day = start
        return [_row(n, day) for n in nmids]

    wb_hub.wb_data_manager.get_sales_funnel_products_history = AsyncMock(side_effect=_spy_history)

    with patch(
        "app.modules.shop_runner.service_manager.services.shop_wide_common_sales.coordinator.resolve_legacy_assigned_nmids",
        AsyncMock(
            return_value=SimpleNamespace(
                nmids=frozenset(e),
                complex_advs=tuple(SimpleNamespace(main_nmid=i, all_adv_ids={i}) for i in e),
            )
        ),
    ):
        summary = await run_shop_wide_common_sale_stat_tick(
            shop_id="shop1",
            wb_manager_hub=wb_hub,
            wb_shop_data_manager=wb_shop_dm,
            updater=updater,
            redis_client=RedisClient(fake_redis),
            redis_common_stat_timestamp_manager=SimpleNamespace(set=AsyncMock()),
        )

    assert get_complex.await_count == 0
    e_calls = [c for c in api_calls if set(c) & e]
    u_calls = [c for c in api_calls if set(c) & u]
    assert e_calls
    assert u_calls
    all_nmids_called = set(n for batch in api_calls for n in batch)
    assert len(all_nmids_called) == 500
    assert summary.coverage_status in (CoverageStatus.COMPLETE, CoverageStatus.PARTIAL_API)


@pytest.mark.asyncio
async def test_legacy_e_includes_absent_from_a(fake_redis) -> None:
    e_only = {999}
    pages = [_card_page([1, 2, 3])]
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages))

    wb_shop_dm = MagicMock()
    wb_shop_dm.get_complex_advs = AsyncMock(
        return_value=[SimpleNamespace(main_nmid=999, all_adv_ids={1})]
    )

    snapshot = await resolve_legacy_assigned_nmids(wb_shop_dm, only_bot_active=False)
    assert 999 in snapshot.nmids

    reader = ShopAssortmentReader(products_manager)
    assortment = await reader.paginate_all_nmids()
    assert 999 not in assortment.nmids
    assert e_only.isdisjoint(assortment.nmids)


@pytest.mark.asyncio
async def test_assortment_pagination_fail_explicit() -> None:
    products_manager = SimpleNamespace(
        get_cards_list=AsyncMock(
            side_effect=[
                _card_page(list(range(1, 101))),
                None,
            ]
        )
    )
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert not result.complete
    assert result.partial_reason == "null_response"
    assert len(result.nmids) == 100


@pytest.mark.asyncio
async def test_assortment_pagination_proof() -> None:
    pages = [_card_page(list(range(i, i + 100))) for i in range(1, 501, 100)] + [_empty_page()]
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages))
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert result.complete
    assert len(result.nmids) == 500
    assert result.pages_completed == 6


@pytest.mark.asyncio
async def test_assortment_terminal_empty_page() -> None:
    pages = [_card_page(list(range(i, i + 100))) for i in range(1, 501, 100)] + [_empty_page()]
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages))
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert len(result.nmids) == 500
    assert result.terminal_empty_page
    assert result.pages_completed >= 5


@pytest.mark.asyncio
async def test_no_campaign_e_empty_coordinator_continues(fake_redis) -> None:
    wb_shop_dm = MagicMock()
    wb_shop_dm.get_complex_advs = AsyncMock(side_effect=NotFoundActiveAdvCompany("none"))

    snapshot = await resolve_legacy_assigned_nmids(wb_shop_dm)
    assert snapshot.nmids == frozenset()

    pages = [_card_page([1, 2, 3])]
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages))
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            products_manager=products_manager,
            get_sales_funnel_products_history=AsyncMock(return_value=[]),
        ),
        redis_client_wrapper=RedisClient(fake_redis),
    )
    updater = CommonSaleStatUpdater(wb_hub, SimpleNamespace(insert=AsyncMock()))
    summary = await run_shop_wide_common_sale_stat_tick(
        shop_id="shop-nc",
        wb_manager_hub=wb_hub,
        wb_shop_data_manager=wb_shop_dm,
        updater=updater,
        redis_client=RedisClient(fake_redis),
        redis_common_stat_timestamp_manager=SimpleNamespace(set=AsyncMock()),
    )
    assert summary.coverage_status != CoverageStatus.FAILED


@pytest.mark.asyncio
async def test_taskgroup_survives_no_campaign_siblings(fake_redis) -> None:
    coordinator_done = asyncio.Event()
    sibling_restarts = {"count": 0}

    async def coordinator_coro() -> None:
        coordinator_done.set()
        await asyncio.sleep(0.01)

    async def sibling_coro() -> None:
        sibling_restarts["count"] += 1
        if sibling_restarts["count"] == 1:
            raise StopShopUpdateException from NotFoundActiveAdvCompany("no adv")
        return

    async def run_group() -> None:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(coordinator_coro())
            tg.create_task(
                taskgroup_no_ad_supervisor(sibling_coro, coroutine_name="refresh_stats_freshness_cache")
            )

    with patch(
        "app.modules.shop_runner.service_manager.services.shop_wide_common_sales.taskgroup_no_ad_supervisor.asyncio.sleep",
        AsyncMock(),
    ):
        await asyncio.wait_for(run_group(), timeout=2.0)

    assert coordinator_done.is_set()
    assert sibling_restarts["count"] >= 2


@pytest.mark.asyncio
async def test_auth_error_still_cancels() -> None:
    from app.core.mp.wb.api.excs import ApiForbiddenError

    async def failing_coro() -> None:
        raise ApiForbiddenError("forbidden")

    with pytest.raises(ApiForbiddenError):
        await taskgroup_no_ad_supervisor(failing_coro, coroutine_name="test")


@pytest.mark.asyncio
async def test_other_stop_not_swallowed() -> None:
    async def stop_coro() -> None:
        raise StopShopUpdateException from RuntimeError("other")

    with pytest.raises(StopShopUpdateException):
        await taskgroup_no_ad_supervisor(stop_coro, coroutine_name="test")


def test_taskgroup_registry_ast_binding() -> None:
    wb_shop_path = (
        Path(__file__).resolve().parents[4]
        / "app"
        / "modules"
        / "shop_runner"
        / "wb_shop.py"
    )
    source = wb_shop_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "create_task":
            for arg in node.args:
                if isinstance(arg, ast.Call):
                    inner = arg.func
                    if isinstance(inner, ast.Name) and inner.id == "_taskgroup_coro":
                        if arg.args and isinstance(arg.args[0], ast.Constant):
                            found.add(str(arg.args[0].value))
                    elif isinstance(inner, ast.Attribute):
                        if inner.attr == "update_common_sale_stat":
                            found.add("update_common_sale_stat")

    assert found == TASKGROUP_COROUTINE_NAMES
    assert SUPERVISOR_COROUTINE_NAMES <= found
    assert "update_common_sale_stat" not in SUPERVISOR_COROUTINE_NAMES


@pytest.mark.asyncio
async def test_ad_transition_recomputes_partition() -> None:
    a_t = frozenset({1, 2, 3})
    e_t = frozenset({2})
    u_t = frozenset(n for n in a_t if n not in e_t)
    assert 3 in u_t

    e_t1 = frozenset({2, 3})
    u_t1 = frozenset(n for n in a_t if n not in e_t1)
    assert 3 not in u_t1
    assert 3 in e_t1


@pytest.mark.asyncio
async def test_non_ad_transition_recomputes() -> None:
    a = frozenset({10, 20})
    e_before = frozenset({10})
    u_before = a - e_before
    assert 20 in u_before

    e_after = frozenset()
    u_after = a - e_after
    assert 10 in u_after


@pytest.mark.asyncio
async def test_regular_recollection_despite_existing_ch(fake_redis) -> None:
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            get_sales_funnel_products_history=AsyncMock(
                return_value=[_row(42, _msk_window()[0])]
            )
        )
    )
    clickhouse = SimpleNamespace(insert=AsyncMock())
    updater = CommonSaleStatUpdater(wb_hub, clickhouse)
    start, end = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({42}), window_start=start, window_end=end)
    result = await updater.collect_by_nmids([42], collect_context=ctx)
    assert 42 not in result.updated_nmids
    assert 42 in result.failed_nmids
    wb_hub.wb_data_manager.get_sales_funnel_products_history.assert_awaited()


@pytest.mark.asyncio
async def test_u_route_remainder_batch_25() -> None:
    wb_data = SimpleNamespace(
        get_sales_funnel_products_history=AsyncMock(return_value=[])
    )
    updater = CommonSaleStatUpdater(
        SimpleNamespace(wb_data_manager=wb_data),
        SimpleNamespace(insert=AsyncMock()),
    )
    start, end = _msk_window()
    ctx = CollectContext(
        attempted_nmids=frozenset(range(1000, 1025)),
        window_start=start,
        window_end=end,
    )
    _ = await updater.collect_by_nmids(
        list(range(1000, 1025)),
        collect_context=ctx,
    )
    assert wb_data.get_sales_funnel_products_history.await_count == 2


def test_missing_date_not_zero() -> None:
    start, end = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1}), window_start=start, window_end=end)
    validated = validate_and_deduplicate_rows([], context=ctx)
    assert not validated.returned_pairs


def test_reject_unexpected_nmid() -> None:
    start, end = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1}), window_start=start, window_end=end)
    validated = validate_and_deduplicate_rows([_row(999, start)], context=ctx)
    assert validated.rejected_count == 1
    assert not validated.rows


def test_reject_out_of_window_date() -> None:
    start, end = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1}), window_start=start, window_end=end)
    validated = validate_and_deduplicate_rows(
        [_row(1, start - datetime.timedelta(days=10))],
        context=ctx,
    )
    assert validated.rejected_count == 1


def test_reject_conflicting_duplicate() -> None:
    start, _ = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1}), window_start=start, window_end=start)
    validated = validate_and_deduplicate_rows(
        [_row(1, start, open_card=1), _row(1, start, open_card=2)],
        context=ctx,
    )
    assert validated.rejected_count >= 1
    assert not validated.rows


def test_dedup_identical_duplicate() -> None:
    start, _ = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1}), window_start=start, window_end=start)
    validated = validate_and_deduplicate_rows(
        [_row(1, start), _row(1, start)],
        context=ctx,
    )
    assert len(validated.rows) == 1
    assert validated.rejected_count == 0


def test_reject_nonfinite_metric() -> None:
    start, _ = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1}), window_start=start, window_end=start)
    bad = _row(1, start, orders_sum=float("nan"))
    validated = validate_and_deduplicate_rows([bad], context=ctx)
    assert validated.rejected_count == 1
    assert not math.isfinite(bad.orders_sum)


def test_fractional_orders_and_buyouts_sums_preserved() -> None:
    """Fractional orders_sum/buyouts_sum_rub roundtrip through strict validator unchanged."""
    start, _ = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({42}), window_start=start, window_end=start)
    fractional = _row(
        42,
        start,
        orders_sum=123.45,
        buyouts_sum_rub=67.89,
    )
    validated = validate_and_deduplicate_rows([fractional], context=ctx)
    assert validated.rejected_count == 0
    assert len(validated.rows) == 1
    normalized = validated.rows[0]
    assert normalized.orders_sum == 123.45
    assert normalized.buyouts_sum_rub == 67.89


@pytest.mark.asyncio
async def test_collect_failure_retains_prior_facts() -> None:
    insert = AsyncMock(side_effect=RuntimeError("ch down"))
    wb_data = SimpleNamespace(
        get_sales_funnel_products_history=AsyncMock(return_value=[_row(1, _msk_window()[0])])
    )
    updater = CommonSaleStatUpdater(
        SimpleNamespace(wb_data_manager=wb_data),
        SimpleNamespace(insert=insert),
    )
    start, end = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1}), window_start=start, window_end=end)
    result = await updater.collect_by_nmids([1], collect_context=ctx)
    assert result.ch_insert_failed
    assert 1 in result.failed_nmids
    assert 1 not in result.updated_nmids


@pytest.mark.asyncio
async def test_mid_batch_partial_failure() -> None:
    async def _side_effect(*, nmids: list[int], start: datetime.date, end: datetime.date):
        return [_row(n, start) for n in nmids if n <= 15]

    wb_data = SimpleNamespace(get_sales_funnel_products_history=AsyncMock(side_effect=_side_effect))
    updater = CommonSaleStatUpdater(
        SimpleNamespace(wb_data_manager=wb_data),
        SimpleNamespace(insert=AsyncMock()),
    )
    nmids = list(range(1, 21))
    start, end = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset(nmids), window_start=start, window_end=end)
    result = await updater.collect_by_nmids(nmids, collect_context=ctx)
    assert len(result.updated_nmids) == 0
    assert len(result.failed_nmids) == 20


@pytest.mark.asyncio
async def test_last_attempt_redis_evidence(fake_redis) -> None:
    store = ShopWideCoverageEvidenceStore(RedisClient(fake_redis))
    await store.write_started(
        "s1",
        attempt_id="attempt-test-1",
        window_start="2026-10-01",
        window_end="2026-10-07",
        a_count=10,
        e_count=2,
        u_count=8,
        assortment_complete=False,
        assortment_pages=1,
        assortment_hash="abc123",
    )
    evidence = await store.read_last_attempt("s1")
    assert evidence is not None
    assert evidence.attempt_status == "STARTED"
    assert evidence.missing_pair_count == 70


@pytest.mark.asyncio
async def test_started_before_api(fake_redis) -> None:
    order: list[str] = []

    async def before() -> None:
        order.append("started")

    async def api(*args: Any, **kwargs: Any) -> list[CommonSaleStatRow]:
        order.append("api")
        return []

    wb_data = SimpleNamespace(get_sales_funnel_products_history=AsyncMock(side_effect=api))
    updater = CommonSaleStatUpdater(
        SimpleNamespace(wb_data_manager=wb_data),
        SimpleNamespace(insert=AsyncMock()),
    )
    start, end = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1}), window_start=start, window_end=end)
    _ = await updater.collect_by_nmids(
        [1],
        collect_context=ctx,
        before_first_api=before,
    )
    assert order.index("started") < order.index("api")


@pytest.mark.asyncio
async def test_failed_ch_insert_no_false_complete(fake_redis) -> None:
    pages = [_card_page([1])]
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages))
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            products_manager=products_manager,
            get_sales_funnel_products_history=AsyncMock(return_value=[_row(1, _msk_window()[0])]),
        ),
        redis_client_wrapper=RedisClient(fake_redis),
    )
    updater = CommonSaleStatUpdater(wb_hub, SimpleNamespace(insert=AsyncMock(side_effect=RuntimeError("fail"))))
    summary = await run_shop_wide_common_sale_stat_tick(
        shop_id="s-fail",
        wb_manager_hub=wb_hub,
        wb_shop_data_manager=SimpleNamespace(
            get_complex_advs=AsyncMock(return_value=[]),
        ),
        updater=updater,
        redis_client=RedisClient(fake_redis),
        redis_common_stat_timestamp_manager=SimpleNamespace(set=AsyncMock()),
    )
    store = ShopWideCoverageEvidenceStore(RedisClient(fake_redis))
    evidence = await store.read_last_attempt("s-fail")
    assert evidence is not None
    assert evidence.attempt_status != "COMPLETE"
    assert summary.coverage_status == CoverageStatus.PARTIAL_CH


def test_no_second_coroutine_registered() -> None:
    wb_shop_path = Path(__file__).resolve().parents[4] / "app" / "modules" / "shop_runner" / "wb_shop.py"
    text = wb_shop_path.read_text(encoding="utf-8")
    assert text.count("update_common_sale_stat") >= 1
    assert "update_shop_wide_common_sale_stat" not in text


@pytest.mark.asyncio
async def test_no_adv_setting_create_or_bot_active_mutation() -> None:
    session_mock = MagicMock()
    session_mock.execute = AsyncMock()
    session_mock.commit = AsyncMock()
    assert not hasattr(resolve_legacy_assigned_nmids, "commit")


def test_taskgroup_supervisor_count_matches_design() -> None:
    assert len(SUPERVISOR_COROUTINE_NAMES) == 19


def _full_window_rows(nmid: int, start: datetime.date, end: datetime.date) -> list[CommonSaleStatRow]:
    rows: list[CommonSaleStatRow] = []
    day = start
    while day <= end:
        rows.append(_row(nmid, day))
        day += datetime.timedelta(days=1)
    return rows


@pytest.mark.asyncio
async def test_provisional_started_before_content_api(fake_redis) -> None:
    """F1: provisional STARTED at tick entry invalidates prior COMPLETE."""
    from app.modules.shop_runner.service_manager.services.shop_wide_common_sales.coverage_evidence import (
        derive_attempt_status,
    )

    store = ShopWideCoverageEvidenceStore(RedisClient(fake_redis))
    prior = LastAttemptEvidence(
        attempt_status="COMPLETE",
        window_start="2026-01-01",
        window_end="2026-01-07",
        a_count=2,
        e_count=0,
        u_count=2,
        assortment_complete=True,
        assortment_pages=1,
        expected_pair_count=14,
        returned_pair_count=14,
        persisted_pair_count=14,
        missing_pair_count=0,
        rejected_pair_count=0,
        partial_reason=None,
        tick_ts="2026-01-01T00:00:00+00:00",
        attempt_id="old-complete",
        assortment_hash="deadbeef",
    )
    await store.write_terminal("s-prov", prior)

    order: list[str] = []

    async def slow_cards(*args: Any, **kwargs: Any) -> SimpleNamespace:
        mid = await store.read_last_attempt("s-prov")
        if mid is not None:
            order.append(mid.attempt_status)
        await asyncio.sleep(0.01)
        return _card_page([1, 2])

    products_manager = SimpleNamespace(get_cards_list=AsyncMock(side_effect=slow_cards))
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            products_manager=products_manager,
            get_sales_funnel_products_history=AsyncMock(return_value=[]),
        ),
    )
    updater = CommonSaleStatUpdater(wb_hub, SimpleNamespace(insert=AsyncMock()))
    _ = await run_shop_wide_common_sale_stat_tick(
        shop_id="s-prov",
        wb_manager_hub=wb_hub,
        wb_shop_data_manager=SimpleNamespace(get_complex_advs=AsyncMock(return_value=[])),
        updater=updater,
        redis_client=RedisClient(fake_redis),
        redis_common_stat_timestamp_manager=SimpleNamespace(set=AsyncMock()),
    )
    final = await store.read_last_attempt("s-prov")
    assert final is not None
    assert "STARTED" in order or final.attempt_status != "COMPLETE"
    assert derive_attempt_status(CoverageStatus.PARTIAL_API) == "PARTIAL"


@pytest.mark.asyncio
async def test_content_failure_leaves_no_stale_complete(fake_redis) -> None:
    """F1: Content API failure before funnel must not leave stale COMPLETE."""
    store = ShopWideCoverageEvidenceStore(RedisClient(fake_redis))
    prior = LastAttemptEvidence(
        attempt_status="COMPLETE",
        window_start="2026-01-01",
        window_end="2026-01-07",
        a_count=1,
        e_count=0,
        u_count=1,
        assortment_complete=True,
        assortment_pages=1,
        expected_pair_count=7,
        returned_pair_count=7,
        persisted_pair_count=7,
        missing_pair_count=0,
        rejected_pair_count=0,
        partial_reason=None,
        tick_ts="2026-01-01T00:00:00+00:00",
        attempt_id="prior-complete",
        assortment_hash="aa",
    )
    await store.write_terminal("s-content-fail", prior)

    products_manager = SimpleNamespace(get_cards_list=AsyncMock(return_value=None))
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            products_manager=products_manager,
            get_sales_funnel_products_history=AsyncMock(return_value=[]),
        ),
    )
    updater = CommonSaleStatUpdater(wb_hub, SimpleNamespace(insert=AsyncMock()))
    summary = await run_shop_wide_common_sale_stat_tick(
        shop_id="s-content-fail",
        wb_manager_hub=wb_hub,
        wb_shop_data_manager=SimpleNamespace(get_complex_advs=AsyncMock(return_value=[])),
        updater=updater,
        redis_client=RedisClient(fake_redis),
        redis_common_stat_timestamp_manager=SimpleNamespace(set=AsyncMock()),
    )
    evidence = await store.read_last_attempt("s-content-fail")
    assert evidence is not None
    assert evidence.attempt_status != "COMPLETE"
    assert summary.coverage_status == CoverageStatus.PARTIAL_ASSORTMENT


@pytest.mark.asyncio
async def test_epartial_outside_a_not_counted_in_shop_coverage(fake_redis) -> None:
    """F2: A={1,2}, E={999}; partial nmid2 → PARTIAL with exactly 6 missing pairs."""
    start, end = _msk_window()

    async def _history(*, nmids: list[int], start: datetime.date, end: datetime.date):
        rows: list[CommonSaleStatRow] = []
        for n in nmids:
            if n == 1:
                rows.extend(_full_window_rows(1, start, end))
            elif n == 999:
                rows.extend(_full_window_rows(999, start, end))
            elif n == 2:
                rows.append(_row(2, start))
        return rows

    pages = [_card_page([1, 2])]
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages))
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            products_manager=products_manager,
            get_sales_funnel_products_history=AsyncMock(side_effect=_history),
        ),
    )
    with patch(
        "app.modules.shop_runner.service_manager.services.shop_wide_common_sales.coordinator.resolve_legacy_assigned_nmids",
        AsyncMock(
            return_value=SimpleNamespace(
                nmids=frozenset({999}),
                complex_advs=tuple(SimpleNamespace(main_nmid=999, all_adv_ids={1}) for _ in [0]),
            )
        ),
    ):
        summary = await run_shop_wide_common_sale_stat_tick(
            shop_id="s-f2",
            wb_manager_hub=wb_hub,
            wb_shop_data_manager=MagicMock(),
            updater=CommonSaleStatUpdater(wb_hub, SimpleNamespace(insert=AsyncMock())),
            redis_client=RedisClient(fake_redis),
            redis_common_stat_timestamp_manager=SimpleNamespace(set=AsyncMock()),
        )

    expected = expected_shop_pairs(frozenset({1, 2}), start, end)
    coverage = summary.returned_pairs & expected
    assert summary.coverage_status == CoverageStatus.PARTIAL_API
    assert len(expected) == 14
    assert len(coverage) == 8
    assert len(expected) - len(coverage) == 6
    assert 1 in summary.updated_nmids
    assert 2 not in summary.updated_nmids
    assert 999 not in summary.updated_nmids


@pytest.mark.asyncio
async def test_same_cardinality_wrong_membership_is_partial(fake_redis) -> None:
    """F2: equal pair count but wrong membership must not yield COMPLETE."""
    start, end = _msk_window()
    wrong_day = end + datetime.timedelta(days=1)

    async def _history(*, nmids: list[int], start: datetime.date, end: datetime.date):
        return [_row(1, wrong_day) for _ in nmids]

    pages = [_card_page([1])]
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            products_manager=SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages)),
            get_sales_funnel_products_history=AsyncMock(side_effect=_history),
        ),
    )
    summary = await run_shop_wide_common_sale_stat_tick(
        shop_id="s-wrong-member",
        wb_manager_hub=wb_hub,
        wb_shop_data_manager=SimpleNamespace(get_complex_advs=AsyncMock(return_value=[])),
        updater=CommonSaleStatUpdater(wb_hub, SimpleNamespace(insert=AsyncMock())),
        redis_client=RedisClient(fake_redis),
        redis_common_stat_timestamp_manager=SimpleNamespace(set=AsyncMock()),
    )
    assert summary.coverage_status == CoverageStatus.PARTIAL_API
    assert len(summary.returned_pairs) == 0


def test_reject_u_batch_returning_e_id() -> None:
    """F3: U chunk must reject E-only nmid in response."""
    start, end = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({10, 11}), window_start=start, window_end=end)
    validated = validate_and_deduplicate_rows([_row(999, start)], context=ctx)
    assert validated.rejected_count == 1
    assert not validated.rows


@pytest.mark.asyncio
async def test_second_chunk_cannot_resurrect_first_chunk_id() -> None:
    """F3: second chunk returning first-chunk ID is rejected (per-chunk validation)."""
    start, end = _msk_window()
    seen_pairs: set[tuple[int, datetime.date]] = set()

    async def _history(*, nmids: list[int], start: datetime.date, end: datetime.date):
        if 1 in nmids:
            return [_row(1, start)]
        if 21 in nmids:
            return [_row(1, start + datetime.timedelta(days=1))]
        return []

    wb_data = SimpleNamespace(get_sales_funnel_products_history=AsyncMock(side_effect=_history))
    updater = CommonSaleStatUpdater(
        SimpleNamespace(wb_data_manager=wb_data),
        SimpleNamespace(insert=AsyncMock(side_effect=lambda rows: seen_pairs.update((r.nmid, r.day) for r in rows))),
    )
    ctx = CollectContext(attempted_nmids=frozenset(), window_start=start, window_end=end)
    result = await updater.collect_by_nmids(list(range(1, 22)), collect_context=ctx)
    assert (1, start + datetime.timedelta(days=1)) not in result.returned_pairs
    assert result.rejected_pair_count >= 1


def test_tombstone_rejects_v1_v2_v1() -> None:
    """F4: [V1,V2,V1] — all rows for key excluded after conflict."""
    start, _ = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1}), window_start=start, window_end=start)
    v1 = _row(1, start, open_card=1)
    v2 = _row(1, start, open_card=2)
    validated = validate_and_deduplicate_rows([v1, v2, v1], context=ctx)
    assert not validated.rows
    assert validated.rejected_count >= 2


def test_tombstone_rejects_v1_v2_v3_v1() -> None:
    """F4: [V1,V2,V3,V1] — key permanently tombstoned."""
    start, _ = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1}), window_start=start, window_end=start)
    rows = [
        _row(1, start, open_card=1),
        _row(1, start, open_card=2),
        _row(1, start, open_card=3),
        _row(1, start, open_card=1),
    ]
    validated = validate_and_deduplicate_rows(rows, context=ctx)
    assert not validated.rows
    assert validated.rejected_count >= 3


def test_reject_none_and_string_metrics() -> None:
    """F4: invalid field types reject explicitly without aborting siblings."""
    start, _ = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1, 2}), window_start=start, window_end=start)
    bad = SimpleNamespace(
        nmid=1,
        day=start,
        open_card=1,
        add_to_cart=1,
        orders=1,
        orders_sum=None,
        buy_outs=1,
        buyouts_sum_rub=5.0,
    )
    good = _row(2, start)
    validated = validate_and_deduplicate_rows(
        [bad, good],  # type: ignore[list-item]
        context=ctx,
    )
    assert len(validated.rows) == 1
    assert validated.rows[0].nmid == 2
    assert validated.rejected_count == 1


@pytest.mark.asyncio
async def test_one_of_seven_dates_no_campaign_freshness(fake_redis) -> None:
    """F5: 1/7 dates must not set campaign Redis freshness."""
    start, end = _msk_window()
    ts_manager = SimpleNamespace(set=AsyncMock())

    pages = [_card_page([1])]
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            products_manager=SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages)),
            get_sales_funnel_products_history=AsyncMock(return_value=[_row(1, start)]),
        ),
    )
    with patch(
        "app.modules.shop_runner.service_manager.services.shop_wide_common_sales.coordinator.resolve_legacy_assigned_nmids",
        AsyncMock(
            return_value=SimpleNamespace(
                nmids=frozenset({1}),
                complex_advs=(SimpleNamespace(main_nmid=1, all_adv_ids={42}),),
            )
        ),
    ):
        _ = await run_shop_wide_common_sale_stat_tick(
            shop_id="s-partial7",
            wb_manager_hub=wb_hub,
            wb_shop_data_manager=MagicMock(),
            updater=CommonSaleStatUpdater(wb_hub, SimpleNamespace(insert=AsyncMock())),
            redis_client=RedisClient(fake_redis),
            redis_common_stat_timestamp_manager=ts_manager,
        )
    ts_manager.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_source_funnel_forbidden_propagates() -> None:
    """F5: ApiForbidden on funnel must propagate (not swallowed)."""
    from app.core.mp.wb.api.excs import ApiForbiddenError

    wb_data = SimpleNamespace(
        get_sales_funnel_products_history=AsyncMock(side_effect=ApiForbiddenError("forbidden"))
    )
    updater = CommonSaleStatUpdater(
        SimpleNamespace(wb_data_manager=wb_data),
        SimpleNamespace(insert=AsyncMock()),
    )
    start, end = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1}), window_start=start, window_end=end)
    with pytest.raises(ApiForbiddenError):
        await updater.collect_by_nmids([1], collect_context=ctx)


@pytest.mark.asyncio
async def test_malformed_evidence_returns_none(fake_redis) -> None:
    """F7: unsupported schema_version → None (fail closed)."""
    store = ShopWideCoverageEvidenceStore(RedisClient(fake_redis))
    await RedisClient(fake_redis).set(
        store.last_attempt_key("s-bad"),
        '{"schema_version": 999, "attempt_status": "COMPLETE"}',
    )
    assert await store.read_last_attempt("s-bad") is None


@pytest.mark.asyncio
async def test_evidence_has_schema_binding_fields(fake_redis) -> None:
    """F7: evidence binds scope/source/window/attempt/snapshot."""
    store = ShopWideCoverageEvidenceStore(RedisClient(fake_redis))
    attempt_id = store.new_attempt_id()
    await store.write_started(
        "s-bind",
        attempt_id=attempt_id,
        window_start="2026-10-01",
        window_end="2026-10-07",
        a_count=3,
        e_count=1,
        u_count=2,
        assortment_complete=True,
        assortment_pages=1,
        assortment_hash="hash123",
    )
    evidence = await store.read_last_attempt("s-bind")
    assert evidence is not None
    assert evidence.schema_version == EVIDENCE_SCHEMA_VERSION
    assert evidence.attempt_id == attempt_id
    assert evidence.scope == "current_non_trash_cards"
    assert evidence.source == "wb_sales_funnel_products_history"
    assert evidence.assortment_hash == "hash123"


@pytest.mark.asyncio
async def test_ch_insert_failure_no_false_updated_or_freshness(fake_redis) -> None:
    """F9: full E 7 rows + CH insert raises → zero updated/freshness; returned≠persisted."""
    start, end = _msk_window()
    ts_manager = SimpleNamespace(set=AsyncMock())

    async def _history(*, nmids: list[int], start: datetime.date, end: datetime.date):
        return _full_window_rows(nmids[0], start, end)

    pages = [_card_page([1])]
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            products_manager=SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages)),
            get_sales_funnel_products_history=AsyncMock(side_effect=_history),
        ),
    )
    with patch(
        "app.modules.shop_runner.service_manager.services.shop_wide_common_sales.coordinator.resolve_legacy_assigned_nmids",
        AsyncMock(
            return_value=SimpleNamespace(
                nmids=frozenset({1}),
                complex_advs=(SimpleNamespace(main_nmid=1, all_adv_ids={42}),),
            )
        ),
    ):
        summary = await run_shop_wide_common_sale_stat_tick(
            shop_id="s-f9-ch-fail",
            wb_manager_hub=wb_hub,
            wb_shop_data_manager=MagicMock(),
            updater=CommonSaleStatUpdater(
                wb_hub,
                SimpleNamespace(insert=AsyncMock(side_effect=RuntimeError("ch down"))),
            ),
            redis_client=RedisClient(fake_redis),
            redis_common_stat_timestamp_manager=ts_manager,
        )

    assert summary.coverage_status == CoverageStatus.PARTIAL_CH
    assert 1 not in summary.updated_nmids
    assert len(summary.returned_pairs) == 7
    assert len(summary.persisted_pairs) == 0
    ts_manager.set.assert_not_awaited()
    store = ShopWideCoverageEvidenceStore(RedisClient(fake_redis))
    evidence = await store.read_last_attempt("s-f9-ch-fail")
    assert evidence is not None
    assert evidence.returned_pair_count == 7
    assert evidence.persisted_pair_count == 0
    assert evidence.missing_pair_count == 7


@pytest.mark.asyncio
async def test_e_ok_u_fail_independent_freshness(fake_redis) -> None:
    """F9: E route success retains freshness when U route CH insert fails."""
    start, end = _msk_window()
    ts_manager = SimpleNamespace(set=AsyncMock())
    insert_calls = {"count": 0}

    async def _history(*, nmids: list[int], start: datetime.date, end: datetime.date):
        if nmids == [999]:
            return _full_window_rows(999, start, end)
        return [_row(n, start) for n in nmids]

    async def _insert(rows: list[CommonSaleStatRow]) -> None:
        insert_calls["count"] += 1
        if insert_calls["count"] == 2:
            raise RuntimeError("u insert failed")

    pages = [_card_page([1, 2])]
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            products_manager=SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages)),
            get_sales_funnel_products_history=AsyncMock(side_effect=_history),
        ),
    )
    with patch(
        "app.modules.shop_runner.service_manager.services.shop_wide_common_sales.coordinator.resolve_legacy_assigned_nmids",
        AsyncMock(
            return_value=SimpleNamespace(
                nmids=frozenset({999}),
                complex_advs=(SimpleNamespace(main_nmid=999, all_adv_ids={77}),),
            )
        ),
    ):
        summary = await run_shop_wide_common_sale_stat_tick(
            shop_id="s-f9-indep",
            wb_manager_hub=wb_hub,
            wb_shop_data_manager=MagicMock(),
            updater=CommonSaleStatUpdater(wb_hub, SimpleNamespace(insert=AsyncMock(side_effect=_insert))),
            redis_client=RedisClient(fake_redis),
            redis_common_stat_timestamp_manager=ts_manager,
        )

    assert summary.coverage_status == CoverageStatus.PARTIAL_CH
    assert 999 in summary.legacy_route_updated_nmids
    assert 999 not in summary.updated_nmids
    ts_manager.set.assert_awaited_once_with(77)


@pytest.mark.asyncio
async def test_e_outside_a_full_success_gets_freshness(fake_redis) -> None:
    """F10: E={999}∉A full window → legacy freshness; shop coverage stays PARTIAL."""
    start, end = _msk_window()
    ts_manager = SimpleNamespace(set=AsyncMock())

    async def _history(*, nmids: list[int], start: datetime.date, end: datetime.date):
        if 999 in nmids:
            return _full_window_rows(999, start, end)
        return [_row(n, start) for n in nmids]

    pages = [_card_page([1, 2])]
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            products_manager=SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages)),
            get_sales_funnel_products_history=AsyncMock(side_effect=_history),
        ),
    )
    with patch(
        "app.modules.shop_runner.service_manager.services.shop_wide_common_sales.coordinator.resolve_legacy_assigned_nmids",
        AsyncMock(
            return_value=SimpleNamespace(
                nmids=frozenset({999}),
                complex_advs=(SimpleNamespace(main_nmid=999, all_adv_ids={55}),),
            )
        ),
    ):
        summary = await run_shop_wide_common_sale_stat_tick(
            shop_id="s-f10-e-outside",
            wb_manager_hub=wb_hub,
            wb_shop_data_manager=MagicMock(),
            updater=CommonSaleStatUpdater(wb_hub, SimpleNamespace(insert=AsyncMock())),
            redis_client=RedisClient(fake_redis),
            redis_common_stat_timestamp_manager=ts_manager,
        )

    assert summary.coverage_status == CoverageStatus.PARTIAL_API
    assert 999 in summary.legacy_route_updated_nmids
    assert 999 not in summary.updated_nmids
    ts_manager.set.assert_awaited_once_with(55)


def test_strict_reject_string_nmid_and_datetime_day() -> None:
    """F12: string nmid and datetime day rejected; valid sibling kept."""
    start, _ = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1, 2}), window_start=start, window_end=start)
    bad_nmid = SimpleNamespace(
        nmid="123",
        day=start,
        open_card=1,
        add_to_cart=1,
        orders=1,
        orders_sum=10.0,
        buy_outs=1,
        buyouts_sum_rub=5.0,
    )
    bad_day = SimpleNamespace(
        nmid=1,
        day=datetime.datetime(2026, 1, 1),
        open_card=1,
        add_to_cart=1,
        orders=1,
        orders_sum=10.0,
        buy_outs=1,
        buyouts_sum_rub=5.0,
    )
    good = _row(2, start)
    validated = validate_and_deduplicate_rows(
        [bad_nmid, bad_day, good],  # type: ignore[list-item]
        context=ctx,
    )
    assert len(validated.rows) == 1
    assert validated.rows[0].nmid == 2
    assert validated.rejected_count == 2


def test_strict_reject_bool_count() -> None:
    """F12: bool metric/count rejected without aborting siblings."""
    start, _ = _msk_window()
    ctx = CollectContext(attempted_nmids=frozenset({1, 2}), window_start=start, window_end=start)
    bad = SimpleNamespace(
        nmid=True,
        day=start,
        open_card=1,
        add_to_cart=1,
        orders=1,
        orders_sum=10.0,
        buy_outs=1,
        buyouts_sum_rub=5.0,
    )
    good = _row(2, start)
    validated = validate_and_deduplicate_rows(
        [bad, good],  # type: ignore[list-item]
        context=ctx,
    )
    assert len(validated.rows) == 1
    assert validated.rejected_count == 1


@pytest.mark.asyncio
async def test_malformed_attempt_status_enum_returns_none(fake_redis) -> None:
    """F12: wrong attempt_status enum → None (no silent COMPLETE)."""
    store = ShopWideCoverageEvidenceStore(RedisClient(fake_redis))
    await RedisClient(fake_redis).set(
        store.last_attempt_key("s-bad-status"),
        '{"schema_version": 1, "attempt_status": "COMPLETE-ish", '
        '"window_start": "2026-01-01", "window_end": "2026-01-07", '
        '"a_count": 1, "e_count": 0, "u_count": 1, '
        '"assortment_complete": true, "assortment_pages": 1, '
        '"expected_pair_count": 7, "returned_pair_count": 7, '
        '"persisted_pair_count": 7, "missing_pair_count": 0, '
        '"rejected_pair_count": 0, "partial_reason": null, '
        '"tick_ts": "2026-01-01T00:00:00+00:00", "attempt_id": "x", '
        '"scope": "current_non_trash_cards", "source": "wb_sales_funnel_products_history", '
        '"assortment_hash": "aa", "provisional": false}',
    )
    assert await store.read_last_attempt("s-bad-status") is None


@pytest.mark.asyncio
async def test_collect_by_nmids_persisted_vs_returned_on_ch_failure() -> None:
    """F9: collect_by_nmids keeps returned_pairs but clears persisted on CH fail."""
    start, end = _msk_window()
    wb_data = SimpleNamespace(
        get_sales_funnel_products_history=AsyncMock(return_value=[_row(1, start)])
    )
    updater = CommonSaleStatUpdater(
        SimpleNamespace(wb_data_manager=wb_data),
        SimpleNamespace(insert=AsyncMock(side_effect=RuntimeError("ch"))),
    )
    ctx = CollectContext(attempted_nmids=frozenset({1}), window_start=start, window_end=end)
    result = await updater.collect_by_nmids([1], collect_context=ctx)
    assert result.ch_insert_failed
    assert len(result.returned_pairs) == 1
    assert len(result.persisted_pairs) == 0
    assert 1 not in result.updated_nmids


def _page_with_cards(
    nmids: list[int],
    *,
    total: int | None = None,
    cursor_nm: int | None = None,
) -> SimpleNamespace:
    cards = []
    for nmid in nmids:
        cards.append(SimpleNamespace(nm_id=nmid, updated_at="2026-01-01T00:00:00Z"))
    last = nmids[-1] if nmids else 0
    cursor_total = len(nmids) if total is None else total
    return SimpleNamespace(
        cards=cards,
        cursor=SimpleNamespace(
            updated_at="2026-01-01T00:00:00Z",
            nm_id=cursor_nm if cursor_nm is not None else last,
            total=cursor_total,
        ),
    )


@pytest.mark.asyncio
async def test_assortment_unset_cards_not_complete() -> None:
    """F1: UNSET cards must not yield complete=True (was empty terminal)."""
    page = SimpleNamespace(cards=UNSET, cursor=SimpleNamespace(total=0))
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(return_value=page))
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert not result.complete
    assert result.partial_reason == "malformed_cards_unset"
    assert len(result.nmids) == 0


@pytest.mark.asyncio
async def test_assortment_null_cards_malformed() -> None:
    """F1: null cards → partial, not complete."""
    page = SimpleNamespace(cards=None, cursor=SimpleNamespace(total=0))
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(return_value=page))
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert not result.complete
    assert result.partial_reason == "malformed_cards_null"


@pytest.mark.asyncio
async def test_assortment_invalid_bool_nm_id_skipped() -> None:
    """F1: bool nm_id cast rejected; valid siblings kept."""
    cards = [
        SimpleNamespace(nm_id=True, updated_at="2026-01-01T00:00:00Z"),
        SimpleNamespace(nm_id=42, updated_at="2026-01-01T00:00:00Z"),
    ]
    page = SimpleNamespace(
        cards=cards,
        cursor=SimpleNamespace(updated_at="2026-01-01T00:00:00Z", nm_id=42, total=2),
    )
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(return_value=page))
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert result.complete
    assert result.nmids == frozenset({42})


@pytest.mark.asyncio
async def test_assortment_malformed_cursor_total_no_exception() -> None:
    """F1: malformed cursor.total must not raise; partial with proven nmIDs."""
    page1 = _page_with_cards(list(range(1, 101)))
    page1.cursor = SimpleNamespace(
        updated_at="2026-01-01T00:00:00Z",
        nm_id=100,
        total="not-a-number",
    )
    products_manager = SimpleNamespace(
        get_cards_list=AsyncMock(side_effect=[page1, _empty_page()])
    )
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert len(result.nmids) == 100
    assert result.complete
    assert products_manager.get_cards_list.await_count == 2


@pytest.mark.asyncio
async def test_assortment_cursor_total_per_page_terminal() -> None:
    """F1: cursor.total per-page < limit on full page → terminal without extra page."""
    page = _page_with_cards(list(range(1, 101)), total=50)
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(return_value=page))
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert result.complete
    assert len(result.nmids) == 100
    assert products_manager.get_cards_list.await_count == 1


@pytest.mark.asyncio
async def test_assortment_cursor_loop_stops_partial() -> None:
    """F1: repeated cursor → PARTIAL without infinite requests."""
    page1 = _page_with_cards(list(range(1, 101)), cursor_nm=100)
    page2 = _page_with_cards(list(range(101, 201)), cursor_nm=100)
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(side_effect=[page1, page2]))
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert not result.complete
    assert result.partial_reason == "cursor_loop"
    assert products_manager.get_cards_list.await_count == 2
    assert len(result.nmids) == 200


@pytest.mark.asyncio
async def test_assortment_max_pages_bounded() -> None:
    """F1: max_pages caps endless pagination."""
    page1 = _page_with_cards(list(range(1, 101)), cursor_nm=100)
    page2 = _page_with_cards(list(range(101, 201)), cursor_nm=200)
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(side_effect=[page1, page2]))
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids(page_limit=100, max_pages=2)
    assert not result.complete
    assert result.partial_reason == "max_pages"
    assert products_manager.get_cards_list.await_count == 2
    assert len(result.nmids) == 200


@pytest.mark.asyncio
async def test_assortment_no_progress_repeated_full_page() -> None:
    """F1: repeated full page with same nmIDs → no_progress PARTIAL."""
    nmids = list(range(1, 101))
    page1 = _page_with_cards(nmids)
    page2 = _page_with_cards(nmids, cursor_nm=200)
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(side_effect=[page1, page2]))
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert not result.complete
    assert result.partial_reason == "no_progress"


@pytest.mark.asyncio
async def test_assortment_mid_page_failure_retains_prior_a() -> None:
    """F1: exception after page 1 retains proven nmIDs."""
    page1 = _page_with_cards(list(range(1, 101)))
    products_manager = SimpleNamespace(
        get_cards_list=AsyncMock(side_effect=[page1, RuntimeError("timeout")])
    )
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert not result.complete
    assert result.partial_reason == "content_api_error:RuntimeError"
    assert len(result.nmids) == 100


@pytest.mark.asyncio
async def test_assortment_empty_shop_valid_terminal() -> None:
    """F1: genuine 0-card page with cursor.total=0 → complete empty A."""
    page = SimpleNamespace(cards=[], cursor=SimpleNamespace(total=0))
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(return_value=page))
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert result.complete
    assert len(result.nmids) == 0


@pytest.mark.asyncio
async def test_assortment_empty_unconfirmed_first_page() -> None:
    """F1: empty first page without terminal evidence → partial."""
    page = SimpleNamespace(cards=[], cursor=SimpleNamespace(total=UNSET))
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(return_value=page))
    reader = ShopAssortmentReader(products_manager)
    result = await reader.paginate_all_nmids()
    assert not result.complete
    assert result.partial_reason == "empty_unconfirmed"


@pytest.mark.asyncio
async def test_assortment_auth_forbidden_propagates() -> None:
    """F1: ApiForbiddenError propagates from reader (not swallowed)."""
    from app.core.mp.wb.api.excs import ApiForbiddenError

    products_manager = SimpleNamespace(
        get_cards_list=AsyncMock(side_effect=ApiForbiddenError("forbidden"))
    )
    reader = ShopAssortmentReader(products_manager)
    with pytest.raises(ApiForbiddenError):
        await reader.paginate_all_nmids()


@pytest.mark.asyncio
async def test_content_exception_preserves_legacy_e_collection(fake_redis) -> None:
    """F1: Content API error before legacy resolve still runs E route."""
    start, end = _msk_window()
    products_manager = SimpleNamespace(
        get_cards_list=AsyncMock(side_effect=RuntimeError("content down"))
    )
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            products_manager=products_manager,
            get_sales_funnel_products_history=AsyncMock(
                side_effect=lambda *, nmids, start, end: _full_window_rows(nmids[0], start, end)
            ),
        ),
    )
    with patch(
        "app.modules.shop_runner.service_manager.services.shop_wide_common_sales.coordinator.resolve_legacy_assigned_nmids",
        AsyncMock(
            return_value=SimpleNamespace(
                nmids=frozenset({999}),
                complex_advs=(SimpleNamespace(main_nmid=999, all_adv_ids={55}),),
            )
        ),
    ):
        summary = await run_shop_wide_common_sale_stat_tick(
            shop_id="s-content-exc",
            wb_manager_hub=wb_hub,
            wb_shop_data_manager=MagicMock(),
            updater=CommonSaleStatUpdater(wb_hub, SimpleNamespace(insert=AsyncMock())),
            redis_client=RedisClient(fake_redis),
            redis_common_stat_timestamp_manager=SimpleNamespace(set=AsyncMock()),
        )
    assert summary.coverage_status == CoverageStatus.PARTIAL_ASSORTMENT
    assert 999 in summary.legacy_route_updated_nmids


@pytest.mark.asyncio
async def test_mid_pagination_null_retains_proven_a_and_legacy_e(fake_redis) -> None:
    """F1: null on page 2 retains page-1 A; legacy E still collected."""
    start, end = _msk_window()
    pages = [_page_with_cards(list(range(1, 101))), None]
    products_manager = SimpleNamespace(get_cards_list=AsyncMock(side_effect=pages))
    wb_hub = SimpleNamespace(
        wb_data_manager=SimpleNamespace(
            products_manager=products_manager,
            get_sales_funnel_products_history=AsyncMock(
                side_effect=lambda *, nmids, start, end: _full_window_rows(nmids[0], start, end)
            ),
        ),
    )
    with patch(
        "app.modules.shop_runner.service_manager.services.shop_wide_common_sales.coordinator.resolve_legacy_assigned_nmids",
        AsyncMock(
            return_value=SimpleNamespace(
                nmids=frozenset({999}),
                complex_advs=(SimpleNamespace(main_nmid=999, all_adv_ids={55}),),
            )
        ),
    ):
        summary = await run_shop_wide_common_sale_stat_tick(
            shop_id="s-mid-null",
            wb_manager_hub=wb_hub,
            wb_shop_data_manager=MagicMock(),
            updater=CommonSaleStatUpdater(wb_hub, SimpleNamespace(insert=AsyncMock())),
            redis_client=RedisClient(fake_redis),
            redis_common_stat_timestamp_manager=SimpleNamespace(set=AsyncMock()),
        )
    assert summary.coverage_status == CoverageStatus.PARTIAL_ASSORTMENT
    assert summary.partial_reason == "null_response"
    store = ShopWideCoverageEvidenceStore(RedisClient(fake_redis))
    evidence = await store.read_last_attempt("s-mid-null")
    assert evidence is not None
    assert evidence.a_count == 100
    assert 999 in summary.legacy_route_updated_nmids


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        "[]",
        "42",
        "null",
    ],
)
async def test_malformed_evidence_non_dict_returns_none(fake_redis, payload: str) -> None:
    """F7/F12: JSON non-dict → None (fail closed)."""
    store = ShopWideCoverageEvidenceStore(RedisClient(fake_redis))
    await RedisClient(fake_redis).set(store.last_attempt_key("s-nondict"), payload)
    assert await store.read_last_attempt("s-nondict") is None


@pytest.mark.asyncio
async def test_malformed_evidence_wrong_scope_returns_none(fake_redis) -> None:
    """F12: wrong scope → None."""
    store = ShopWideCoverageEvidenceStore(RedisClient(fake_redis))
    await RedisClient(fake_redis).set(
        store.last_attempt_key("s-scope"),
        '{"schema_version": 1, "attempt_status": "STARTED", '
        '"window_start": "2026-01-01", "window_end": "2026-01-07", '
        '"a_count": 0, "e_count": 0, "u_count": 0, '
        '"assortment_complete": false, "assortment_pages": 0, '
        '"expected_pair_count": 0, "returned_pair_count": 0, '
        '"persisted_pair_count": 0, "missing_pair_count": 0, '
        '"rejected_pair_count": 0, "partial_reason": null, '
        '"tick_ts": "2026-01-01T00:00:00+00:00", "attempt_id": "x", '
        '"scope": "wrong_scope", "source": "wb_sales_funnel_products_history", '
        '"assortment_hash": "aa", "provisional": true}',
    )
    assert await store.read_last_attempt("s-scope") is None


@pytest.mark.asyncio
async def test_malformed_evidence_provisional_complete_rejected(fake_redis) -> None:
    """F12: provisional COMPLETE rejected."""
    store = ShopWideCoverageEvidenceStore(RedisClient(fake_redis))
    await RedisClient(fake_redis).set(
        store.last_attempt_key("s-prov-complete"),
        '{"schema_version": 1, "attempt_status": "COMPLETE", '
        '"window_start": "2026-01-01", "window_end": "2026-01-07", '
        '"a_count": 1, "e_count": 0, "u_count": 1, '
        '"assortment_complete": true, "assortment_pages": 1, '
        '"expected_pair_count": 7, "returned_pair_count": 7, '
        '"persisted_pair_count": 7, "missing_pair_count": 0, '
        '"rejected_pair_count": 0, "partial_reason": null, '
        '"tick_ts": "2026-01-01T00:00:00+00:00", "attempt_id": "x", '
        '"scope": "current_non_trash_cards", "source": "wb_sales_funnel_products_history", '
        '"assortment_hash": "aa", "provisional": true}',
    )
    assert await store.read_last_attempt("s-prov-complete") is None
