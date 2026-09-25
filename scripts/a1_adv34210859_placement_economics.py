"""READ_ONLY: placement economics для adv 34210859 (nmID 837395782).

Targeted fullstats + v2 config + min bids. Без full-cabinet recollect.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts.wb_a1_associated_conversions import _nm_rows, _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable

SHOP_ID = "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-ADV34210859-PLACEMENT-ECONOMICS"

TARGET_ADV = 34210859
TARGET_NMID = 837395782
NEW_UNIFIED_ADV = 39900256
NEW_SEARCH_ADV = 39900211
ALL_ADVS = [TARGET_ADV, NEW_UNIFIED_ADV, NEW_SEARCH_ADV]

PERIOD_FROM = date(2026, 8, 5)
PERIOD_TO = date(2026, 9, 1)

WB_STATUS_NAMES = {
    4: "ready_to_launch",
    7: "completed_paused",
    8: "declined_stopped",
    9: "active",
    11: "paused",
}

PLATFORM_LABELS = {
    1: "website",
    32: "android",
    64: "ios",
}


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _in_period(day: str) -> bool:
    try:
        d = date.fromisoformat(day[:10])
    except ValueError:
        return False
    return PERIOD_FROM <= d <= PERIOD_TO


def _metric_row(
    *,
    placement: str,
    spend: float,
    views: int,
    clicks: int,
    orders: int,
    gmv: float,
    atbs: int = 0,
    source: str,
) -> dict[str, Any]:
    spend = round(spend, 2)
    gmv = round(gmv, 2)
    return {
        "PLACEMENT": placement,
        "SPEND": spend,
        "VIEWS": views,
        "CLICKS": clicks,
        "CTR": round(100 * clicks / views, 3) if views else None,
        "CPC": round(spend / clicks, 2) if clicks else None,
        "ATTRIBUTED_ORDERS": orders,
        "ATTRIBUTED_GMV": gmv,
        "ATBS": atbs,
        "ATTR_GMV_PER_RUB": round(gmv / spend, 3) if spend else None,
        "source": source,
    }


def _aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    spend = sum(_read_float(r, "spend", "day_spend") for r in rows)
    views = sum(_read_int(r, "views", "day_views") for r in rows)
    clicks = sum(_read_int(r, "clicks", "day_clicks") for r in rows)
    orders = sum(_read_int(r, "orders", "day_orders") for r in rows)
    gmv = sum(_read_float(r, "sum_price", "day_sum_price") for r in rows)
    atbs = sum(_read_int(r, "atbs") for r in rows)
    return _metric_row(
        placement="TOTAL",
        spend=spend,
        views=views,
        clicks=clicks,
        orders=orders,
        gmv=gmv,
        atbs=atbs,
        source="aggregated",
    )


def _platform_label(app_type: Any) -> str:
    try:
        code = int(app_type)
    except (TypeError, ValueError):
        return str(app_type or "unknown")
    return PLATFORM_LABELS.get(code, f"platform_{code}")


def _placement_zone_from_config(placements: dict[str, Any] | None) -> str:
    p = placements or {}
    search = bool(p.get("search"))
    rec = bool(p.get("recommendations"))
    if search and rec:
        return "mixed"
    if search and not rec:
        return "search"
    if rec and not search:
        return "recommendations"
    return "unresolved"


def _extract_nm_bids(nm_settings: list[Any], nmid: int) -> dict[str, Any]:
    for nm in nm_settings:
        if not isinstance(nm, dict):
            continue
        nid = _read_int(nm, "nm_id", "nmId", "nmID")
        if nid != nmid:
            continue
        bids = nm.get("bids_kopecks") or nm.get("bidsKopecks") or nm.get("bids") or {}
        if isinstance(bids, dict):
            return {
                "nm_id": nmid,
                "bids_kopecks": bids,
                "search_bid_kopecks": bids.get("search"),
                "recommendations_bid_kopecks": bids.get("recommendations"),
                "combined_bid_kopecks": bids.get("combined"),
            }
    return {"nm_id": nmid, "bids_kopecks": None}


def _campaign_config_block(raw: dict[str, Any], min_bids: dict[str, Any] | None) -> dict[str, Any]:
    settings = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
    placements = settings.get("placements") if isinstance(settings.get("placements"), dict) else {}
    nm_settings = raw.get("nm_settings") or raw.get("nmSettings") or []
    promoted = sorted(
        _read_int(nm, "nm_id", "nmId", "nmID")
        for nm in nm_settings
        if isinstance(nm, dict) and _read_int(nm, "nm_id", "nmId", "nmID")
    )
    st = _read_int(raw, "status")
    return {
        "adv_id": _read_int(raw, "id", "advertId"),
        "bid_type": raw.get("bid_type"),
        "payment_type": settings.get("payment_type") or settings.get("paymentType"),
        "search_placement_enabled": bool(placements.get("search")),
        "recommendations_placement_enabled": bool(placements.get("recommendations")),
        "placements": placements,
        "placement_zone_config": _placement_zone_from_config(placements),
        "wb_status": st,
        "wb_status_name": WB_STATUS_NAMES.get(st, f"status_{st}"),
        "name": settings.get("name"),
        "promoted_nmids": promoted,
        "target_nmid_bids": _extract_nm_bids(nm_settings, TARGET_NMID),
        "min_bid_probe": min_bids,
    }


async def _cpc_min_bids(pm: Any, adv_id: int, nmid: int) -> dict[str, Any]:
    from app.core.mp.wb.api.adapter.promotion_client.min_bids.raw_response_to_dto import (
        convert as response_to_dto,
    )
    from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
    from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.api.sozdanie_kampanij.post_api_advert_v1_bids_min import (
        asyncio_detailed,
    )
    from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
        PostApiAdvertV1BidsMinBody,
        PostApiAdvertV1BidsMinBodyPaymentType,
        PostApiAdvertV1BidsMinBodyPlacementTypesItem,
        PostApiAdvertV1BidsMinResponse200,
    )
    from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.types import Response

    adapter = pm._client.min_bids_adapter
    out: dict[str, Any] = {"endpoint": "POST /api/advert/v1/bids/min", "adv_id": adv_id, "nmID": nmid}
    for label, pt in (
        ("search", PostApiAdvertV1BidsMinBodyPlacementTypesItem.SEARCH),
        ("combined", PostApiAdvertV1BidsMinBodyPlacementTypesItem.COMBINED),
        ("recommendations", PostApiAdvertV1BidsMinBodyPlacementTypesItem.RECOMMENDATION),
    ):
        body = PostApiAdvertV1BidsMinBody(
            advert_id=adv_id,
            nm_ids=[nmid],
            payment_type=PostApiAdvertV1BidsMinBodyPaymentType.CPC,
            placement_types=[pt],
        )
        try:
            client = await adapter.auth_client_handler.get_proxy_client(adapter)
            response: Response[PostApiAdvertV1BidsMinResponse200] = await with_raise_errors(
                asyncio_detailed, client, body=body,
            )
            dto = response_to_dto(response.parsed) if response.parsed else []
            vals = [b.min_cpm for b in dto if b.nmid == nmid]
            out[f"min_bid_{label}_kopecks"] = vals[0] if vals else None
        except Exception as exc:  # noqa: BLE001
            out[f"min_bid_{label}_error"] = str(exc)[:400]
    return out


async def _fetch_normquery_search(
    pm: Any,
    adv_id: int,
    nmid: int,
) -> dict[str, Any]:
    from app.core.mp.wb.api.adapter.promotion_client.normquery_stats.command import (
        GetNormqueryStatsCommand,
        GetNormqueryStatsCommandBatchForAdv,
    )

    adapter = pm._client.normquery_stats_adapter
    rows: list[dict[str, Any]] = []
    day = PERIOD_FROM
    while day <= PERIOD_TO:
        command = GetNormqueryStatsCommand(
            date_from=day,
            date_to=day,
            batchs=[GetNormqueryStatsCommandBatchForAdv(adv_id=adv_id, nmid=nmid)],
        )
        try:
            dtos = await adapter.get_adv_v0_normquery_stats(command)
            for dto in dtos or []:
                dto_dict = jsonable(dto.model_dump() if hasattr(dto, "model_dump") else dto)
                for stat in dto_dict.get("stats") or []:
                    if not isinstance(stat, dict):
                        continue
                    rows.append(
                        {
                            "date": day.isoformat(),
                            "views": _read_int(stat, "views"),
                            "clicks": _read_int(stat, "clicks"),
                            "spend": _read_float(stat, "spend"),
                            "orders": _read_int(stat, "orders"),
                            "sum_price": _read_float(stat, "sum_price"),
                            "atbs": _read_int(stat, "add_to_cart", "atbs"),
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            rows.append({"date": day.isoformat(), "error": str(exc)[:300]})
        if day < PERIOD_TO:
            await asyncio.sleep(2)
        day += timedelta(days=1)

    return _aggregate_rows(rows) | {
        "PLACEMENT": "search_normquery_proxy",
        "source": "POST /adv/v0/normquery/stats (search-cluster traffic proxy)",
        "days_with_data": len({r["date"] for r in rows if "error" not in r and _read_int(r, "views") + _read_int(r, "clicks") > 0}),
        "normquery_row_count": len(rows),
    }


async def run_collect(output_dir: Path) -> dict[str, Any]:
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
    from redis.asyncio import Redis

    checked = _msk_now()
    gaps: list[str] = []

    app_config = AppConfig.create()
    rc = app_config.infrastructure.redis
    redis_raw: Redis[str] = Redis(
        host=rc.host, port=rc.port, db=rc.db, password=rc.password, decode_responses=True,
    )
    await redis_raw.ping()
    redis_wrap = RedisClient(redis_client=redis_raw)
    httpx = HttpxClientHandler()
    await httpx.init()
    try:
        await get_access_for_wb_cabinet(SHOP_ID)
        hub = WBManagerHubFactory(httpx_client_handler=httpx, redis_client_wrapper=redis_wrap).get_wb_manager_hub(SHOP_ID)
        pm = hub.wb_data_manager.promotion_manager
        budget = ApiCallBudget(max_seconds=1200.0, max_api_calls=200)

        budget.consume()
        camps_raw = list(await pm.get_adverts_v2_by_ids(ALL_ADVS) or [])
        configs: dict[int, dict[str, Any]] = {}
        for raw in camps_raw:
            d = jsonable(raw)
            if isinstance(d, dict):
                adv_id = _read_int(d, "id", "advertId")
                if adv_id:
                    configs[adv_id] = d

        min_bids: dict[int, dict[str, Any]] = {}
        for adv_id in ALL_ADVS:
            if adv_id in configs:
                min_bids[adv_id] = await _cpc_min_bids(pm, adv_id, TARGET_NMID)

        target_cfg = configs.get(TARGET_ADV, {})
        target_settings = target_cfg.get("settings") if isinstance(target_cfg.get("settings"), dict) else {}
        placements = target_settings.get("placements") if isinstance(target_settings.get("placements"), dict) else {}
        placement_zone = _placement_zone_from_config(placements)

        dates: list[date] = []
        d = PERIOD_FROM
        while d <= PERIOD_TO:
            dates.append(d)
            d += timedelta(days=1)
        budget.consume()
        stats_raw = list(await pm.get_full_adv_stat([TARGET_ADV], dates) or [])
        raw_items = [jsonable(x) for x in stats_raw if isinstance(jsonable(x), dict)]
        nm_rows, day_rows = _nm_rows(raw_items)

        period_nm = [r for r in nm_rows if _in_period(r.get("date", ""))]
        period_day = [r for r in day_rows if _in_period(r.get("date", ""))]
        target_nm = [r for r in period_nm if _read_int(r, "ordered_nm_id") == TARGET_NMID]

        by_platform: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in period_nm:
            by_platform[_platform_label(row.get("app_type"))].append(row)

        platform_table = [
            _aggregate_rows(rows) | {"PLACEMENT": f"platform_{label}", "source": "fullstats apps[] appType"}
            for label, rows in sorted(by_platform.items())
        ]

        campaign_total = _aggregate_rows(period_day) | {
            "PLACEMENT": "campaign_total",
            "source": "fullstats day totals",
        }
        target_nmid_total = _aggregate_rows(target_nm) | {
            "PLACEMENT": f"nmID_{TARGET_NMID}",
            "source": "fullstats apps/nms[] filtered",
        }

        placement_zone_table: list[dict[str, Any]] = []
        if placement_zone == "search":
            placement_zone_table.append(
                campaign_total
                | {
                    "PLACEMENT": "search",
                    "source": "config_inferred (search-only placements; API does not split placement zone in fullstats)",
                }
            )
        elif placement_zone == "recommendations":
            placement_zone_table.append(
                campaign_total
                | {
                    "PLACEMENT": "recommendations",
                    "source": "config_inferred (recommendations-only placements)",
                }
            )
        elif placement_zone == "mixed":
            placement_zone_table.append(
                _metric_row(
                    placement="mixed",
                    spend=_read_float(campaign_total, "SPEND"),
                    views=_read_int(campaign_total, "VIEWS"),
                    clicks=_read_int(campaign_total, "CLICKS"),
                    orders=_read_int(campaign_total, "ATTRIBUTED_ORDERS"),
                    gmv=_read_float(campaign_total, "ATTRIBUTED_GMV"),
                    source="unresolved — both search and recommendations enabled; fullstats has no placement-zone split",
                )
            )
            gaps.append("mixed placements enabled — fullstats cannot split search vs recommendations")
        else:
            placement_zone_table.append(
                _metric_row(
                    placement="unresolved",
                    spend=_read_float(campaign_total, "SPEND"),
                    views=_read_int(campaign_total, "VIEWS"),
                    clicks=_read_int(campaign_total, "CLICKS"),
                    orders=_read_int(campaign_total, "ATTRIBUTED_ORDERS"),
                    gmv=_read_float(campaign_total, "ATTRIBUTED_GMV"),
                    source="placements flags empty/disabled in current v2 config",
                )
            )
            gaps.append("placement zone unresolved from v2 config")

        placement_zone_table.append(
            _metric_row(
                placement="catalog",
                spend=0.0,
                views=0,
                clicks=0,
                orders=0,
                gmv=0.0,
                source="GAP — WB v3 fullstats has no catalog placement dimension",
            )
        )

        normquery_search = await _fetch_normquery_search(pm, TARGET_ADV, TARGET_NMID)

        gaps.extend([
            "fullstats apps[].appType is platform (website/android/ios), not search/recommendations/catalog",
            "catalog placement not exposed in v3 fullstats response",
            "config_inferred placement uses current v2 config, not historical placement flags",
        ])

        payload = {
            "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "MODE": "STRICT_READ_ONLY",
            "TARGET": {"adv_id": TARGET_ADV, "nmID": TARGET_NMID},
            "PERIOD": {"from": PERIOD_FROM.isoformat(), "to": PERIOD_TO.isoformat(), "timezone": "Europe/Moscow"},
            "PLACEMENT_ECONOMICS": {
                "placement_zone_table": placement_zone_table,
                "by_platform_apps": platform_table,
                "campaign_total": campaign_total,
                "target_nmid_subset": target_nmid_total,
                "search_normquery_proxy": normquery_search,
                "dominant_zone": placement_zone if placement_zone != "mixed" else "mixed_unresolved",
            },
            "CURRENT_V2_CONFIG_34210859": _campaign_config_block(
                configs.get(TARGET_ADV, {}), min_bids.get(TARGET_ADV),
            ),
            "NEW_CAMPAIGNS_CONFIG": {
                str(NEW_UNIFIED_ADV): _campaign_config_block(
                    configs.get(NEW_UNIFIED_ADV, {}), min_bids.get(NEW_UNIFIED_ADV),
                ),
                str(NEW_SEARCH_ADV): _campaign_config_block(
                    configs.get(NEW_SEARCH_ADV, {}), min_bids.get(NEW_SEARCH_ADV),
                ),
            },
            "remaining_gaps": gaps,
            "NO_WRITES": "CONFIRMED",
        }

        pkg = output_dir / PACKAGE
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / f"{PACKAGE}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
        )
        (pkg / "raw_fullstats_target_adv.json").write_text(
            json.dumps(raw_items, ensure_ascii=False, indent=2, default=str), encoding="utf-8",
        )
        return payload
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default="/tmp/a1_adv34210859_placement")
    args = ap.parse_args(argv)
    payload = asyncio.run(run_collect(Path(args.output_dir).resolve()))
    summary = {
        "CHECKED_AT_MSK": payload["CHECKED_AT_MSK"],
        "TARGET": payload["TARGET"],
        "PERIOD": payload["PERIOD"],
        "PLACEMENT_ECONOMICS": payload["PLACEMENT_ECONOMICS"],
        "CURRENT_V2_CONFIG_34210859": payload["CURRENT_V2_CONFIG_34210859"],
        "NEW_CAMPAIGNS_CONFIG": payload["NEW_CAMPAIGNS_CONFIG"],
        "remaining_gaps": payload["remaining_gaps"],
        "NO_WRITES": payload["NO_WRITES"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
