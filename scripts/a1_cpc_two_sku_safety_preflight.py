"""READ_ONLY: A1 CPC two-SKU safety preflight (837395782 + 180148471).

Текущие stock/price/campaign/CPC-eligibility данные для безопасного launch plan.
Без advertising writes.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import dotenv

dotenv.load_dotenv()

from scripts import ch_a1_evidence as evidence
from scripts.wb_a1_associated_conversions import _read_float, _read_int
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable

SHOP_ID = evidence.SHOP_ID
MSK = ZoneInfo("Europe/Moscow")
PACKAGE = "A1-CPC-TWO-SKU-SAFETY-PREFLIGHT"

TARGET_CLIENT = {"nmid": 837395782, "label": "CLIENT_DESIGNATED", "primary_adv": 34210859}
TARGET_GROWTH = {"nmid": 180148471, "label": "GROWTH_CANDIDATE"}
TARGET_NMIDS = (837395782, 180148471)
ACTIVE_WB = {9, 11}
PAUSED_WB = {7, 8}

PG_FIELDS = [
    "id", "adv_id", "_search_adv_id", "type", "name", "nmids", "active_status", "bot_active",
    "auto_budget_watchdog_enabled", "auto_budget_daily_limit", "search_auto_budget_daily_limit",
    "use_common_budget", "common_budget_daily_limit", "strategy", "automatic_version",
    "auto_adv_target_status", "auction_adv_target_status",
]

WB_STATUS_NAMES = {
    4: "ready_to_launch",
    7: "completed/paused",
    8: "declined/stopped",
    9: "active",
    11: "active_variant",
}


def _msk_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(MSK)


def _pg_db() -> str:
    return os.environ.get("POSTGRES_DBNAME") or "adv_updater"


def _bootstrap() -> None:
    u, p = os.environ.get("POSTGRES_USER"), os.environ.get("POSTGRES_PASSWORD")
    if u and p:
        evidence._PG_CREDENTIALS = u, p
    h = os.environ.get("POSTGRES_MASTER_HOST") or os.environ.get("POSTGRES_REPLICA_HOST")
    if h:
        evidence.PG_EXTERNAL_HOST = h
    pt = os.environ.get("POSTGRES_PORT")
    if pt:
        evidence.PG_EXTERNAL_PORT = int(pt)


def _parse_nmids(raw: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", str(raw or ""))]


def _load_pg(root: Path) -> list[dict[str, str]]:
    out = root / "staging" / "pg_adv.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = ", ".join(f"a.{c}" for c in PG_FIELDS)
    q = (
        f"SELECT {cols} FROM public.advsetting a "
        f"JOIN public.wbcabinet c ON a.wb_cabinet_id = c.id "
        f"WHERE c.shop_id = '{SHOP_ID}'"
    )
    st = evidence.run_pg_query(_pg_db(), q, out, root / "sql" / "pg_adv.sql", csv_output=True)
    if not st["success"]:
        raise RuntimeError(st["stderr"])
    with out.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_wbcards(root: Path, nmids: tuple[int, ...]) -> dict[int, dict[str, Any]]:
    ids = ", ".join(str(n) for n in nmids)
    path = root / "staging" / "wbcard.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    q = (
        f"SELECT w.nmid, w.name, w.wb_category_id, w.json, w.adv_setting_id "
        f"FROM public.wbcard w JOIN public.wbcabinet c ON w.wb_cabinet_id = c.id "
        f"WHERE c.shop_id = '{SHOP_ID}' AND w.nmid IN ({ids})"
    )
    st = evidence.run_pg_query(_pg_db(), q, path, root / "sql" / "wbcard.sql", csv_output=True)
    out: dict[int, dict[str, Any]] = {}
    if not st["success"]:
        return out
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            nmid = _read_int(row, "nmid")
            if not nmid:
                continue
            raw: dict[str, Any] = {}
            try:
                parsed = json.loads(row.get("json") or "{}")
                if isinstance(parsed, dict):
                    raw = parsed
            except (TypeError, json.JSONDecodeError):
                pass
            out[nmid] = {
                "name": row.get("name") or raw.get("title"),
                "wb_category_id": row.get("wb_category_id") or raw.get("subjectID"),
                "subject": raw.get("subjectName"),
                "category": raw.get("parentName"),
                "adv_setting_id": row.get("adv_setting_id"),
                "pg_json_stock": _read_int(raw, "quantity", "stocks"),
            }
    return out


def _adv_nm_map(campaigns: list[dict[str, Any]]) -> dict[int, set[int]]:
    from collections import defaultdict

    out: dict[int, set[int]] = defaultdict(set)
    for c in campaigns:
        adv_id = _read_int(c, "id", "advertId")
        if not adv_id:
            continue
        for nm in c.get("nm_settings") or c.get("nmSettings") or []:
            if isinstance(nm, dict):
                nid = _read_int(nm, "nm_id", "nmId", "nmID")
                if nid:
                    out[adv_id].add(nid)
    return out


def _campaign_settings(c: dict[str, Any]) -> dict[str, Any]:
    s = c.get("settings") if isinstance(c.get("settings"), dict) else {}
    return {
        "payment_type": str(s.get("payment_type") or s.get("paymentType") or "unknown").lower(),
        "name": s.get("name") or c.get("name"),
        "placements": s.get("placements"),
        "status_name": s.get("status"),
    }


async def _fetch_cards(pm: Any, nmids: set[int]) -> dict[int, dict[str, Any]]:
    from app.core.mp.wb.api.generated.products.v1.content_products_client.models import (
        PostContentV2GetCardsListBody,
        PostContentV2GetCardsListBodySettings,
        PostContentV2GetCardsListBodySettingsCursor,
        PostContentV2GetCardsListBodySettingsFilter,
        PostContentV2GetCardsListBodySettingsSort,
    )
    from app.core.mp.wb.api.generated.products.v1.content_products_client.types import UNSET

    found: dict[int, dict[str, Any]] = {}
    sort = PostContentV2GetCardsListBodySettingsSort(ascending=True)

    for nmid in nmids:
        filter_ = PostContentV2GetCardsListBodySettingsFilter(with_photo=-1, text_search=str(nmid))
        cursor = PostContentV2GetCardsListBodySettingsCursor(limit=20)
        settings = PostContentV2GetCardsListBodySettings(filter_=filter_, cursor=cursor, sort=sort)
        body = PostContentV2GetCardsListBody(settings=settings)
        response = await pm.get_cards_list(body=body)
        if response is None:
            continue
        cards_raw = response.cards
        page = list(cards_raw) if cards_raw is not UNSET and cards_raw else []
        for card in page:
            d = jsonable(card)
            if not isinstance(d, dict):
                continue
            card_nmid = _read_int(d, "nmID", "nmId", "nmid")
            if card_nmid != nmid:
                continue
            sizes = d.get("sizes") or []
            chrt_ids: list[int] = []
            barcodes: list[str] = []
            seller_prices: list[float] = []
            for sz in sizes:
                if not isinstance(sz, dict):
                    continue
                cid = _read_int(sz, "chrtID", "chrtId")
                if cid:
                    chrt_ids.append(cid)
                skus = sz.get("skus") or []
                if isinstance(skus, list):
                    barcodes.extend(str(s) for s in skus)
                p = _read_float(sz, "price")
                if p > 0:
                    seller_prices.append(p)
            found[nmid] = {
                "nmID": nmid,
                "vendorCode": d.get("vendorCode"),
                "subjectName": d.get("subjectName"),
                "subjectID": d.get("subjectID"),
                "brand": d.get("brand"),
                "title": d.get("title"),
                "chrt_ids": chrt_ids,
                "barcodes": barcodes,
                "seller_price_rub": round(min(seller_prices), 2) if seller_prices else None,
                "seller_price_range_rub": (
                    [round(min(seller_prices), 2), round(max(seller_prices), 2)]
                    if seller_prices else None
                ),
                "discount": d.get("discount"),
                "raw_sizes_count": len(sizes),
            }
    return found


async def _fetch_seller_stocks(products: Any, cards: dict[int, dict[str, Any]]) -> dict[int, Any]:
    """POST /api/v3/stocks/{warehouse_id} по chrtIds (READ_ONLY)."""
    from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
    from app.core.mp.wb.api.generated.products.v1.content_products_client.api.ostatki_na_skladah_prodavtsa.post_api_v_3_stocks_warehouse_id import (
        asyncio_detailed as stocks_detailed,
    )
    from app.core.mp.wb.api.generated.products.v1.content_products_client.api.sklady_prodavtsa.get_api_v3_warehouses import (
        asyncio_detailed as wh_detailed,
    )
    from app.core.mp.wb.api.generated.products.v1.content_products_client.models.post_api_v3_stocks_warehouse_id_body import (
        PostApiV3StocksWarehouseIdBody,
    )

    all_chrt = sorted({cid for c in cards.values() for cid in c.get("chrt_ids", [])})
    if not all_chrt:
        return {"source": "POST /api/v3/stocks/{warehouse_id}", "status": "GAP_no_chrt_ids", "by_nmid": {}}

    content_adapter = products._product_cards_adapter
    try:
        proxy = await content_adapter.auth_client_handler.get_proxy_client(content_adapter)
        wh_resp = await with_raise_errors(wh_detailed, proxy)
    except Exception as exc:  # noqa: BLE001
        return {
            "source": "POST /api/v3/stocks/{warehouse_id}",
            "status": "GAP",
            "error": str(exc)[:400],
            "by_nmid": {n: {"warehouses": [], "total_sellable": None} for n in cards},
        }
    wh_parsed = wh_resp.parsed
    warehouses: list[dict[str, Any]] = []
    if wh_parsed is not None:
        raw_wh = jsonable(wh_parsed)
        if isinstance(raw_wh, dict):
            warehouses = raw_wh.get("warehouses") or raw_wh.get("data") or []
        elif isinstance(raw_wh, list):
            warehouses = raw_wh

    by_nmid: dict[int, dict[str, Any]] = {
        n: {"warehouses": [], "total_sellable": 0} for n in cards
    }
    chrt_to_nmid = {}
    for nmid, card in cards.items():
        for cid in card.get("chrt_ids", []):
            chrt_to_nmid[cid] = nmid

    for wh in warehouses:
        if not isinstance(wh, dict):
            continue
        wh_id = _read_int(wh, "id", "warehouseId")
        wh_name = wh.get("name") or wh.get("warehouseName")
        if not wh_id:
            continue
        body = PostApiV3StocksWarehouseIdBody(chrt_ids=all_chrt)
        try:
            resp = await with_raise_errors(stocks_detailed, proxy, warehouse_id=wh_id, body=body)
            parsed = resp.parsed
            stocks_raw = jsonable(parsed) if parsed is not None else {}
            items = []
            if isinstance(stocks_raw, dict):
                items = stocks_raw.get("stocks") or stocks_raw.get("data") or []
            for it in items:
                if not isinstance(it, dict):
                    continue
                chrt = _read_int(it, "chrtId", "chrt_id", "chrtID")
                qty = _read_int(it, "amount", "quantity", "stock")
                nmid = chrt_to_nmid.get(chrt)
                if not nmid:
                    continue
                row = {"warehouse_id": wh_id, "warehouse_name": wh_name, "chrt_id": chrt, "amount": qty}
                by_nmid[nmid]["warehouses"].append(row)
                by_nmid[nmid]["total_sellable"] += qty
        except Exception as exc:  # noqa: BLE001
            for nmid in cards:
                by_nmid[nmid].setdefault("errors", []).append(f"wh={wh_id}: {exc}")

    return {
        "source": "POST /api/v3/stocks/{warehouse_id}",
        "warehouse_count": len(warehouses),
        "note": "seller warehouse stocks only; FBO/WB warehouse may require warehouse_remains report",
        "by_nmid": by_nmid,
    }


async def _recent_spp(dm: Any, nmid: int) -> dict[str, Any]:
    """Последний non-cancelled order SPP (READ_ONLY supplier orders)."""
    rm = getattr(dm, "reports_manager", None)
    try:
        if rm:
            rows = list(await rm.get_supplier_orders(date_from="2026-08-15", flag=0) or [])
        else:
            rows = list(await dm.get_supplier_orders(date_from="2026-08-15", flag=0) or [])
    except Exception as exc:  # noqa: BLE001
        return {"status": "GAP", "error": str(exc)[:200]}
    best = None
    for r in rows:
        d = jsonable(r)
        if not isinstance(d, dict):
            continue
        if _read_int(d, "nmId", "nm_id", "nmid") != nmid:
            continue
        if str(d.get("isCancel")).lower() in ("true", "1", "t"):
            continue
        spp = _read_float(d, "spp")
        fp = _read_float(d, "finishedPrice", "priceWithDisc")
        tp = _read_float(d, "totalPrice")
        pwd = _read_float(d, "priceWithDisc")
        best = {
            "spp_pct": spp if spp > 0 else None,
            "finished_price_rub": fp if fp > 0 else None,
            "price_with_disc_rub": pwd if pwd > 0 else None,
            "total_price_rub": tp if tp > 0 else None,
            "order_date": str(d.get("date") or "")[:19],
            "source": "GET /api/v1/supplier/orders",
        }
    return best or {"status": "GAP_no_recent_order"}


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
            out[f"cpc_min_{label}_kopecks"] = [b.min_cpm for b in dto if b.nmid == nmid]
        except Exception as exc:  # noqa: BLE001
            out[f"cpc_min_{label}_error"] = str(exc)[:400]
    return out


def _pg_rows_for_nmid(pg: list[dict[str, str]], nmid: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in pg:
        adv = _read_int(row, "adv_id")
        nmids = _parse_nmids(row.get("nmids") or "")
        search = _read_int(row, "_search_adv_id")
        if nmid not in nmids:
            continue
        rows.append({
            "pg_id": row.get("id"),
            "adv_id": adv,
            "search_adv_id": search,
            "name": row.get("name"),
            "nmids": nmids,
            "active_status": _read_int(row, "active_status"),
            "bot_active": str(row.get("bot_active")).lower() in ("true", "t", "1"),
            "auto_budget_daily_limit": _read_int(row, "auto_budget_daily_limit"),
            "search_auto_budget_daily_limit": _read_int(row, "search_auto_budget_daily_limit"),
            "use_common_budget": str(row.get("use_common_budget")).lower() in ("true", "t", "1"),
            "common_budget_daily_limit": _read_int(row, "common_budget_daily_limit"),
            "strategy": row.get("strategy"),
            "automatic_version": row.get("automatic_version"),
            "auto_adv_target_status": row.get("auto_adv_target_status"),
            "auction_adv_target_status": row.get("auction_adv_target_status"),
        })
    return rows


def _campaigns_for_nmid(
    nmid: int,
    campaigns: list[dict[str, Any]],
    adv_nm: dict[int, set[int]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in campaigns:
        adv_id = _read_int(c, "id", "advertId")
        if not adv_id or nmid not in adv_nm.get(adv_id, ()):
            continue
        st = _read_int(c, "status")
        cfg = _campaign_settings(c)
        out.append({
            "adv_id": adv_id,
            "wb_status": st,
            "wb_status_name": WB_STATUS_NAMES.get(st, f"status_{st}"),
            "is_active_wb": st in ACTIVE_WB,
            "is_paused_wb": st in PAUSED_WB,
            **cfg,
            "nm_settings": c.get("nm_settings") or c.get("nmSettings"),
            "budget_from_config": c.get("budget"),
        })
    return out


async def _budgets(pm: Any, adv_ids: list[int]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for adv_id in adv_ids:
        try:
            b = await pm.get_campaign_budget(adv_id)
            d = jsonable(b)
            if hasattr(b, "to_dict"):
                d = b.to_dict()
            out[adv_id] = {
                "endpoint": "GET /adv/v1/budget",
                "total": d.get("total") if isinstance(d, dict) else getattr(b, "total", None),
                "cash": d.get("cash") if isinstance(d, dict) else getattr(b, "cash", None),
                "netting": d.get("netting") if isinstance(d, dict) else getattr(b, "netting", None),
            }
        except Exception as exc:  # noqa: BLE001
            out[adv_id] = {"endpoint": "GET /adv/v1/budget", "error": str(exc)[:300]}
    return out


def _build_sku_block(
    *,
    nmid: int,
    label: str,
    wbcard: dict[str, Any],
    card: dict[str, Any],
    stock: dict[str, Any],
    spp: dict[str, Any],
    pg_rows: list[dict[str, Any]],
    camp_rows: list[dict[str, Any]],
    budgets: dict[int, dict[str, Any]],
    cpc_min: dict[str, Any],
    primary_adv: int | None = None,
) -> dict[str, Any]:
    active = [c for c in camp_rows if c.get("is_active_wb")]
    for c in camp_rows:
        c["budget_live"] = budgets.get(c["adv_id"])

    seller_price = card.get("seller_price_rub")
    buyer = spp.get("finished_price_rub") or spp.get("price_with_disc_rub")

    stock_block = stock.get("by_nmid", {}).get(nmid, {})
    total_stock = stock_block.get("total_sellable")
    if total_stock is None and wbcard.get("pg_json_stock") is not None:
        total_stock = wbcard.get("pg_json_stock")
        stock_block = {"total_sellable": total_stock, "source_fallback": "wbcard.json"}

    min_vals = []
    for k, v in cpc_min.items():
        if k.startswith("cpc_min_") and k.endswith("_kopecks") and isinstance(v, list) and v:
            min_vals.extend(v)

    return {
        "nmID": nmid,
        "label": label,
        "subject": card.get("subjectName") or wbcard.get("subject"),
        "category": wbcard.get("category"),
        "wb_category_id": wbcard.get("wb_category_id"),
        "current_stock": {
            "total_sellable": total_stock,
            "by_warehouse": stock_block.get("warehouses", []),
            "source": stock.get("source"),
            "errors": stock_block.get("errors"),
        },
        "current_seller_price_rub": seller_price,
        "current_buyer_price_rub": buyer,
        "current_spp_pct": spp.get("spp_pct"),
        "spp_evidence": spp,
        "campaign_inventory": camp_rows,
        "has_active_campaign": len(active) > 0,
        "active_campaign_adv_ids": [c["adv_id"] for c in active],
        "pg_bot_linkage": pg_rows,
        "cpc_min_bid_probe": cpc_min,
        "cpc_min_bid_kopecks_summary": min(min_vals) if min_vals else None,
        "primary_adv_expected": primary_adv,
        "primary_adv_state": next(
            (c for c in camp_rows if c["adv_id"] == primary_adv), None
        ) if primary_adv else None,
    }


def _verdicts(payload: dict[str, Any]) -> dict[str, str]:
    s837 = payload["SKU_837395782"]
    s180 = payload["SKU_180148471"]
    c342 = s837.get("primary_adv_state") or {}
    risks_837: list[str] = []
    risks_180: list[str] = []

    v837 = "YES"
    if c342.get("is_active_wb"):
        v837 = "CONDITIONAL"
        risks_837.append("34210859 WB status active — verify intended pause before CPC")
    elif c342.get("wb_status") not in PAUSED_WB and c342:
        v837 = "CONDITIONAL"
        risks_837.append(f"34210859 status={c342.get('wb_status')} not in paused set")
    if s837.get("has_active_campaign"):
        v837 = "NO"
        risks_837.append("another active campaign contains nmID")
    if (s837.get("current_stock") or {}).get("total_sellable") == 0:
        v837 = "CONDITIONAL"
        risks_837.append("zero sellable stock signal")

    v180 = "YES"
    if s180.get("has_active_campaign"):
        v180 = "NO"
        risks_180.append("active campaign exists")
    elif s180.get("campaign_inventory"):
        v180 = "CONDITIONAL"
        risks_180.append("inactive/historical campaigns exist but none active")
    if not s180.get("cpc_min_bid_kopecks_summary") and s180.get("cpc_min_bid_probe", {}).get("cpc_min_search_error"):
        v180 = "CONDITIONAL"
        risks_180.append("CPC min bid probe failed — need create-time probe adv")

    conflicts = []
    if c342 and c342.get("payment_type") == "cpm":
        conflicts.append(
            "34210859 is separate CPM Search campaign; new CPC via POST /api/advert/v2/seacat/save/ad "
            "should not require converting 34210859 if left paused"
        )
    if s180.get("campaign_inventory"):
        conflicts.append("180148471 has historical CPM campaigns (all paused) — isolated new CPC preferred")

    return {
        "837395782_SAFE_FOR_ISOLATED_CPC": v837,
        "180148471_SAFE_FOR_ISOLATED_CPC": v180,
        "BLOCKING_RISKS": {
            "837395782": risks_837,
            "180148471": risks_180,
        },
        "EXISTING_CAMPAIGN_CONFLICTS": conflicts,
        "ROLLBACK_PATH": (
            "837395782: keep paused CPM 34210859 as rollback; do not delete/convert. "
            "180148471: no active contour — pause/delete new CPC only affects new campaign."
        ),
    }


CPC_API_ROUTES = {
    "create_campaign": "POST /api/advert/v2/seacat/save/ad",
    "get_campaigns": "GET /api/advert/v2/adverts",
    "start_pause": "GET /adv/v0/start | GET /adv/v0/pause (legacy) / status via v2",
    "min_bid": "POST /api/advert/v1/bids/min",
    "set_bids": "PATCH /adv/v0/auction/bids (auction topology)",
    "campaign_budget": "GET /adv/v1/budget",
    "deposit_budget": "POST /adv/v1/budget/deposit",
    "balance": "GET /adv/v1/balance",
    "normquery_stats": "POST /adv/v0/normquery/stats",
    "irreversible_or_topology_touching": [
        "payment model conversion on existing campaign",
        "deleting parent auto/search pair without mapping rollback",
        "mutating 34210859 payment_type or nm binding",
    ],
    "paused_create": (
        "WB v2 seacat save typically allows creating campaign before start; "
        "confirm status=ready/paused at create response — not probed (NO_WRITE)"
    ),
    "prefund_before_launch": (
        "GET /adv/v1/budget + POST /adv/v1/budget/deposit can fund campaign budget "
        "before GET /adv/v0/start — not executed"
    ),
}


async def run_preflight(
    root: Path,
    *,
    pg: list[dict[str, str]],
    wbcards: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    from app.configs.app_config import AppConfig
    from app.core.di.wb_manager_hub.wb_manager_hub_factory import WBManagerHubFactory
    from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
    from app.core.redis_manager_v2.redis_client import RedisClient
    from app.modules.common_slaves.wildberries.super_cabinet_manager import get_access_for_wb_cabinet
    from redis.asyncio import Redis

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
        dm = hub.wb_data_manager
        pm = dm.promotion_manager
        products = dm.products_manager

        cards = await _fetch_cards(products, set(TARGET_NMIDS))
        stocks = await _fetch_seller_stocks(products, cards)

        adv_ids = list(await pm._client.promotion_count_adapter.get_cabinet_adv_ids() or [])
        camps_raw = list(await pm.get_adverts_v2_by_ids(adv_ids) or [])
        campaigns = [jsonable(x) for x in camps_raw if isinstance(jsonable(x), dict)]
        adv_nm = _adv_nm_map(campaigns)

        # ensure 34210859 fetched even if not in count
        extra = [34210859]
        for e in extra:
            if e not in adv_ids:
                try:
                    extra_raw = await pm.get_adverts_v2_by_ids([e])
                    for x in extra_raw or []:
                        d = jsonable(x)
                        if isinstance(d, dict):
                            campaigns.append(d)
                            aid = _read_int(d, "id", "advertId")
                            if aid:
                                for nm in d.get("nm_settings") or d.get("nmSettings") or []:
                                    if isinstance(nm, dict):
                                        nid = _read_int(nm, "nm_id", "nmId", "nmID")
                                        if nid:
                                            adv_nm.setdefault(aid, set()).add(nid)
                except Exception:  # noqa: BLE001
                    pass

        all_adv = sorted({
            c["adv_id"] for c in (
                _campaigns_for_nmid(837395782, campaigns, adv_nm)
                + _campaigns_for_nmid(180148471, campaigns, adv_nm)
            )
        })
        budgets = await _budgets(pm, all_adv)

        spp837 = await _recent_spp(dm, 837395782)
        spp180 = await _recent_spp(dm, 180148471)

        cpc837 = await _cpc_min_bids(pm, 34210859, 837395782)
        # 180148471: probe first historical adv if any, else skip
        camps180 = _campaigns_for_nmid(180148471, campaigns, adv_nm)
        probe180 = camps180[0]["adv_id"] if camps180 else None
        cpc180 = (
            await _cpc_min_bids(pm, probe180, 180148471)
            if probe180
            else {"status": "GAP_no_campaign_for_probe", "note": "create-time min bid probe required"}
        )

        checked = _msk_now()
        sku837 = _build_sku_block(
            nmid=837395782, label="CLIENT_DESIGNATED",
            wbcard=wbcards.get(837395782, {}), card=cards.get(837395782, {}),
            stock=stocks, spp=spp837,
            pg_rows=_pg_rows_for_nmid(pg, 837395782),
            camp_rows=_campaigns_for_nmid(837395782, campaigns, adv_nm),
            budgets=budgets, cpc_min=cpc837, primary_adv=34210859,
        )
        sku180 = _build_sku_block(
            nmid=180148471, label="GROWTH_CANDIDATE",
            wbcard=wbcards.get(180148471, {}), card=cards.get(180148471, {}),
            stock=stocks, spp=spp180,
            pg_rows=_pg_rows_for_nmid(pg, 180148471),
            camp_rows=camps180,
            budgets=budgets, cpc_min=cpc180,
        )

        payload = {
            "CHECKED_AT_MSK": checked.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "SKU_837395782": sku837,
            "SKU_180148471": sku180,
            "CPC_API_ROUTES": CPC_API_ROUTES,
            "NO_WRITES": "CONFIRMED",
        }
        payload.update(_verdicts(payload))
        payload["CURRENT_STOCK_837395782"] = sku837["current_stock"]
        payload["CURRENT_STOCK_180148471"] = sku180["current_stock"]
        payload["CPC_MIN_BID_837395782"] = sku837["cpc_min_bid_probe"]
        payload["CPC_MIN_BID_180148471"] = sku180["cpc_min_bid_probe"]
        return payload
    finally:
        await httpx.shutdown()
        await redis_raw.aclose()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default=".tmp/a1_cpc_two_sku_preflight")
    args = ap.parse_args(argv)
    root = Path(args.output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "staging").mkdir(parents=True, exist_ok=True)
    (root / "sql").mkdir(parents=True, exist_ok=True)
    _bootstrap()
    pg = _load_pg(root)
    wbcards = _load_wbcards(root, TARGET_NMIDS)

    payload = asyncio.run(run_preflight(root, pg=pg, wbcards=wbcards))
    pkg = root / PACKAGE
    pkg.mkdir(parents=True, exist_ok=True)
    out_path = pkg / f"{PACKAGE}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    summary = {
        k: payload[k]
        for k in (
            "CHECKED_AT_MSK", "837395782_SAFE_FOR_ISOLATED_CPC", "180148471_SAFE_FOR_ISOLATED_CPC",
            "CURRENT_STOCK_837395782", "CURRENT_STOCK_180148471",
            "CPC_MIN_BID_837395782", "CPC_MIN_BID_180148471",
            "EXISTING_CAMPAIGN_CONFLICTS", "ROLLBACK_PATH", "BLOCKING_RISKS", "NO_WRITES",
        )
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
