"""Advertising campaigns discovery, configs и historical fullstats."""

from __future__ import annotations

import datetime
from typing import Any, cast

from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.coverage import CompletenessStatus, CoverageEntry
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.raw_store import RawStore
from scripts.wb_api_readonly_ops.mutation_guard import assert_read_only_op


async def collect_ads(
    wb_data_manager: object,
    *,
    store: RawStore,
    budget: ApiCallBudget,
    date_from: datetime.date,
    date_to: datetime.date,
) -> tuple[list[int], list[dict[str, Any]]]:
    """Discovery всех campaign IDs, configs и fullstats history."""
    assert_read_only_op("get_full_adv_stat")
    dm = cast(Any, wb_data_manager)
    pm = dm.promotion_manager
    promotion_count = pm._client.promotion_count_adapter

    budget.consume()
    adv_ids = list(await promotion_count.get_cabinet_adv_ids() or [])
    ids_entry = CoverageEntry(
        family="advertising_campaigns_read",
        endpoint="/adv/v1/promotion/count",
        method="GET",
        http_statuses=[200],
        api_calls=1,
        unique_campaign_ids=len(adv_ids),
        completeness=(
            CompletenessStatus.FULL_AVAILABLE
            if adv_ids
            else CompletenessStatus.EMPTY
        ),
    )
    store.write_json(
        "ads/campaign_ids.json",
        {"adv_ids": adv_ids, "count": len(adv_ids)},
        entry=ids_entry,
        records_count=len(adv_ids),
    )

    budget.consume()
    campaigns_raw = list(await pm.get_adverts_v2_by_ids(adv_ids) or [])
    campaign_rows = [
        cast(dict[str, Any], jsonable(item))
        for item in campaigns_raw
        if isinstance(jsonable(item), dict)
    ]
    cfg_entry = CoverageEntry(
        family="advertising_campaigns_read",
        endpoint="/api/advert/v2/adverts",
        method="GET",
        http_statuses=[200],
        api_calls=_config_api_calls(len(adv_ids)),
        unique_campaign_ids=len(adv_ids),
        completeness=(
            CompletenessStatus.FULL_AVAILABLE
            if campaign_rows
            else CompletenessStatus.EMPTY if not adv_ids else CompletenessStatus.PARTIAL
        ),
    )
    if len(campaign_rows) < len(adv_ids):
        cfg_entry.notes.append(
            f"campaign_configs={len(campaign_rows)} adv_ids={len(adv_ids)}"
        )
    store.write_jsonl("ads/campaigns.jsonl", campaign_rows, entry=cfg_entry)

    fullstats_rows: list[dict[str, Any]] = []
    fs_entry = CoverageEntry(
        family="advertising_fullstats_read",
        endpoint="/adv/v3/fullstats",
        method="GET",
        http_statuses=[200],
        completeness=CompletenessStatus.EMPTY,
    )
    if adv_ids:
        budget.consume()
        dates = _date_range(date_from, date_to)
        stats = await pm.get_full_adv_stat(adv_ids, dates)
        fullstats_rows = _flatten_fullstats(stats)
        fs_entry.api_calls = _fullstats_api_calls(len(adv_ids), date_from, date_to)
        fs_entry.window_count = _fullstats_windows(date_from, date_to)
        fs_entry.unique_campaign_ids = len({r.get("advertId") for r in fullstats_rows})
        fs_entry.completeness = (
            CompletenessStatus.FULL_AVAILABLE
            if fullstats_rows
            else CompletenessStatus.PARTIAL
        )
    store.write_jsonl("ads/fullstats.jsonl", fullstats_rows, entry=fs_entry)

    return adv_ids, campaign_rows


def _config_api_calls(adv_count: int) -> int:
    return max(1, (adv_count + 49) // 50) if adv_count else 0


def _fullstats_windows(date_from: datetime.date, date_to: datetime.date) -> int:
    total_days = (date_to - date_from).days + 1
    if total_days <= 0:
        return 0
    return (total_days + 30) // 31


def _fullstats_api_calls(
    adv_count: int, date_from: datetime.date, date_to: datetime.date
) -> int:
    id_chunks = max(1, (adv_count + 49) // 50) if adv_count else 0
    return id_chunks * max(1, _fullstats_windows(date_from, date_to))


def _date_range(date_from: datetime.date, date_to: datetime.date) -> list[datetime.date]:
    if date_to < date_from:
        return []
    out: list[datetime.date] = []
    cur = date_from
    while cur <= date_to:
        out.append(cur)
        cur += datetime.timedelta(days=1)
    return out


def _flatten_fullstats(stats: list[object]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stat in stats:
        base = jsonable(stat)
        if not isinstance(base, dict):
            continue
        advert_id = base.get("advertId")
        days = base.get("days") or []
        if not isinstance(days, list):
            continue
        for day in days:
            if not isinstance(day, dict):
                day = cast(dict[str, Any], jsonable(day))
            row = dict(day)
            row["advertId"] = advert_id
            rows.append(row)
    return rows
