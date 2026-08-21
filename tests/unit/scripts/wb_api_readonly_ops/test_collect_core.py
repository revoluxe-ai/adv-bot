"""Targeted unit tests для full collect pipeline (mocks only, no live WB API)."""

from __future__ import annotations

import json
import zipfile
from datetime import date, timedelta, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

from scripts.wb_api_readonly_ops.collect.ads import (
    _fullstats_windows,
    collect_ads,
)
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.cards import collect_cards
from scripts.wb_api_readonly_ops.collect.coverage import (
    ArtifactIntegrityError,
    CoverageEntry,
)
from scripts.wb_api_readonly_ops.collect.funnel import (
    FUNNEL_API_MAX_HISTORY_DAYS,
    _allowed_funnel_period,
    collect_funnel,
)
from scripts.wb_api_readonly_ops.collect.normqueries import build_normquery_batches
from scripts.wb_api_readonly_ops.collect.orders_sales import (
    _paginate_supplier_rows,
    collect_orders_sales,
)
from scripts.wb_api_readonly_ops.collect.pagination import (
    extract_last_change_date,
    merge_unique_rows,
    should_fetch_next_page,
)
from scripts.wb_api_readonly_ops.collect.raw_store import RawStore
from scripts.wb_api_readonly_ops.collect.runner import run_full_collect
from scripts.wb_api_readonly_ops.mutation_guard import (
    MUTATION_WRITE_OPS,
    MutationWriteRefused,
    assert_read_only_op,
)
from scripts.wb_api_readonly_ops.secret_strip import strip_secrets


def _order(srid: str, lcd: str, nmid: int = 1) -> dict[str, Any]:
    return {
        "srid": srid,
        "lastChangeDate": lcd,
        "date": lcd[:10],
        "nmId": nmid,
        "totalPrice": 100.0,
    }


def _sale(srid: str, lcd: str) -> dict[str, Any]:
    return {"srid": srid, "saleID": srid, "lastChangeDate": lcd, "date": lcd[:10]}


@pytest.mark.asyncio
async def test_no_sample_truncation_orders_sales(tmp_path: Path) -> None:
    """Collect store MUST persist all fetched rows (no [:20] truncation)."""
    rows = [_order(f"o{i}", f"2026-08-20T12:00:{i:02d}") for i in range(50)]
    dm = MagicMock()
    dm.reports_manager = MagicMock()
    dm.reports_manager.get_supplier_orders = AsyncMock(return_value=rows)
    dm.reports_manager.get_supplier_sales = AsyncMock(return_value=rows)
    store = RawStore(output_dir=tmp_path)
    budget = ApiCallBudget(max_seconds=60, max_api_calls=100)
    orders, sales = await collect_orders_sales(
        dm, store=store, budget=budget, orders_date_from="2026-08-01"
    )
    assert len(orders) == 50
    assert len(sales) == 50
    orders_file = tmp_path / "raw" / "orders.jsonl"
    assert sum(1 for _ in orders_file.open(encoding="utf-8")) == 50


@pytest.mark.asyncio
async def test_orders_full_persistence(tmp_path: Path) -> None:
    page1 = [_order("a", "2026-08-01T10:00:00")]
    page2 = [_order("b", "2026-08-02T10:00:00")]
    calls: list[str] = []

    async def fetch(date_from: str) -> list[dict[str, Any]]:
        calls.append(date_from)
        if len(calls) == 1:
            return page1
        if len(calls) == 2:
            return page2
        return []

    budget = ApiCallBudget(max_seconds=60, max_api_calls=10)
    result = await _paginate_supplier_rows(
        fetch=fetch, initial_date_from="2026-08-01", budget=budget, max_pages=10
    )
    assert len(result.rows) == 2
    assert result.api_calls == 3


@pytest.mark.asyncio
async def test_sales_full_persistence(tmp_path: Path) -> None:
    sales = [_sale("s1", "2026-08-01T11:00:00"), _sale("s2", "2026-08-02T11:00:00")]
    dm = MagicMock()
    dm.reports_manager = MagicMock()
    dm.reports_manager.get_supplier_orders = AsyncMock(return_value=[])
    dm.reports_manager.get_supplier_sales = AsyncMock(return_value=sales)
    store = RawStore(output_dir=tmp_path)
    budget = ApiCallBudget(max_seconds=60, max_api_calls=10)
    _, got = await collect_orders_sales(
        dm, store=store, budget=budget, orders_date_from="2026-08-01"
    )
    assert len(got) == 2


