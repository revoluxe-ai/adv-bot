"""Full orders/sales collect с cursor pagination и полным JSONL persistence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, cast

from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.coverage import (
    CompletenessStatus,
    CoverageEntry,
    date_stats_from_rows,
)
from scripts.wb_api_readonly_ops.collect.pagination import (
    extract_last_change_date,
    merge_unique_rows,
    should_fetch_next_page,
)
from scripts.wb_api_readonly_ops.collect.raw_store import RawStore
from scripts.wb_api_readonly_ops.mutation_guard import assert_read_only_op


@dataclass(frozen=True)
class PaginationResult:
    """Результат cursor pagination для одного endpoint."""

    rows: list[dict[str, Any]]
    api_calls: int
    pagination_pages: int
    duplicate_page_detected: bool


async def collect_orders_sales(
    wb_data_manager: object,
    *,
    store: RawStore,
    budget: ApiCallBudget,
    orders_date_from: str,
    max_pages: int = 10_000,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Собрать orders+sales с pagination; сохранить полный JSONL."""
    assert_read_only_op("get_supplier_orders")
    assert_read_only_op("get_supplier_sales")
    dm = cast(Any, wb_data_manager)
    reports_manager = getattr(dm, "reports_manager", None)

    async def fetch_orders(date_from: str) -> list[object]:
        if reports_manager is not None:
            return list(await reports_manager.get_supplier_orders(date_from=date_from, flag=0) or [])
        return list(await dm.get_supplier_orders(date_from=date_from, flag=0) or [])

    async def fetch_sales(date_from: str) -> list[object]:
        if reports_manager is not None:
            return list(await reports_manager.get_supplier_sales(date_from=date_from, flag=0) or [])
        return list(await dm.get_supplier_sales(date_from=date_from, flag=0) or [])

    orders_result = await _paginate_supplier_rows(
        fetch=fetch_orders,
        initial_date_from=orders_date_from,
        budget=budget,
        max_pages=max_pages,
    )
    sales_result = await _paginate_supplier_rows(
        fetch=fetch_sales,
        initial_date_from=orders_date_from,
        budget=budget,
        max_pages=max_pages,
    )

    orders_entry = _coverage_entry(
        endpoint="/api/v1/supplier/orders",
        result=orders_result,
    )
    store.write_jsonl("orders.jsonl", orders_result.rows, entry=orders_entry)

    sales_entry = _coverage_entry(
        endpoint="/api/v1/supplier/sales",
        result=sales_result,
    )
    store.write_jsonl("sales.jsonl", sales_result.rows, entry=sales_entry)

    return orders_result.rows, sales_result.rows


def _coverage_entry(*, endpoint: str, result: PaginationResult) -> CoverageEntry:
    entry = CoverageEntry(
        family="orders_or_sales_reports_read",
        endpoint=endpoint,
        method="GET",
        http_statuses=[200],
        api_calls=result.api_calls,
        pagination_used=result.pagination_pages > 1,
        pagination_pages=result.pagination_pages,
    )
    if result.duplicate_page_detected:
        entry.notes.append("duplicate_page_protection_triggered")
    stats = date_stats_from_rows(result.rows)
    entry.min_date = stats["min_date"]
    entry.max_date = stats["max_date"]
    entry.min_last_change_date = stats["min_last_change_date"]
    entry.max_last_change_date = stats["max_last_change_date"]
    entry.unique_nmids = stats["unique_nmids"]
    entry.completeness = (
        CompletenessStatus.FULL_AVAILABLE
        if result.rows
        else CompletenessStatus.EMPTY
    )
    return entry


async def _paginate_supplier_rows(
    *,
    fetch: Callable[[str], Awaitable[list[object]]],
    initial_date_from: str,
    budget: ApiCallBudget,
    max_pages: int,
) -> PaginationResult:
    merged: list[dict[str, Any]] = []
    date_from = initial_date_from
    previous_cursor: str | None = None
    pages = 0
    api_calls = 0
    duplicate_detected = False
    while pages < max_pages:
        budget.consume()
        api_calls += 1
        page = list(await fetch(date_from) or [])
        pages += 1
        merged, _added, duplicate = merge_unique_rows(merged, page)
        if duplicate:
            duplicate_detected = True
        if not page:
            break
        new_cursor = extract_last_change_date(page[-1])
        if duplicate or not should_fetch_next_page(
            page, previous_cursor=previous_cursor, new_cursor=new_cursor
        ):
            break
        previous_cursor = new_cursor
        date_from = new_cursor
    return PaginationResult(
        rows=merged,
        api_calls=api_calls,
        pagination_pages=pages,
        duplicate_page_detected=duplicate_detected,
    )
