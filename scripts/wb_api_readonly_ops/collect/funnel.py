"""Historical sales funnel collect для всех nmIDs с batching × date windows."""

from __future__ import annotations

import datetime
from typing import Any, cast

from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.coverage import CompletenessStatus, CoverageEntry
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.raw_store import RawStore
from scripts.wb_api_readonly_ops.mutation_guard import assert_read_only_op

FUNNEL_MAX_DAYS_PER_REQUEST = 7
DEFAULT_NMID_BATCH = 20


async def collect_funnel(
    wb_data_manager: object,
    *,
    store: RawStore,
    budget: ApiCallBudget,
    nmids: list[int],
    date_from: datetime.date,
    date_to: datetime.date,
    nmid_batch_size: int = DEFAULT_NMID_BATCH,
) -> list[dict[str, Any]]:
    """POST sales-funnel/products/history для всех nmIDs и historical windows."""
    assert_read_only_op("get_sales_funnel_products_history")
    dm = cast(Any, wb_data_manager)
    rows: list[dict[str, Any]] = []
    api_calls = 0
    window_count = 0
    unique_nmids: set[int] = set()

    errors: list[str] = []

    for window_start, window_end in _iter_date_windows(date_from, date_to):
        window_count += 1
        for batch in _chunks(nmids, nmid_batch_size):
            budget.consume()
            api_calls += 1
            try:
                batch_rows = await dm.get_sales_funnel_products_history(
                    nmids=batch,
                    start=window_start,
                    end=window_end,
                )
            except Exception as exc:  # noqa: BLE001 — skip window/batch, continue
                errors.append(
                    f"{window_start}..{window_end} nmids={len(batch)}: "
                    f"{type(exc).__name__}: {exc}"
                )
                continue
            for item in batch_rows or []:
                as_dict = jsonable(item)
                if isinstance(as_dict, dict):
                    rows.append(as_dict)
                    nmid_val = as_dict.get("nmId") or as_dict.get("nm_id")
                    if nmid_val is not None:
                        try:
                            unique_nmids.add(int(nmid_val))
                        except (TypeError, ValueError):
                            pass

    entry = CoverageEntry(
        family="analytics_funnel_read",
        endpoint="/api/analytics/v3/sales-funnel/products/history",
        method="POST",
        http_statuses=[200],
        api_calls=api_calls,
        window_count=window_count,
        unique_nmids=len(unique_nmids) or (len(set(nmids)) if nmids else 0),
        pagination_used=window_count > 1 or len(nmids) > nmid_batch_size,
        completeness=(
            CompletenessStatus.FULL_AVAILABLE
            if rows and not errors
            else CompletenessStatus.PARTIAL
            if rows
            else CompletenessStatus.EMPTY
            if not nmids
            else CompletenessStatus.PARTIAL
        ),
    )
    entry.errors = errors[:20]
    if nmids and len(unique_nmids) < len(set(nmids)):
        entry.notes.append(
            f"funnel_nmids_requested={len(set(nmids))} with_data={len(unique_nmids)}"
        )
    store.write_jsonl("funnel/funnel.jsonl", rows, entry=entry)
    return rows


def _iter_date_windows(
    date_from: datetime.date, date_to: datetime.date
) -> list[tuple[datetime.date, datetime.date]]:
    if date_to < date_from:
        return []
    windows: list[tuple[datetime.date, datetime.date]] = []
    cur = date_from
    while cur <= date_to:
        end = min(cur + datetime.timedelta(days=FUNNEL_MAX_DAYS_PER_REQUEST - 1), date_to)
        windows.append((cur, end))
        cur = end + datetime.timedelta(days=1)
    return windows


def _chunks(items: list[int], size: int) -> list[list[int]]:
    if size <= 0:
        raise ValueError("batch size must be positive")
    return [items[i : i + size] for i in range(0, len(items), size)]