@pytest.mark.asyncio
async def test_orders_cursor_pagination() -> None:
    pages = [
        [_order("1", "2026-08-01T00:00:01")],
        [_order("2", "2026-08-01T00:00:02")],
        [],
    ]
    idx = 0

    async def fetch(_date_from: str) -> list[dict[str, Any]]:
        nonlocal idx
        chunk = pages[idx]
        idx += 1
        return chunk

    budget = ApiCallBudget(max_seconds=60, max_api_calls=10)
    result = await _paginate_supplier_rows(
        fetch=fetch, initial_date_from="2026-08-01", budget=budget, max_pages=10
    )
    assert len(result.rows) == 2
    assert result.pagination_pages == 3


@pytest.mark.asyncio
async def test_sales_cursor_pagination() -> None:
    pages = [[_sale("1", "2026-08-01T00:00:01")], []]
    idx = 0

    async def fetch(_date_from: str) -> list[dict[str, Any]]:
        nonlocal idx
        chunk = pages[idx]
        idx += 1
        return chunk

    budget = ApiCallBudget(max_seconds=60, max_api_calls=5)
    result = await _paginate_supplier_rows(
        fetch=fetch, initial_date_from="2026-08-01", budget=budget, max_pages=5
    )
    assert len(result.rows) == 1
    assert result.pagination_pages == 2


def test_cursor_termination_on_empty_page() -> None:
    assert should_fetch_next_page([], previous_cursor=None, new_cursor="x") is False


def test_duplicate_page_protection() -> None:
    page = [_order("dup", "2026-08-01T12:00:00")]
    merged, added, duplicate = merge_unique_rows([], page)
    assert added == 1
    merged2, added2, duplicate2 = merge_unique_rows(merged, page)
    assert added2 == 0
    assert duplicate2 is True
    assert should_fetch_next_page(
        page,
        previous_cursor="2026-08-01T12:00:00",
        new_cursor="2026-08-01T12:00:00",
    ) is False


@pytest.mark.asyncio
async def test_all_campaign_ids_persistence(tmp_path: Path) -> None:
    adv_ids = list(range(1, 136))
    dm = MagicMock()
    pm = MagicMock()
    pm._client.promotion_count_adapter.get_cabinet_adv_ids = AsyncMock(
        return_value=adv_ids
    )
    pm.get_adverts_v2_by_ids = AsyncMock(return_value=[])
    pm.get_full_adv_stat = AsyncMock(return_value=[])
    dm.promotion_manager = pm
    store = RawStore(output_dir=tmp_path)
    budget = ApiCallBudget(max_seconds=60, max_api_calls=100)
    got_ids, _ = await collect_ads(
        dm,
        store=store,
        budget=budget,
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 21),
    )
    assert got_ids == adv_ids
    payload = json.loads((tmp_path / "raw" / "ads" / "campaign_ids.json").read_text())
    assert payload["count"] == 135


@pytest.mark.asyncio
async def test_campaign_config_batching_calls(tmp_path: Path) -> None:
    adv_ids = list(range(1, 101))
    dm = MagicMock()
    pm = MagicMock()
    pm._client.promotion_count_adapter.get_cabinet_adv_ids = AsyncMock(
        return_value=adv_ids
    )
    pm.get_adverts_v2_by_ids = AsyncMock(return_value=[{"id": 1}])
    pm.get_full_adv_stat = AsyncMock(return_value=[])
    dm.promotion_manager = pm
    store = RawStore(output_dir=tmp_path)
    budget = ApiCallBudget(max_seconds=60, max_api_calls=100)
    await collect_ads(
        dm,
        store=store,
        budget=budget,
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 2),
    )
    pm.get_adverts_v2_by_ids.assert_called_once_with(adv_ids)


