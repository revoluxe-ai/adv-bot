"""Normquery statistics через POST /adv/v0/normquery/stats (READ_ONLY)."""

from __future__ import annotations

import datetime
from typing import Any, cast

from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import (
    GetNormqueryStatsCommand,
    GetNormqueryStatsCommandBatchForAdv,
)

from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.coverage import CompletenessStatus, CoverageEntry
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.raw_store import RawStore
from scripts.wb_api_readonly_ops.mutation_guard import assert_read_only_op

# POST /adv/v0/normquery/stats: «date range must not exceed 30 days» (WB camp-api).
NORMQUERY_API_MAX_RANGE_DAYS = 30


def _allowed_normquery_period(
    date_from: datetime.date,
    date_to: datetime.date,
) -> tuple[datetime.date, datetime.date]:
    """Сжать диапазон до допустимого API окна (max 30 календарных дней inclusive)."""
    max_start = date_to - datetime.timedelta(days=NORMQUERY_API_MAX_RANGE_DAYS - 1)
    effective_from = max(date_from, max_start)
    if effective_from > date_to:
        effective_from = date_to
    return effective_from, date_to


def build_normquery_batches(
    campaign_rows: list[dict[str, Any]],
) -> list[GetNormqueryStatsCommandBatchForAdv]:
    """Построить adv_id+nmid pairs из campaign configs (без ComplexAdv/DB)."""
    batches: list[GetNormqueryStatsCommandBatchForAdv] = []
    seen: set[tuple[int, int]] = set()
    for row in campaign_rows:
        adv_id_raw = row.get("advertId") or row.get("id") or row.get("advert_id")
        if adv_id_raw is None:
            continue
        try:
            adv_id = int(adv_id_raw)
        except (TypeError, ValueError):
            continue
        nm_settings = row.get("nmSettings") or row.get("nm_settings") or []
        if not isinstance(nm_settings, list):
            continue
        for nm in nm_settings:
            if not isinstance(nm, dict):
                nm = cast(dict[str, Any], jsonable(nm))
            nmid_raw = nm.get("nmId") or nm.get("nm_id") or nm.get("nm")
            if nmid_raw is None:
                continue
            try:
                nmid = int(nmid_raw)
            except (TypeError, ValueError):
                continue
            key = (adv_id, nmid)
            if key in seen:
                continue
            seen.add(key)
            batches.append(
                GetNormqueryStatsCommandBatchForAdv(adv_id=adv_id, nmid=nmid)
            )
    return batches


async def collect_normqueries(
    wb_data_manager: object,
    *,
    store: RawStore,
    budget: ApiCallBudget,
    campaign_rows: list[dict[str, Any]],
    date_from: datetime.date,
    date_to: datetime.date,
) -> list[dict[str, Any]]:
    """Собрать normquery stats для adv+nmid pairs из campaign configs."""
    assert_read_only_op("get_normquery_stats")
    dm = cast(Any, wb_data_manager)
    batches = build_normquery_batches(campaign_rows)
    entry = CoverageEntry(
        family="normqueries_read",
        endpoint="/adv/v0/normquery/stats",
        method="POST",
        http_statuses=[200],
        completeness=CompletenessStatus.UNAVAILABLE,
    )
    if not batches:
        entry.notes.append("no_adv_nmid_pairs_from_campaign_configs")
        entry.completeness = CompletenessStatus.EMPTY
        store.write_jsonl("normqueries/normqueries.jsonl", [], entry=entry)
        return []

    effective_from, effective_to = _allowed_normquery_period(date_from, date_to)
    entry.window_count = 1
    entry.min_date = effective_from.isoformat()
    entry.max_date = effective_to.isoformat()
    entry.notes.extend(
        [
            f"API_max_range_days={NORMQUERY_API_MAX_RANGE_DAYS}",
            "historical_beyond_30d=normquery_historical_beyond_30_days_requires_separate_surface",
        ]
    )
    if date_from < effective_from:
        entry.notes.append(
            f"requested_from={date_from} capped_to={effective_from} "
            "(API max 30 days per request)"
        )

    command = GetNormqueryStatsCommand(
        date_from=effective_from,
        date_to=effective_to,
        batchs=batches,
    )
    adapter = dm.promotion_manager._client.normquery_stats_adapter
    budget.consume()
    api_calls = max(1, (len(batches) + 99) // 100)
    entry.api_calls = api_calls
    dtos = await adapter.get_adv_v0_normquery_stats(command)
    rows = [
        cast(dict[str, Any], jsonable(d))
        for d in (dtos or [])
        if isinstance(jsonable(d), dict)
    ]
    entry.completeness = (
        CompletenessStatus.FULL_AVAILABLE
        if rows
        else CompletenessStatus.PARTIAL
    )
    if not rows:
        entry.notes.append("normquery_stats_empty_or_permission_gap")
    store.write_jsonl("normqueries/normqueries.jsonl", rows, entry=entry)
    return rows