@pytest.mark.asyncio
async def test_fullstats_batching_invoked(tmp_path: Path) -> None:
    adv_ids = [1, 2, 3]
    dm = MagicMock()
    pm = MagicMock()
    pm._client.promotion_count_adapter.get_cabinet_adv_ids = AsyncMock(
        return_value=adv_ids
    )
    pm.get_adverts_v2_by_ids = AsyncMock(return_value=[])
    stat = MagicMock()
    stat.model_dump.return_value = {
        "advertId": 1,
        "days": [{"date": "2026-08-01T00:00:00", "views": 1, "clicks": 1, "sum": 1.0}],
    }
    pm.get_full_adv_stat = AsyncMock(return_value=[stat])
    dm.promotion_manager = pm
    store = RawStore(output_dir=tmp_path)
    budget = ApiCallBudget(max_seconds=60, max_api_calls=100)
    await collect_ads(
        dm,
        store=store,
        budget=budget,
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 2),
    )
    pm.get_full_adv_stat.assert_called_once()
    lines = (tmp_path / "raw" / "ads" / "fullstats.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1


def test_fullstats_date_windowing_count() -> None:
    assert _fullstats_windows(date(2026, 1, 1), date(2026, 1, 31)) == 1
    assert _fullstats_windows(date(2026, 1, 1), date(2026, 3, 1)) == 2


@pytest.mark.asyncio
async def test_funnel_nmid_batching(tmp_path: Path) -> None:
    """Все nmIDs обрабатываются batching'ом в одном 7-day window."""
    nmids = list(range(1, 45))
    dm = MagicMock()
    dm.get_sales_funnel_products_history = AsyncMock(
        side_effect=lambda nmids, start, end: [{"nmId": nmids[0], "date": str(start)}]
    )
    store = RawStore(output_dir=tmp_path)
    budget = ApiCallBudget(max_seconds=60, max_api_calls=100)
    date_to = date(2026, 8, 21)
    await collect_funnel(
        dm,
        store=store,
        budget=budget,
        nmids=nmids,
        date_from=date(2010, 1, 1),
        date_to=date_to,
        nmid_batch_size=20,
    )
    calls = dm.get_sales_funnel_products_history.await_args_list
    assert len(calls) == 3
    assert len(calls[0].kwargs["nmids"]) == 20
    expected_start, expected_end = _allowed_funnel_period(date_to)
    for call in calls:
        assert call.kwargs["start"] == expected_start
        assert call.kwargs["end"] == expected_end


def test_funnel_allowed_period_respects_api_retention() -> None:
    """startDate не старше API retention (7 days inclusive)."""
    date_to = date(2026, 8, 21)
    start, end = _allowed_funnel_period(date_to)
    assert end == date_to
    assert (end - start).days == FUNNEL_API_MAX_HISTORY_DAYS - 1
    assert start == date(2026, 8, 15)


@pytest.mark.asyncio
async def test_funnel_never_requests_start_older_than_api_retention(
    tmp_path: Path,
) -> None:
    """Collect funnel игнорирует date_from старше retention и не шлёт historical windows."""
    nmids = list(range(1, 25))
    dm = MagicMock()
    captured: list[tuple[date, date]] = []

    async def _mock(*, nmids: list[int], start: date, end: date) -> list[dict[str, int]]:
        captured.append((start, end))
        return [{"nmId": nmids[0]}]

    dm.get_sales_funnel_products_history = _mock
    store = RawStore(output_dir=tmp_path)
    budget = ApiCallBudget(max_seconds=60, max_api_calls=100)
    date_to = date(2026, 8, 21)
    await collect_funnel(
        dm,
        store=store,
        budget=budget,
        nmids=nmids,
        date_from=date(2020, 1, 1),
        date_to=date_to,
        nmid_batch_size=10,
    )
    expected_start, expected_end = _allowed_funnel_period(date_to)
    assert len(captured) == 3
    assert all(s == expected_start and e == expected_end for s, e in captured)
    assert expected_start >= date_to - timedelta(days=FUNNEL_API_MAX_HISTORY_DAYS - 1)


def test_fullstats_collect_uses_promotion_manager_adapter() -> None:
    """ads fullstats MUST идти через PromotionManager.get_full_adv_stat (adapter stack)."""
    import inspect
    from scripts.wb_api_readonly_ops.collect import ads as ads_mod

    src = inspect.getsource(ads_mod.collect_ads)
    assert "get_full_adv_stat" in src
    assert "httpx" not in src
    assert "get_adv_v3_fullstats" not in src


@pytest.mark.asyncio
async def test_cards_cursor_pagination(tmp_path: Path) -> None:
    from app.core.mp.wb.api.generated.products.v1.content_products_client.types import (
        UNSET,
    )

    class FakeCard:
        def __init__(self, nmid: int) -> None:
            self.nm_id = nmid

        def to_dict(self) -> dict[str, int | str]:
            return {"nmID": self.nm_id, "title": str(self.nm_id)}

    page1 = MagicMock()
    page1.cards = [FakeCard(111)]
    page1.cursor = MagicMock(updated_at="2026-08-01", nm_id=111)

    page2 = MagicMock()
    page2.cards = [FakeCard(222)]
    page2.cursor = UNSET

    dm = MagicMock()
    pm = MagicMock()
    pm.get_cards_list = AsyncMock(side_effect=[page1, page2])
    dm.products_manager = pm
    store = RawStore(output_dir=tmp_path)
    budget = ApiCallBudget(max_seconds=60, max_api_calls=10)
    nmids, cards = await collect_cards(
        dm, store=store, budget=budget, page_limit=1
    )
    assert pm.get_cards_list.await_count == 2
    assert set(nmids) == {111, 222}
    assert len(cards) == 2


def test_secret_absence_in_artifacts(tmp_path: Path) -> None:
    entry = CoverageEntry(
        family="t",
        endpoint="/e",
        method="GET",
        records_fetched=1,
        records_stored=1,
    )
    store = RawStore(output_dir=tmp_path)
    store.write_jsonl(
        "secret_test.jsonl",
        [{"Authorization": "Bearer SECRET", "nmId": 1}],
        entry=entry,
    )
    text = (tmp_path / "raw" / "secret_test.jsonl").read_text()
    assert "SECRET" not in text
    assert "***REDACTED***" in text


def test_read_only_mutation_guard_blocks_writes() -> None:
    for op in ("start_campaign", "set_cluster_bids", "wallet_top_up"):
        assert op in MUTATION_WRITE_OPS
        with pytest.raises(MutationWriteRefused):
            assert_read_only_op(op)


def test_records_fetched_equals_stored_integrity_gate() -> None:
    entry = CoverageEntry(
        family="t",
        endpoint="/e",
        method="GET",
        records_fetched=2,
        records_stored=1,
    )
    with pytest.raises(ArtifactIntegrityError):
        entry.assert_integrity()


def test_build_normquery_batches_from_campaign_configs() -> None:
    rows = [
        {
            "id": 10,
            "nm_settings": [{"nm_id": 100}, {"nm_id": 200}],
        }
    ]
    batches = build_normquery_batches(rows)
    assert len(batches) == 2
    assert batches[0].adv_id == 10
    assert batches[0].nmid == 100


@pytest.mark.asyncio
async def test_run_full_collect_zip_layout(tmp_path: Path) -> None:
    dm = MagicMock()
    dm.reports_manager = MagicMock()
    dm.reports_manager.get_supplier_orders = AsyncMock(return_value=[_order("x", "2026-08-01T00:00:00")])
    dm.reports_manager.get_supplier_sales = AsyncMock(return_value=[_sale("x", "2026-08-01T00:00:00")])
    pm = MagicMock()
    pm._client.promotion_count_adapter.get_cabinet_adv_ids = AsyncMock(return_value=[1])
    pm.get_adverts_v2_by_ids = AsyncMock(return_value=[{"id": 1, "nm_settings": [{"nm_id": 1}]}])
    pm.get_full_adv_stat = AsyncMock(return_value=[])
    pm._client.normquery_stats_adapter.get_adv_v0_normquery_stats = AsyncMock(return_value=[])
    dm.promotion_manager = pm
    dm.products_manager = MagicMock()
    dm.products_manager.get_cards_list = AsyncMock(return_value=None)
    dm.get_sales_funnel_products_history = AsyncMock(return_value=[])

    report = await run_full_collect(
        shop_id="shop-1",
        wb_data_manager=dm,
        output_dir=tmp_path,
        orders_date_from="2026-08-01",
        max_seconds=60,
        max_api_calls=50,
    )
    assert report.integrity_pass is True
    zpath = tmp_path / "wb_readonly_research.zip"
    assert zpath.exists()
    with zipfile.ZipFile(zpath) as zf:
        names = set(zf.namelist())
        assert "report.json" in names
        assert "manifest.json" in names
        assert "raw/orders.jsonl" in names
        assert "raw/sales.jsonl" in names
    assert strip_secrets(report.to_dict()) == report.to_dict()
